from __future__ import annotations

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
    lightweight = MetricCollection({
        "ergas": ErrorRelativeGlobalDimensionlessSynthesis(),
        "sam": SpectralAngleMapper(),
    }, prefix=f"{p}_spectral/")

    heavy = MetricCollection({
        "ssim": StructuralSimilarityIndexMeasure(data_range=1.0),
    }, prefix=f"{p}_structural/")
    return lightweight, heavy


class GanLitModule(pl.LightningModule):
    """Unified GAN framework for SR generators/discriminators."""

    def __init__(self, cfg: DictConfig) -> None:
        super().__init__()
        self.save_hyperparameters(cfg)
        self.cfg = cfg
        self.automatic_optimization = False

        self.generator: nn.Module = instantiate(cfg.model.generator, _recursive_=False)
        self.discriminator: nn.Module = instantiate(cfg.model.discriminator, _recursive_=False)
        self.pixel_loss: nn.Module = instantiate(cfg.model.pixel_loss)
        self.adv_loss: nn.Module = instantiate(cfg.model.adv_loss)

        # Backward compatibility with visualization callback that calls pl_module.model(batch).
        self.model = self.generator

        self.pixel_weight = float(cfg.model.get("pixel_weight", 1.0))
        self.adv_weight = float(cfg.model.get("adv_weight", 0.005))
        self.d_steps = int(cfg.model.get("d_steps", 1))
        self.g_steps = int(cfg.model.get("g_steps", 1))

        val_light, val_heavy = _build_metrics("val")
        self.val_metrics = val_light
        self.val_heavy = val_heavy

    def forward(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        return self.generator(batch)

    def training_step(self, batch: dict[str, torch.Tensor], batch_idx: int) -> None:
        opt_g, opt_d = self.optimizers()

        # 1) Train discriminator
        d_loss_last = None
        d_real_last = None
        d_fake_last = None
        for _ in range(self.d_steps):
            self.toggle_optimizer(opt_d)
            opt_d.zero_grad()

            with torch.no_grad():
                fake = self.generator(batch)
            real = batch["hr"]

            logits_real = self.discriminator(real)
            logits_fake = self.discriminator(fake.detach())
            real_target = torch.ones_like(logits_real)
            fake_target = torch.zeros_like(logits_fake)

            d_real = self.adv_loss(logits_real, real_target)
            d_fake = self.adv_loss(logits_fake, fake_target)
            d_loss = 0.5 * (d_real + d_fake)

            self.manual_backward(d_loss)
            opt_d.step()
            self.untoggle_optimizer(opt_d)

            d_loss_last = d_loss.detach()
            d_real_last = d_real.detach()
            d_fake_last = d_fake.detach()

        # 2) Train generator
        g_total_last = None
        g_pixel_last = None
        g_adv_last = None
        for _ in range(self.g_steps):
            self.toggle_optimizer(opt_g)
            opt_g.zero_grad()

            fake = self.generator(batch)
            logits_fake_for_g = self.discriminator(fake)
            real_target = torch.ones_like(logits_fake_for_g)

            g_pixel = self.pixel_loss(fake, batch["hr"])
            g_adv = self.adv_loss(logits_fake_for_g, real_target)
            g_total = self.pixel_weight * g_pixel + self.adv_weight * g_adv

            self.manual_backward(g_total)
            opt_g.step()
            self.untoggle_optimizer(opt_g)

            g_total_last = g_total.detach()
            g_pixel_last = g_pixel.detach()
            g_adv_last = g_adv.detach()

        if d_loss_last is not None:
            self.log("train/d_loss", d_loss_last, prog_bar=True)
            self.log("train/d_real", d_real_last)
            self.log("train/d_fake", d_fake_last)
        if g_total_last is not None:
            self.log("train/g_total", g_total_last, prog_bar=True)
            self.log("train/g_pixel", g_pixel_last)
            self.log("train/g_adv", g_adv_last)

    def validation_step(self, batch: dict[str, torch.Tensor], batch_idx: int) -> None:
        sd = {"sync_dist": True}
        pred = self.generator(batch).float()
        target = batch["hr"].float()

        val_pixel = self.pixel_loss(pred, target)
        logits_fake = self.discriminator(pred)
        adv_term = self.adv_loss(logits_fake, torch.ones_like(logits_fake))
        g_total = self.pixel_weight * val_pixel + self.adv_weight * adv_term

        self.log("val/loss", val_pixel, prog_bar=True, **sd)
        self.log("val/g_total", g_total, **sd)
        self.log("val/g_adv", adv_term, **sd)

        for k, v in self.val_metrics(pred, target).items():
            self.log(k, v, **sd)
        for k, v in self.val_heavy(pred, target).items():
            self.log(k, v, prog_bar=k.endswith("/ssim"), **sd)

        for c in range(pred.shape[1]):
            ch = CHANNEL_NAMES[c] if c < len(CHANNEL_NAMES) else f"ch{c}"
            p, t = pred[:, c : c + 1], target[:, c : c + 1]
            self.log(f"val_psnr/{ch}", _psnr(p, t), **sd)
            self.log(f"val_mae/{ch}", (p - t).abs().mean(), **sd)

        self.log("val_psnr/mean", _psnr(pred, target), prog_bar=True, **sd)
        self.log("val_physics/max_ae", (pred - target).abs().max(), **sd)
        self.log("val_physics/grad_mae", _gradient_mae(pred, target), **sd)

    def configure_optimizers(self):
        g_opt = instantiate(self.cfg.model.g_optimizer, params=self.generator.parameters())
        d_opt = instantiate(self.cfg.model.d_optimizer, params=self.discriminator.parameters())

        g_sched_cfg = self.cfg.model.get("g_scheduler")
        d_sched_cfg = self.cfg.model.get("d_scheduler")
        if g_sched_cfg is None and d_sched_cfg is None:
            return [g_opt, d_opt]

        schedulers = []
        if g_sched_cfg is not None and g_sched_cfg.get("_target_") is not None:
            g_sched = instantiate(g_sched_cfg, optimizer=g_opt)
            schedulers.append(_scheduler_dict(g_sched))
        if d_sched_cfg is not None and d_sched_cfg.get("_target_") is not None:
            d_sched = instantiate(d_sched_cfg, optimizer=d_opt)
            schedulers.append(_scheduler_dict(d_sched))

        return [g_opt, d_opt], schedulers


def _scheduler_dict(scheduler):
    if scheduler.__class__.__name__ == "ReduceLROnPlateau":
        return {
            "scheduler": scheduler,
            "interval": "epoch",
            "monitor": "val/loss",
        }
    return {
        "scheduler": scheduler,
        "interval": "epoch",
    }


def _psnr(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    mse = torch.mean((pred - target) ** 2)
    if mse == 0:
        return torch.tensor(100.0, device=pred.device)
    return 10.0 * torch.log10(1.0 / mse)


def _gradient_mae(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    mae_h = (torch.diff(pred, dim=2) - torch.diff(target, dim=2)).abs().mean()
    mae_w = (torch.diff(pred, dim=3) - torch.diff(target, dim=3)).abs().mean()
    return (mae_h + mae_w) / 2.0
