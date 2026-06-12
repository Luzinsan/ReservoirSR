"""Training entry point for Reservoir SR.

Usage:
    python -m reservoir_sr.tools.train +experiment=srresnet_baseline
    python -m reservoir_sr.tools.train +experiment=gan_srresnet
    python -m reservoir_sr.tools.train +experiment=gan_rfdn
    python -m reservoir_sr.tools.train +experiment=gan_mdsr
"""
from __future__ import annotations

import torch

# Patch torch.load для совместимости с Lightning checkpoint loading (weights_only=False).
_original_torch_load = torch.load


def _torch_load_unsafe(*args, **kwargs):
    kwargs["weights_only"] = False
    return _original_torch_load(*args, **kwargs)


torch.load = _torch_load_unsafe

from pathlib import Path

import hydra
import pytorch_lightning as pl
from omegaconf import DictConfig, OmegaConf
from pytorch_lightning.callbacks import (
    EarlyStopping,
    LearningRateMonitor,
    ModelCheckpoint,
    TQDMProgressBar,
)
from pytorch_lightning.loggers import CSVLogger, MLFlowLogger
from pytorch_lightning.profilers import PyTorchProfiler, SimpleProfiler

from reservoir_sr.ml.data.sr_data_module import SrDataModule
from reservoir_sr.ml.training.callbacks import SrVisualizationCallback
from reservoir_sr.ml.training.csv_report_callback import ExperimentReportCallback
from reservoir_sr.ml.training.gan_module import GanLitModule
from reservoir_sr.ml.training.sr_module import SrLitModule

torch.set_float32_matmul_precision("high")  # speedup на A100/H100 без потери качества


# ============================================================================
# Configuration helpers
# ============================================================================


def _build_profiler(cfg: DictConfig):
    mode = cfg.globals.get("profiler")
    if not mode:
        return None
    if mode == "simple":
        return SimpleProfiler(dirpath=".", filename="profile_simple")
    if mode == "pytorch":
        return PyTorchProfiler(
            dirpath=".",
            filename="profile_pytorch",
            schedule=torch.profiler.schedule(wait=2, warmup=2, active=6, repeat=1),
            record_shapes=True,
            with_stack=True,
        )
    raise ValueError(f"Unknown profiler mode: {mode}. Use 'simple' or 'pytorch'.")


def _resolve_condition_dim(cfg: DictConfig, datamodule: SrDataModule) -> None:
    """Прокинуть condition_dim из datamodule в model (для SR-режима с FiLM).
    GAN-конфиги всегда работают без conditioning."""
    OmegaConf.set_struct(cfg, False)
    if cfg.task != "gan" and cfg.model.get("condition_dim") is not None:
        cfg.model.condition_dim = datamodule.condition_dim
    OmegaConf.set_struct(cfg, True)


# ============================================================================
# Module factory
# ============================================================================


def _build_lit_module(cfg: DictConfig) -> tuple[pl.LightningModule, str, str]:
    """Возвращает (module, monitor_metric, monitor_mode).

    Для GAN мониторим SSIM (больше = лучше — perceptual quality).
    Для SR мониторим val/loss (меньше = лучше — pixel accuracy).
    """
    if cfg.task == "gan":
        return GanLitModule(cfg), "val_structural/ssim", "max"
    return SrLitModule(cfg), "val_psnr/mean", "max"


# ============================================================================
# Logger / metric setup
# ============================================================================


def _build_loggers(cfg: DictConfig, artifacts_dir: Path) -> list:
    mlflow_cfg = cfg.globals.get("mlflow", {})
    mlflow_logger = MLFlowLogger(
        experiment_name=mlflow_cfg.get("experiment_name", cfg.globals.experiment_name),
        tracking_uri=mlflow_cfg.get("tracking_uri", "file:./mlruns"),
        run_name=mlflow_cfg.get("run_name", cfg.globals.experiment_name),
        save_dir=mlflow_cfg.get("save_dir", "./mlruns"),
        log_model=mlflow_cfg.get("log_model", False),
    )
    csv_cfg = cfg.globals.get("csv", {})
    csv_logger = CSVLogger(
        save_dir=str(csv_cfg.get("save_dir", artifacts_dir / "csv")),
        name=cfg.globals.experiment_name,
    )
    return [mlflow_logger, csv_logger]


def _log_initial_metadata(lit_module, loggers: list, task: str) -> None:
    """Логируем гиперпараметры и количество параметров модели."""
    for lg in loggers:
        lg.log_hyperparams({"task": task, "experiment_name": lit_module.cfg.globals.experiment_name})

    if task == "gan":
        g = _count_trainable(lit_module.generator)
        d = _count_trainable(lit_module.discriminator)
        metrics = {
            "meta/params_generator": float(g),
            "meta/params_discriminator": float(d),
            "meta/params_total": float(g + d),
        }
    else:
        m = _count_trainable(lit_module.model)
        metrics = {"meta/params_model": float(m), "meta/params_total": float(m)}

    for lg in loggers:
        lg.log_metrics(metrics, step=0)


def _count_trainable(module) -> int:
    return sum(p.numel() for p in module.parameters() if p.requires_grad)


# ============================================================================
# Callbacks
# ============================================================================


def _build_callbacks(
    cfg: DictConfig,
    ckpt_dir: Path,
    monitor_metric: str,
    monitor_mode: str,
    report_path: Path,
) -> list:
    if cfg.task == "gan":
        filename = "epoch={epoch:03d}-ssim={val_structural/ssim:.4f}"
    else:
        filename = "epoch={epoch:03d}-psnr={val_psnr/mean:.2f}"
    callbacks = [
        ModelCheckpoint(
            dirpath=str(ckpt_dir),
            monitor=monitor_metric,
            mode=monitor_mode,
            save_top_k=3,
            filename=filename,
            auto_insert_metric_name=False,
        ),
        LearningRateMonitor(logging_interval="epoch"),
        TQDMProgressBar(refresh_rate=10),
        SrVisualizationCallback(n_samples=cfg.trainer.vis_n_samples),
        ExperimentReportCallback(cfg=cfg, report_path=report_path),
    ]

    # Early stopping для GAN: следим за SSIM
    if cfg.task == "gan":
        callbacks.append(
            EarlyStopping(
                monitor=monitor_metric,
                mode=monitor_mode,
                patience=50,
                min_delta=0.003,
                verbose=True,
                check_finite=True,
            )
        )

    return callbacks


# ============================================================================
# Main
# ============================================================================


@hydra.main(config_path="../conf", config_name="train", version_base="1.3")
def main(cfg: DictConfig) -> None:
    pl.seed_everything(cfg.globals.seed, workers=True)

    artifacts_dir = Path(cfg.globals.artifacts_dir)
    ckpt_dir = artifacts_dir / "checkpoints" / cfg.globals.experiment_name
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    # ── Data ──────────────────────────────────────────────────
    datamodule = SrDataModule(cfg.data)
    _resolve_condition_dim(cfg, datamodule)

    # ── Module ────────────────────────────────────────────────
    lit_module, monitor_metric, monitor_mode = _build_lit_module(cfg)

    # ── Loggers ───────────────────────────────────────────────
    loggers = _build_loggers(cfg, artifacts_dir)
    _log_initial_metadata(lit_module, loggers, cfg.task)

    # ── Trainer ───────────────────────────────────────────────
    csv_cfg = cfg.globals.get("csv", {})
    trainer = pl.Trainer(
        max_epochs=cfg.trainer.max_epochs,
        accelerator=cfg.trainer.accelerator,
        devices=cfg.trainer.get("devices", "auto"),
        num_nodes=cfg.trainer.get("num_nodes", 1),
        strategy=cfg.trainer.get("strategy", "auto"),
        precision=cfg.trainer.precision,
        benchmark=cfg.trainer.get("benchmark", False),
        log_every_n_steps=cfg.trainer.log_every_n_steps,
        check_val_every_n_epoch=cfg.trainer.check_val_every_n_epoch,
        # GAN — manual gradient clipping (см. gan_module.grad_clip_val).
        gradient_clip_val=None if cfg.task == "gan" else cfg.trainer.gradient_clip_val,
        deterministic=cfg.trainer.deterministic,
        default_root_dir=str(artifacts_dir),
        logger=loggers,
        profiler=_build_profiler(cfg),
        callbacks=_build_callbacks(
            cfg=cfg,
            ckpt_dir=ckpt_dir,
            monitor_metric=monitor_metric,
            monitor_mode=monitor_mode,
            report_path=Path(csv_cfg.report_path),
        ),
    )

    trainer.fit(lit_module, datamodule=datamodule, ckpt_path=cfg.globals.resume_from)


if __name__ == "__main__":
    main()