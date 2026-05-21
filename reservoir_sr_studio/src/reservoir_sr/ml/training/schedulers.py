from __future__ import annotations

import math

import torch
from torch.optim.lr_scheduler import _LRScheduler


class WarmupCosineLR(_LRScheduler):

    def __init__(
        self,
        optimizer: torch.optim.Optimizer,
        warmup_epochs: int,
        max_epochs: int,
        eta_min: float = 0.0,
        last_epoch: int = -1,
    ) -> None:
        self.warmup_epochs = warmup_epochs
        self.max_epochs = max_epochs
        self.eta_min = eta_min
        super().__init__(optimizer, last_epoch)

    def get_lr(self) -> list[float]:
        epoch = self.last_epoch
        if epoch < self.warmup_epochs:
            factor = (epoch + 1) / max(1, self.warmup_epochs)
            return [base_lr * factor for base_lr in self.base_lrs]

        progress = (epoch - self.warmup_epochs) / max(1, self.max_epochs - self.warmup_epochs)
        progress = min(1.0, max(0.0, progress))
        cosine = 0.5 * (1.0 + math.cos(math.pi * progress))
        return [self.eta_min + (base_lr - self.eta_min) * cosine for base_lr in self.base_lrs]