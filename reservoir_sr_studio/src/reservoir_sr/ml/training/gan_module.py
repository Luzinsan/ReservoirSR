from __future__ import annotations

from pathlib import Path

import pytorch_lightning as pl
import torch
import torch.nn as nn
import torch.nn.functional as F
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


class VGGPerceptualLoss(nn.Module):
    """Feature-matching loss на признаках VGG19 (до relu5_4), как в ESRGAN.

    Работает на произвольном числе каналов: входы проецируются в 3 канала
    обучаемой 1x1 сверткой перед прогоном через VGG.
    """

    def __init__(self, in_channels: int = 3, layer_indices=(2, 7, 16, 25, 34)):
        super().__init__()
        from torchvision.models import vgg19, VGG19_Weights
        vgg = vgg19(weights=VGG19_Weights.IMAGENET1K_V1).features
        for p in vgg.parameters():
            p.requires_grad = False
        self.vgg = vgg.eval()
        self.layer_indices = layer_indices

        if in_channels != 3:
            self.to_rgb = nn.Conv2d(in_channels, 3, kernel_size=1, bias=False)
        else:
            self.to_rgb = nn.Identity()

        # ImageNet statistics
        self.register_buffer("mean", torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1))
        self.register_buffer("std", torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1))

    def _extract(self, x: torch.Tensor) -> list[torch.Tensor]:
        x = self.to_rgb(x)
        x = (x - self.mean) / self.std
        feats = []
        for i, layer in enumerate(self.vgg):
            x = layer(x)
            if i in self.layer_indices:
                feats.append(x)
            if i >= max(self.layer_indices):
                break
        return feats

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        pred_f = self._extract(pred)
        with torch.no_grad():
            target_f = self._extract(target)
        loss = torch.zeros((), device=pred.device, dtype=pred.dtype)
        for pf, tf in zip(pred_f, target_f):
            loss = loss + F.l1_loss(pf, tf)
        return loss / len(pred_f)


class GanLitModule(pl.LightningModule):
    """GAN SR c поддержкой PSNR pretrain, perceptual loss и RaGAN."""

    def __init__(self, cfg: DictConfig) -> None:
        super().__init__()
        self.save_hyperparameters(cfg)
        self.cfg = cfg
        self.automatic_optimization = False

        self.generator: nn.Module = instantiate(cfg.model.generator, _recursive_=False)
        self.discriminator: nn.Module = instantiate(cfg.model.discriminator, _recursive_=False)
        self.pixel_loss: nn.Module = instantiate(cfg.model.pixel_loss)
        self.adv_loss: nn.Module = instantiate(cfg.model.adv_loss)

        # Perceptual loss: опционально
        if cfg.model.get("perceptual_loss") is not None:
            self.perceptual_loss: nn.Module | None = instantiate(cfg.model.perceptual_loss)
        else:
            self.perceptual_loss = None

        # Backward compat: visualization callback зовёт pl_module.model(batch)
        self.model = self.generator

        self.pixel_weight = float(cfg.model.get("pixel_weight", 1.0))
        self.adv_weight = float(cfg.model.get("adv_weight", 0.005))
        self.perc_weight = float(cfg.model.get("perc_weight", 0.0))
        self.d_steps = int(cfg.model.get("d_steps", 1))
        self.g_steps = int(cfg.model.get("g_steps", 1))

        # RaGAN: относительный средний лосс (ESRGAN-style)
        self.use_ragan = bool(cfg.model.get("use_ragan", True))

        # Label smoothing
        self.real_label = float(cfg.model.get("real_label", 1.0))
        self.fake_label = float(cfg.model.get("fake_label", 0.0))

        # Warmup: сколько эпох обучать только pixel+perceptual (без GAN)
        self.warmup_epochs = int(cfg.model.get("warmup_epochs", 0))

        # Gradient clipping (manual)
        self.grad_clip_val = float(cfg.model.get("grad_clip_val", 0.0) or 0.0)

        val_light, val_heavy = _build_metrics("val")
        self.val_metrics = val_light
        self.val_heavy = val_heavy

        self._maybe_load_generator_weights()

    # ------------------------------------------------------------------
    # Weight loading
    # ------------------------------------------------------------------

    def _maybe_load_generator_weights(self) -> None:
        path = self.cfg.model.get("resume_generator_from")
        if not path:
            return
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"resume_generator_from not found: {path}")

        print(f"[GanLitModule] Loading generator weights from {path}")
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        state_dict = ckpt.get("state_dict", ckpt)

        # В SrLitModule генератор лежит под 'model.*'
        gen_state = {}
        for k, v in state_dict.items():
            if k.startswith("model."):
                gen_state[k[len("model."):]] = v

        if not gen_state:
            raise RuntimeError(f"No 'model.*' keys in checkpoint {path}")

        missing, unexpected = self.generator.load_state_dict(gen_state, strict=False)
        print(f"[GanLitModule] Loaded. missing={len(missing)} unexpected={len(unexpected)}")

    # ------------------------------------------------------------------
    # Loss helpers
    # ------------------------------------------------------------------

    def _adv_d_loss(self, logits_real: torch.Tensor, logits_fake: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        real_t = torch.full_like(logits_real, self.real_label)
        fake_t = torch.full_like(logits_fake, self.fake_label)
        if self.use_ragan:
            # D пытается: real - mean(fake) -> real_label, fake - mean(real) -> fake_label
            d_real = self.adv_loss(logits_real - logits_fake.mean(dim=0, keepdim=True), real_t)
            d_fake = self.adv_loss(logits_fake - logits_real.mean(dim=0, keepdim=True), fake_t)
        else:
            d_real = self.adv_loss(logits_real, real_t)
            d_fake = self.adv_loss(logits_fake, fake_t)
        return 0.5 * (d_real + d_fake), d_real.detach(), d_fake.detach()

    def _adv_g_loss(self, logits_real: torch.Tensor, logits_fake: torch.Tensor) -> torch.Tensor:
        real_t = torch.full_like(logits_real, self.real_label)
        fake_t = torch.full_like(logits_fake, self.fake_label)
        if self.use_ragan:
            g_real = self.adv_loss(logits_real - logits_fake.mean(dim=0, keepdim=True), fake_t)
            g_fake = self.adv_loss(logits_fake - logits_real.mean(dim=0, keepdim=True), real_t)
            return 0.5 * (g_real + g_fake)
        return self.adv_loss(logits_fake, real_t)

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def training_step(self, batch: dict[str, torch.Tensor], batch_idx: int) -> None:
        opt_g, opt_d = self.optimizers()
        in_warmup = self.current_epoch < self.warmup_epochs

        # ---- D step ----
        d_loss_last = d_real_last = d_fake_last = None
        if not in_warmup:
            for _ in range(self.d_steps):
                self.toggle_optimizer(opt_d)
                opt_d.zero_grad()

                with torch.no_grad():
                    fake = self.generator(batch)
                real = batch["hr"]

                logits_real = self.discriminator(real)
                logits_fake = self.discriminator(fake.detach())
                d_loss, d_real_last, d_fake_last = self._adv_d_loss(logits_real, logits_fake)

                self.manual_backward(d_loss)
                if self.grad_clip_val > 0:
                    self.clip_gradients(opt_d, gradient_clip_val=self.grad_clip_val,
                                        gradient_clip_algorithm="norm")
                opt_d.step()
                self.untoggle_optimizer(opt_d)
                d_loss_last = d_loss.detach()

        # ---- G step ----
        g_total_last = g_pixel_last = g_adv_last = g_perc_last = None
        for _ in range(self.g_steps):
            self.toggle_optimizer(opt_g)
            opt_g.zero_grad()

            fake = self.generator(batch)
            g_pixel = self.pixel_loss(fake, batch["hr"])

            if self.perceptual_loss is not None and self.perc_weight > 0:
                g_perc = self.perceptual_loss(fake, batch["hr"])
            else:
                g_perc = torch.zeros((), device=fake.device, dtype=fake.dtype)

            if in_warmup:
                g_adv = torch.zeros((), device=fake.device, dtype=fake.dtype)
            else:
                logits_real = self.discriminator(batch["hr"]).detach()
                logits_fake = self.discriminator(fake)
                g_adv = self._adv_g_loss(logits_real, logits_fake)

            g_total = (self.pixel_weight * g_pixel
                       + self.perc_weight * g_perc
                       + self.adv_weight * g_adv)

            self.manual_backward(g_total)
            if self.grad_clip_val > 0:
                self.clip_gradients(opt_g, gradient_clip_val=self.grad_clip_val,
                                    gradient_clip_algorithm="norm")
            opt_g.step()
            self.untoggle_optimizer(opt_g)

            g_total_last = g_total.detach()
            g_pixel_last = g_pixel.detach()
            g_adv_last = g_adv.detach()
            g_perc_last = g_perc.detach()

        # ---- Logging ----
        if d_loss_last is not None:
            self.log("train/d_loss", d_loss_last, prog_bar=True)
            self.log("train/d_real", d_real_last)
            self.log("train/d_fake", d_fake_last)
        if g_total_last is not None:
            self.log("train/g_total", g_total_last, prog_bar=True)
            self.log("train/g_pixel", g_pixel_last)
            self.log("train/g_perc", g_perc_last)
            self.log("train/g_adv", g_adv_last)
        self.log("train/warmup", float(in_warmup))

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validation_step(self, batch: dict[str, torch.Tensor], batch_idx: int) -> None:
        sd = {"sync_dist": True}
        pred = self.generator(batch).float()
        target = batch["hr"].float()

        val_pixel = self.pixel_loss(pred, target)
        self.log("val/loss", val_pixel, prog_bar=True, **sd)

        # val/g_total = только pixel + perceptual (для выбора чекпоинта)
        if self.perceptual_loss is not None and self.perc_weight > 0:
            val_perc = self.perceptual_loss(pred, target)
        else:
            val_perc = torch.zeros((), device=pred.device)
        g_total = self.pixel_weight * val_pixel + self.perc_weight * val_perc
        self.log("val/g_total", g_total, prog_bar=True, **sd)
        self.log("val/g_perc", val_perc, **sd)

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

    # ------------------------------------------------------------------
    # Optimizers
    # ------------------------------------------------------------------

    def configure_optimizers(self):
        g_opt = instantiate(self.cfg.model.g_optimizer, params=self.generator.parameters())
        d_opt = instantiate(self.cfg.model.d_optimizer, params=self.discriminator.parameters())

        g_sched_cfg = self.cfg.model.get("g_scheduler")
        d_sched_cfg = self.cfg.model.get("d_scheduler")
        if g_sched_cfg is None and d_sched_cfg is None:
            return [g_opt, d_opt]

        schedulers = []
        if g_sched_cfg is not None and g_sched_cfg.get("_target_") is not None:
            schedulers.append(_scheduler_dict(instantiate(g_sched_cfg, optimizer=g_opt)))
        if d_sched_cfg is not None and d_sched_cfg.get("_target_") is not None:
            schedulers.append(_scheduler_dict(instantiate(d_sched_cfg, optimizer=d_opt)))
        return [g_opt, d_opt], schedulers


def _scheduler_dict(scheduler):
    if scheduler.__class__.__name__ == "ReduceLROnPlateau":
        return {"scheduler": scheduler, "interval": "epoch", "monitor": "val/loss"}
    return {"scheduler": scheduler, "interval": "epoch"}


def _psnr(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    mse = torch.mean((pred - target) ** 2)
    if mse == 0:
        return torch.tensor(100.0, device=pred.device)
    return 10.0 * torch.log10(1.0 / mse)


def _gradient_mae(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    mae_h = (torch.diff(pred, dim=2) - torch.diff(target, dim=2)).abs().mean()
    mae_w = (torch.diff(pred, dim=3) - torch.diff(target, dim=3)).abs().mean()
    return (mae_h + mae_w) / 2.0