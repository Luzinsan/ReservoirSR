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
from pytorch_lightning.loggers import TensorBoardLogger
from pytorch_lightning.profilers import SimpleProfiler, PyTorchProfiler

from reservoir_sr.ml.data.sr_data_module import SrDataModule
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
            on_trace_ready=torch.profiler.tensorboard_trace_handler("./tb_profile"),
            record_shapes=True,
            with_stack=True,
        )
    raise ValueError(f"Unknown profiler mode: {mode}. Use 'simple' or 'pytorch'.")


@hydra.main(config_path="../conf", config_name="train", version_base="1.3")
def main(cfg: DictConfig) -> None:
    pl.seed_everything(cfg.globals.seed, workers=True)

    datamodule = SrDataModule(cfg.data)

    OmegaConf.set_struct(cfg, False)
    cfg.model.condition_dim = datamodule.condition_dim
    OmegaConf.set_struct(cfg, True)

    lit_module = SrLitModule(cfg)

    tb_cfg = cfg.globals.get("tensorboard", {})
    logger = TensorBoardLogger(
        save_dir=tb_cfg.get("save_dir", "."),
        name=tb_cfg.get("name", cfg.globals.project_name),
    )

    trainer = pl.Trainer(
        max_epochs=cfg.trainer.max_epochs,
        accelerator=cfg.trainer.accelerator,
        precision=cfg.trainer.precision,
        log_every_n_steps=cfg.trainer.log_every_n_steps,
        check_val_every_n_epoch=cfg.trainer.check_val_every_n_epoch,
        gradient_clip_val=cfg.trainer.gradient_clip_val,
        deterministic=cfg.trainer.deterministic,
        default_root_dir=".",
        logger=logger,
        profiler=_build_profiler(cfg),
        callbacks=[
            pl.callbacks.ModelCheckpoint(
                monitor="val/loss",
                mode="min",
                save_top_k=3,
                filename="epoch={epoch:03d}-val_loss={val/loss:.4f}",
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
