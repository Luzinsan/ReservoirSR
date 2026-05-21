from __future__ import annotations

import torch
import torch.nn as nn


class CharbonnierLoss(nn.Module):
    """Гладкая аппроксимация L1: sqrt((x-y)^2 + eps^2)."""

    def __init__(self, eps: float = 1.0e-3) -> None:
        super().__init__()
        self.eps2 = eps * eps

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        return torch.sqrt((pred - target) ** 2 + self.eps2).mean()