from __future__ import annotations
from copy import deepcopy

import pytorch_lightning as pl
import torch
import torch.nn as nn
from hydra.utils import instantiate
from omegaconf import DictConfig
from torchmetrics import MetricCollection
from torchmetrics.image import (
    ErrorRelativeGlobalDimensionlessSynthesis,
    SpectralAngleMapper,
    StructuralSimilarityIndexMeasure,
)


CHANNEL_NAMES = ("P", "ST", "SB")


def _build_metrics(p: str) -> tuple[MetricCollection, MetricCollection]:
    """Return (lightweight, heavy) metric collections."""
    lightweight = MetricCollection({
        "ergas": ErrorRelativeGlobalDimensionlessSynthesis(),
        "sam": SpectralAngleMapper(),
    }, prefix=f"{p}_spectral/")

    heavy = MetricCollection({
        "ssim": StructuralSimilarityIndexMeasure(data_range=1.0),
    }, prefix=f"{p}_structural/")

    return lightweight, heavy


class SrLitModule(pl.LightningModule):

    def __init__(self, cfg: DictConfig) -> None:
        super().__init__()
        self.save_hyperparameters(cfg)
        self.cfg = cfg

        self.model: nn.Module = instantiate(cfg.model, _recursive_=False)
        self.ema_decay = float(cfg.model.get("ema_decay", 0.999))
        self.use_ema = self.ema_decay > 0
        if self.use_ema:
            self.ema_model = deepcopy(self.model)
            for p in self.ema_model.parameters():
                p.requires_grad_(False)
            self.ema_model.eval()
            
        self.loss_fn: nn.Module = instantiate(cfg.model.loss)

        val_light, val_heavy = _build_metrics("val")
        test_light, test_heavy = _build_metrics("test")
        self.val_metrics = val_light
        self.val_heavy = val_heavy
        self.test_metrics = test_light
        self.test_heavy = test_heavy

    def training_step(self, batch: dict[str, torch.Tensor], batch_idx: int) -> torch.Tensor:
        pred = self.model(batch)
        loss = self.loss_fn(pred, batch["hr"])
        self.log("train/loss", loss, prog_bar=True)

        grad_norm = _total_grad_norm(self.model)
        if grad_norm is not None:
            self.log("train_debug/grad_norm", grad_norm)
        self.log("train_debug/pred_abs_max", pred.detach().abs().max())

        return loss

    def on_train_batch_end(self, outputs, batch, batch_idx) -> None:
        if not self.use_ema:
            return
        with torch.no_grad():
            for ema_p, p in zip(self.ema_model.parameters(), self.model.parameters()):
                ema_p.data.mul_(self.ema_decay).add_(p.data, alpha=1.0 - self.ema_decay)
            for ema_b, b in zip(self.ema_model.buffers(), self.model.buffers()):
                ema_b.data.copy_(b.data)

    def _eval_model(self) -> nn.Module:
        return self.ema_model if self.use_ema else self.model

    def validation_step(self, batch: dict[str, torch.Tensor], batch_idx: int) -> None:
        self._eval_step(batch, self.val_metrics, self.val_heavy, "val")

    def test_step(self, batch: dict[str, torch.Tensor], batch_idx: int) -> None:
        self._eval_step(batch, self.test_metrics, self.test_heavy, "test")

    def on_validation_epoch_end(self) -> None:
        self._flush_metrics(self.val_metrics, self.val_heavy)

    def on_test_epoch_end(self) -> None:
        self._flush_metrics(self.test_metrics, self.test_heavy)

    def _flush_metrics(self, light: MetricCollection, heavy: MetricCollection) -> None:
        """Compute, log and reset metrics; release GPU cache."""
        sd = {"sync_dist": True}
        for k, v in light.compute().items():
            self.log(k, v, **sd)
        for k, v in heavy.compute().items():
            self.log(k, v, prog_bar=k.endswith("/ssim"), **sd)
        light.reset()
        heavy.reset()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def _eval_step(
        self,
        batch: dict[str, torch.Tensor],
        light: MetricCollection,
        heavy: MetricCollection,
        prefix: str,
    ) -> None:
        sd = {"sync_dist": True}
        pred = self._eval_model()(batch).float()
        target = batch["hr"].float()

        self.log(f"{prefix}/loss", self.loss_fn(pred, target), prog_bar=True, **sd)

        for c in range(pred.shape[1]):
            ch = CHANNEL_NAMES[c] if c < len(CHANNEL_NAMES) else f"ch{c}"
            p, t = pred[:, c : c + 1], target[:, c : c + 1]
            self.log(f"{prefix}_psnr/{ch}", _psnr(p, t), **sd)
            self.log(f"{prefix}_mae/{ch}", (p - t).abs().mean(), **sd)

        self.log(f"{prefix}_psnr/mean", _psnr(pred, target), prog_bar=True, **sd)
        self.log(f"{prefix}_physics/max_ae", (pred - target).abs().max(), **sd)
        self.log(f"{prefix}_physics/grad_mae", _gradient_mae(pred, target), **sd)

        light.update(pred, target)
        heavy.update(pred, target)

    def configure_optimizers(self):
        optimizer = instantiate(
            self.cfg.model.optimizer,
            params=self.parameters(),
        )

        scheduler_cfg = self.cfg.model.scheduler
        if scheduler_cfg.get("_target_") is None:
            return optimizer

        scheduler = instantiate(scheduler_cfg, optimizer=optimizer)
        return {
            "optimizer": optimizer,
            "lr_scheduler": {
                "scheduler": scheduler,
                "interval": "epoch",
            },
        }


def _psnr(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    mse = torch.mean((pred - target) ** 2)
    if mse == 0:
        return torch.tensor(100.0, device=pred.device)
    return 10.0 * torch.log10(1.0 / mse)


def _gradient_mae(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """MAE between spatial gradients (finite differences along H and W)."""
    mae_h = (torch.diff(pred, dim=2) - torch.diff(target, dim=2)).abs().mean()
    mae_w = (torch.diff(pred, dim=3) - torch.diff(target, dim=3)).abs().mean()
    return (mae_h + mae_w) / 2.0


def _total_grad_norm(model: nn.Module) -> torch.Tensor | None:
    """L2 norm of all gradients (None if no grads yet)."""
    grads = [p.grad for p in model.parameters() if p.grad is not None]
    if not grads:
        return None
    return torch.norm(torch.stack([g.detach().norm() for g in grads]))
