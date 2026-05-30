from __future__ import annotations

from copy import deepcopy
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
    light = MetricCollection(
        {
            "ergas": ErrorRelativeGlobalDimensionlessSynthesis(),
            "sam": SpectralAngleMapper(),
        },
        prefix=f"{p}_spectral/",
    )
    heavy = MetricCollection(
        {"ssim": StructuralSimilarityIndexMeasure(data_range=1.0)},
        prefix=f"{p}_structural/",
    )
    return light, heavy


def _psnr(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    mse = torch.mean((pred - target) ** 2)
    if mse == 0:
        return torch.tensor(100.0, device=pred.device)
    return 10.0 * torch.log10(1.0 / mse)


def _gradient_mae(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    mae_h = (torch.diff(pred, dim=2) - torch.diff(target, dim=2)).abs().mean()
    mae_w = (torch.diff(pred, dim=3) - torch.diff(target, dim=3)).abs().mean()
    return 0.5 * (mae_h + mae_w)


# ============================================================================
# Perceptual loss
# ============================================================================


class PhysicsPerceptualLoss(nn.Module):
    """Физический perceptual loss: Sobel-градиенты + спектральная L1.

    Заменяет VGG-perceptual для физических полей: оптимизирует то,
    что нас реально волнует — резкость фронтов и спектральный состав.
    """

    def __init__(self, grad_weight: float = 1.0, spectral_weight: float = 0.5):
        super().__init__()
        self.grad_weight = grad_weight
        self.spectral_weight = spectral_weight
        sobel_x = torch.tensor(
            [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=torch.float32
        ).view(1, 1, 3, 3) / 8.0
        sobel_y = torch.tensor(
            [[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=torch.float32
        ).view(1, 1, 3, 3) / 8.0
        self.register_buffer("sobel_x", sobel_x)
        self.register_buffer("sobel_y", sobel_y)

    def _grad_l1(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        C = pred.shape[1]
        sx = self.sobel_x.expand(C, 1, 3, 3).to(pred.dtype)
        sy = self.sobel_y.expand(C, 1, 3, 3).to(pred.dtype)
        gx_p = F.conv2d(pred, sx, padding=1, groups=C)
        gy_p = F.conv2d(pred, sy, padding=1, groups=C)
        gx_t = F.conv2d(target, sx, padding=1, groups=C)
        gy_t = F.conv2d(target, sy, padding=1, groups=C)
        return ((gx_p - gx_t).abs() + (gy_p - gy_t).abs()).mean() * 0.5

    @staticmethod
    def _spectral_l1(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        # torch.fft не поддерживает bf16 — fp32 cast.
        f_pred = torch.fft.rfft2(pred.float(), norm="ortho").abs()
        f_target = torch.fft.rfft2(target.float(), norm="ortho").abs()
        return F.l1_loss(f_pred, f_target)

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        loss = self.grad_weight * self._grad_l1(pred, target)
        if self.spectral_weight > 0:
            loss = loss + self.spectral_weight * self._spectral_l1(pred, target).to(loss.dtype)
        return loss


# ============================================================================
# GAN Lightning module
# ============================================================================


class GanLitModule(pl.LightningModule):
    """SR GAN с поддержкой:

    - Pluggable generator (любая SR-архитектура).
    - Residual PatchGAN discriminator.
    - Hot-start генератора из PSNR-pretrain (resume_generator_from).
    - Двухфазный warmup: D-only → G(pixel+perc) → full GAN.
    - RaGAN или standard non-saturating loss.
    - Label smoothing + затухающий шум на D-входы.
    - Adaptive D-skip: пропуск D-шага если D слишком уверен.
    - EMA для генератора (стабильнее на валидации).
    """

    def __init__(self, cfg: DictConfig) -> None:
        super().__init__()
        self.save_hyperparameters(cfg)
        self.cfg = cfg
        self.automatic_optimization = False

        m = cfg.model
        self.generator: nn.Module = instantiate(m.generator, _recursive_=False)
        self.discriminator: nn.Module = instantiate(m.discriminator, _recursive_=False)
        self.pixel_loss: nn.Module = instantiate(m.pixel_loss)
        self.adv_loss: nn.Module = instantiate(m.adv_loss)
        self.perceptual_loss: nn.Module | None = (
            instantiate(m.perceptual_loss) if m.get("perceptual_loss") is not None else None
        )
        self.model = self.generator  # для совместимости с visualization callback

        # ── Loss weights ───────────────────────────────────────
        self.pixel_weight = float(m.get("pixel_weight", 1.0))
        self.adv_weight = float(m.get("adv_weight", 0.005))
        self.perc_weight = float(m.get("perc_weight", 0.0))

        # ── Training schedule ──────────────────────────────────
        self.d_steps = int(m.get("d_steps", 1))
        self.g_steps = int(m.get("g_steps", 1))
        self.d_warmup_epochs = int(m.get("d_warmup_epochs", 5))
        self.warmup_epochs = int(m.get("warmup_epochs", 20))

        # ── D stabilization ────────────────────────────────────
        self.d_input_noise_std = float(m.get("d_input_noise_std", 0.0))
        self.d_input_noise_decay_epochs = int(m.get("d_input_noise_decay_epochs", 30))
        self.d_skip_threshold = float(m.get("d_skip_threshold", 0.0))  # 0 = выкл, 0.4 рекомендуется
        self._last_d_loss: float | None = None

        # ── Loss variants ──────────────────────────────────────
        self.use_ragan = bool(m.get("use_ragan", True))
        self.real_label = float(m.get("real_label", 1.0))
        self.fake_label = float(m.get("fake_label", 0.0))

        # ── Gradient clipping (manual для GAN) ─────────────────
        self.grad_clip_val = float(m.get("grad_clip_val", 0.0) or 0.0)

        # ── EMA генератора ─────────────────────────────────────
        self.ema_decay = float(m.get("ema_decay", 0.999))
        self.use_ema = self.ema_decay > 0
        if self.use_ema:
            self.ema_generator = deepcopy(self.generator)
            for p in self.ema_generator.parameters():
                p.requires_grad_(False)
            self.ema_generator.eval()

        self.val_metrics, self.val_heavy = _build_metrics("val")
        self._maybe_load_generator_weights()

    # ------------------------------------------------------------------
    # Pretrain weights loading
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
        gen_state = {
            k[len("model."):]: v for k, v in state_dict.items() if k.startswith("model.")
        }
        if not gen_state:
            raise RuntimeError(f"No 'model.*' keys in checkpoint {path}")
        missing, unexpected = self.generator.load_state_dict(gen_state, strict=False)
        print(f"[GanLitModule] Loaded. missing={len(missing)} unexpected={len(unexpected)}")
        if self.use_ema:
            self.ema_generator.load_state_dict(self.generator.state_dict())

    # ------------------------------------------------------------------
    # Adversarial losses (RaGAN-aware)
    # ------------------------------------------------------------------

    def _adv_d(self, logits_real: torch.Tensor, logits_fake: torch.Tensor) -> torch.Tensor:
        real_t = torch.full_like(logits_real, self.real_label)
        fake_t = torch.full_like(logits_fake, self.fake_label)
        if self.use_ragan:
            d_real = self.adv_loss(logits_real - logits_fake.mean(0, keepdim=True), real_t)
            d_fake = self.adv_loss(logits_fake - logits_real.mean(0, keepdim=True), fake_t)
            return 0.5 * (d_real + d_fake)
        return 0.5 * (self.adv_loss(logits_real, real_t) + self.adv_loss(logits_fake, fake_t))

    def _adv_g(self, logits_real: torch.Tensor, logits_fake: torch.Tensor) -> torch.Tensor:
        real_t = torch.full_like(logits_real, self.real_label)
        fake_t = torch.full_like(logits_fake, self.fake_label)
        if self.use_ragan:
            g_real = self.adv_loss(logits_real - logits_fake.mean(0, keepdim=True), fake_t)
            g_fake = self.adv_loss(logits_fake - logits_real.mean(0, keepdim=True), real_t)
            return 0.5 * (g_real + g_fake)
        return self.adv_loss(logits_fake, real_t)

    # ------------------------------------------------------------------
    # Training step — высокоуровневая декомпозиция
    # ------------------------------------------------------------------

    def training_step(self, batch: dict[str, torch.Tensor], batch_idx: int) -> None:
        opt_g, opt_d = self.optimizers()
        device = batch["hr"].device

        in_d_warmup = self.current_epoch < self.d_warmup_epochs
        in_g_warmup = self.current_epoch < self.warmup_epochs
        noise_std = self._current_d_noise_std()

        # ── D step (с adaptive skip) ──────────────────────────
        d_stats = self._d_step(batch, opt_d, noise_std)

        # ── G step (skip во время D-warmup) ───────────────────
        g_stats = self._g_step(batch, opt_g, in_g_warmup) if not in_d_warmup else _zero_g_stats(device)
        warmup_phase = 0.0 if in_d_warmup else (1.0 if in_g_warmup else 2.0)

        # ── Logging ───────────────────────────────────────────
        self._log_d_stats(d_stats, noise_std)
        self._log_g_stats(g_stats, warmup_phase)
        if warmup_phase == 2.0 and d_stats["d_loss"] is not None:
            ratio = (d_stats["d_loss"] / (g_stats["g_adv"] + 1e-8)).clamp(0, 10)
            self.log("train/d_g_ratio", ratio)

    def _current_d_noise_std(self) -> float:
        decay = max(0.0, 1.0 - self.current_epoch / max(1, self.d_input_noise_decay_epochs))
        return self.d_input_noise_std * decay

    def _d_step(
        self,
        batch: dict[str, torch.Tensor],
        opt_d: torch.optim.Optimizer,
        noise_std: float,
    ) -> dict[str, torch.Tensor | float | None | bool]:
        """Один шаг дискриминатора с adaptive skip."""
        # Adaptive skip: если D слишком уверен — пропускаем.
        if self._should_skip_d():
            return {"d_loss": None, "logits_real": None, "logits_fake": None, "skipped": True}

        self.toggle_optimizer(opt_d)
        opt_d.zero_grad()

        with torch.no_grad():
            fake = self.generator(batch)

        real, fake_noisy = self._inject_noise(batch["hr"], fake, noise_std)
        logits_real = self.discriminator(real, batch["lr"])
        logits_fake = self.discriminator(fake_noisy, batch["lr"])
        d_loss = self._adv_d(logits_real, logits_fake)

        self.manual_backward(d_loss)
        if self.grad_clip_val > 0:
            self.clip_gradients(opt_d, self.grad_clip_val, "norm")
        opt_d.step()
        self.untoggle_optimizer(opt_d)

        self._last_d_loss = float(d_loss.detach())
        return {
            "d_loss": d_loss.detach(),
            "logits_real": logits_real.detach(),
            "logits_fake": logits_fake.detach(),
            "skipped": False,
        }

    def _should_skip_d(self) -> bool:
        return (
            self.d_skip_threshold > 0
            and self._last_d_loss is not None
            and self._last_d_loss < self.d_skip_threshold
        )

    @staticmethod
    def _inject_noise(
        real: torch.Tensor, fake: torch.Tensor, noise_std: float
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if noise_std <= 0:
            return real, fake
        return (
            real + torch.randn_like(real) * noise_std,
            fake + torch.randn_like(fake) * noise_std,
        )

    def _g_step(
        self,
        batch: dict[str, torch.Tensor],
        opt_g: torch.optim.Optimizer,
        in_g_warmup: bool,
    ) -> dict[str, torch.Tensor]:
        """Один шаг генератора (pixel + perc + опционально adv)."""
        self.toggle_optimizer(opt_g)
        opt_g.zero_grad()

        fake = self.generator(batch)
        g_pixel = self.pixel_loss(fake, batch["hr"])
        g_perc = (
            self.perceptual_loss(fake, batch["hr"])
            if self.perceptual_loss is not None and self.perc_weight > 0
            else torch.zeros((), device=fake.device, dtype=fake.dtype)
        )

        if in_g_warmup:
            g_adv = torch.zeros((), device=fake.device, dtype=fake.dtype)
        else:
            logits_fake_g = self.discriminator(fake, batch["lr"])
            logits_real_g = self.discriminator(batch["hr"], batch["lr"]).detach()
            g_adv = self._adv_g(logits_real_g, logits_fake_g)

        g_total = (
            self.pixel_weight * g_pixel
            + self.perc_weight * g_perc
            + self.adv_weight * g_adv
        )

        self.manual_backward(g_total)
        if self.grad_clip_val > 0:
            self.clip_gradients(opt_g, self.grad_clip_val, "norm")
        opt_g.step()
        self.untoggle_optimizer(opt_g)

        return {
            "g_total": g_total.detach(),
            "g_pixel": g_pixel.detach(),
            "g_perc": g_perc.detach(),
            "g_adv": g_adv.detach(),
        }

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------

    def _log_d_stats(self, d_stats: dict, noise_std: float) -> None:
        self.log("train/d_skipped", float(d_stats["skipped"]))
        self.log("train/d_noise_std", noise_std)
        if d_stats["d_loss"] is None:
            return
        self.log("train/d_loss", d_stats["d_loss"], prog_bar=True)
        self.log("train/d_logit_real", d_stats["logits_real"].mean())
        self.log("train/d_logit_fake", d_stats["logits_fake"].mean())
        self.log(
            "train/d_logit_gap",
            d_stats["logits_real"].mean() - d_stats["logits_fake"].mean(),
        )

    def _log_g_stats(self, g_stats: dict, warmup_phase: float) -> None:
        self.log("train/warmup_phase", warmup_phase)
        self.log("train/g_total", g_stats["g_total"], prog_bar=True)
        self.log("train/g_pixel", g_stats["g_pixel"])
        self.log("train/g_perc", g_stats["g_perc"])
        self.log("train/g_adv", g_stats["g_adv"])

    # ------------------------------------------------------------------
    # EMA hook
    # ------------------------------------------------------------------

    def on_train_batch_end(self, outputs, batch, batch_idx) -> None:
        if not self.use_ema:
            return
        with torch.no_grad():
            for ema_p, p in zip(self.ema_generator.parameters(), self.generator.parameters()):
                ema_p.data.mul_(self.ema_decay).add_(p.data, alpha=1.0 - self.ema_decay)
            for ema_b, b in zip(self.ema_generator.buffers(), self.generator.buffers()):
                ema_b.data.copy_(b.data)

    def _eval_model(self) -> nn.Module:
        """Используется в validation и visualization callback."""
        return self.ema_generator if self.use_ema else self.generator

    def on_save_checkpoint(self, checkpoint: dict) -> None:
        if self.use_ema:
            checkpoint["ema_generator_state_dict"] = self.ema_generator.state_dict()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validation_step(self, batch: dict[str, torch.Tensor], batch_idx: int) -> None:
        sd = {"sync_dist": True}
        pred = self._eval_model()(batch).float()
        target = batch["hr"].float()

        val_pixel = self.pixel_loss(pred, target)
        val_perc = (
            self.perceptual_loss(pred, target)
            if self.perceptual_loss is not None and self.perc_weight > 0
            else torch.zeros((), device=pred.device)
        )
        g_total = self.pixel_weight * val_pixel + self.perc_weight * val_perc

        self.log("val/loss", val_pixel, prog_bar=True, **sd)
        self.log("val/g_total", g_total, prog_bar=True, **sd)
        self.log("val/g_perc", val_perc, **sd)

        self.val_metrics.update(pred, target)
        self.val_heavy.update(pred, target)
        for c in range(pred.shape[1]):
            ch = CHANNEL_NAMES[c] if c < len(CHANNEL_NAMES) else f"ch{c}"
            p, t = pred[:, c:c + 1], target[:, c:c + 1]
            self.log(f"val_psnr/{ch}", _psnr(p, t), **sd)
            self.log(f"val_mae/{ch}", (p - t).abs().mean(), **sd)
        self.log("val_psnr/mean", _psnr(pred, target), prog_bar=True, **sd)
        self.log("val_physics/max_ae", (pred - target).abs().max(), **sd)
        self.log("val_physics/grad_mae", _gradient_mae(pred, target), **sd)

    def on_validation_epoch_end(self) -> None:
        sd = {"sync_dist": True}
        for k, v in self.val_metrics.compute().items():
            self.log(k, v, **sd)
        for k, v in self.val_heavy.compute().items():
            self.log(k, v, prog_bar=k.endswith("/ssim"), **sd)
        self.val_metrics.reset()
        self.val_heavy.reset()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    # ------------------------------------------------------------------
    # Optimizers
    # ------------------------------------------------------------------

    def configure_optimizers(self):
        g_opt = instantiate(self.cfg.model.g_optimizer, params=self.generator.parameters())
        d_opt = instantiate(self.cfg.model.d_optimizer, params=self.discriminator.parameters())

        schedulers = []
        for sched_cfg, opt in (
            (self.cfg.model.get("g_scheduler"), g_opt),
            (self.cfg.model.get("d_scheduler"), d_opt),
        ):
            if sched_cfg is not None and sched_cfg.get("_target_") is not None:
                schedulers.append(_scheduler_dict(instantiate(sched_cfg, optimizer=opt)))
        return ([g_opt, d_opt], schedulers) if schedulers else [g_opt, d_opt]


def _scheduler_dict(scheduler):
    if scheduler.__class__.__name__ == "ReduceLROnPlateau":
        return {"scheduler": scheduler, "interval": "epoch", "monitor": "val/loss"}
    return {"scheduler": scheduler, "interval": "epoch"}


def _zero_g_stats(device: torch.device) -> dict[str, torch.Tensor]:
    """Нулевые G-метрики для unified логирования во время D-warmup."""
    z = torch.zeros((), device=device)
    return {"g_total": z, "g_pixel": z, "g_perc": z, "g_adv": z}
