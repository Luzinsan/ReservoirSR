"""Training entry point for Reservoir SR.

Usage:
    reservoir-sr-train                        -- all defaults
    reservoir-sr-train model=mdsr             -- select architecture
    reservoir-sr-train data/norm=log_pressure -- select normalization
    reservoir-sr-train trainer.max_epochs=50  -- override trainer param
    reservoir-sr-train globals.profiler=simple         -- quick text profiler
    reservoir-sr-train globals.profiler=pytorch        -- full torch profiler
"""
from __future__ import annotations

import hydra
import pytorch_lightning as pl
from omegaconf import DictConfig, OmegaConf
from pytorch_lightning.loggers import MLFlowLogger
from pytorch_lightning.profilers import SimpleProfiler, PyTorchProfiler

from reservoir_sr.ml.data.sr_data_module import SrDataModule
from reservoir_sr.ml.training.gan_module import GanLitModule
from reservoir_sr.ml.training.sr_module import SrLitModule
from reservoir_sr.ml.training.callbacks import SrVisualizationCallback
from pytorch_lightning.callbacks import TQDMProgressBar


def _build_profiler(cfg: DictConfig):
    """Build profiler from config. Returns None if disabled."""
    mode = cfg.globals.get("profiler")
    if not mode:
        return None
    if mode == "simple":
        return SimpleProfiler(dirpath=".", filename="profile_simple")
    if mode == "pytorch":
        import torch.profiler
        return PyTorchProfiler(
            dirpath=".",
            filename="profile_pytorch",
            schedule=torch.profiler.schedule(wait=2, warmup=2, active=6, repeat=1),
            record_shapes=True,
            with_stack=True,
        )
    raise ValueError(f"Unknown profiler mode: {mode}. Use 'simple' or 'pytorch'.")


def _count_trainable(module) -> int:
    return sum(p.numel() for p in module.parameters() if p.requires_grad)


@hydra.main(config_path="../conf", config_name="train", version_base="1.3")
def main(cfg: DictConfig) -> None:
    pl.seed_everything(cfg.globals.seed, workers=True)

    datamodule = SrDataModule(cfg.data)

    OmegaConf.set_struct(cfg, False)
    if cfg.model.get("condition_dim") is not None:
        cfg.model.condition_dim = datamodule.condition_dim
    if cfg.model.get("generator") is not None and cfg.model.generator.get("condition_dim") is not None:
        cfg.model.generator.condition_dim = datamodule.condition_dim
    OmegaConf.set_struct(cfg, True)

    task_name = cfg.get("task", {}).get("name", "sr")
    if task_name == "gan":
        lit_module = GanLitModule(cfg)
        monitor_metric = "val/g_total"
    else:
        lit_module = SrLitModule(cfg)
        monitor_metric = "val/loss"

    mlflow_cfg = cfg.globals.get("mlflow", {})
    logger = MLFlowLogger(
        experiment_name=mlflow_cfg.get("experiment_name", cfg.globals.experiment_name),
        tracking_uri=mlflow_cfg.get("tracking_uri", "file:./mlruns"),
        run_name=mlflow_cfg.get("run_name", cfg.globals.experiment_name),
        save_dir=mlflow_cfg.get("save_dir", "./mlruns"),
        log_model=mlflow_cfg.get("log_model", False),
    )
    logger.log_hyperparams({
        "task": task_name,
        "experiment_name": cfg.globals.experiment_name,
    })
    if task_name == "gan":
        g_params = _count_trainable(lit_module.generator)
        d_params = _count_trainable(lit_module.discriminator)
        logger.log_metrics({
            "meta/params_generator": float(g_params),
            "meta/params_discriminator": float(d_params),
            "meta/params_total": float(g_params + d_params),
        }, step=0)
    else:
        m_params = _count_trainable(lit_module.model)
        logger.log_metrics({
            "meta/params_model": float(m_params),
            "meta/params_total": float(m_params),
        }, step=0)

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
        gradient_clip_val=cfg.trainer.gradient_clip_val,
        deterministic=cfg.trainer.deterministic,
        default_root_dir=".",
        logger=logger,
        profiler=_build_profiler(cfg),
        callbacks=[
            pl.callbacks.ModelCheckpoint(
                monitor=monitor_metric,
                mode="min",
                save_top_k=3,
                filename="epoch={epoch:03d}",
                auto_insert_metric_name=False,
            ),
            pl.callbacks.LearningRateMonitor(logging_interval="epoch"),
            TQDMProgressBar(refresh_rate=10),
            SrVisualizationCallback(n_samples=cfg.trainer.vis_n_samples),
        ],
    )

    trainer.fit(
        lit_module,
        datamodule=datamodule,
        ckpt_path=cfg.globals.resume_from,
    )


if __name__ == "__main__":
    main()
