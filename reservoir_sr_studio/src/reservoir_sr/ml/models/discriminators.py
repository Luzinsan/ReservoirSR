from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.utils.parametrizations import spectral_norm


class ResidualFieldDiscriminator(nn.Module):
    """Дискриминатор на residual-сигнале."""

    def __init__(self, in_channels: int = 3, base_channels: int = 64, n_layers: int = 3):
        super().__init__()
        layers: list[nn.Module] = [
            spectral_norm(nn.Conv2d(in_channels, base_channels, 3, 1, 1, bias=True)),
            nn.LeakyReLU(0.2, inplace=True),
        ]
        ch = base_channels
        for _ in range(n_layers):
            next_ch = min(ch * 2, 512)
            layers += [
                spectral_norm(nn.Conv2d(ch, next_ch, 3, 2, 1, bias=True)),
                nn.LeakyReLU(0.2, inplace=True),
                spectral_norm(nn.Conv2d(next_ch, next_ch, 3, 1, 1, bias=True)),
                nn.LeakyReLU(0.2, inplace=True),
            ]
            ch = next_ch
        layers.append(spectral_norm(nn.Conv2d(ch, 1, 1, 1, 0, bias=True)))
        self.net = nn.Sequential(*layers)

    def forward(self, field: torch.Tensor, lr: torch.Tensor) -> torch.Tensor:
        """field: (B, C, H, W) — SR или HR. lr: (B, C, H/4, W/4)."""
        bicubic = F.interpolate(lr, size=field.shape[-2:], mode="bicubic", align_corners=False)
        residual = field - bicubic
        with torch.amp.autocast("cuda", enabled=False):
            return self.net(residual.float()).flatten(1)
