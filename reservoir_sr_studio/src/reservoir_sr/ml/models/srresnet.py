from __future__ import annotations

import torch
import torch.nn as nn


class ResidualBlock(nn.Module):
    """Residual block without BatchNorm (MSRResNet-style)."""

    def __init__(self, n_features: int, res_scale: float = 1.0):
        super().__init__()
        self.res_scale = res_scale
        self.conv1 = nn.Conv2d(n_features, n_features, 3, 1, 1, bias=True)
        self.conv2 = nn.Conv2d(n_features, n_features, 3, 1, 1, bias=True)
        self.act = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = self.conv2(self.act(self.conv1(x)))
        return x + residual * self.res_scale


class UpsampleBlock(nn.Module):
    """PixelShuffle upsample block."""

    def __init__(self, n_features: int, scale: int):
        super().__init__()
        self.conv = nn.Conv2d(n_features, n_features * (scale**2), 3, 1, 1, bias=True)
        self.shuffle = nn.PixelShuffle(scale)
        self.act = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.act(self.shuffle(self.conv(x)))


class MSRResNet(nn.Module):
    """Light SR generator for GAN/SR training without spatial compression.

    Uses only stride-1 convolutions in feature space and PixelShuffle at the tail.
    """

    def __init__(
        self,
        in_channels: int = 3,
        out_channels: int = 3,
        n_features: int = 64,
        n_blocks: int = 8,
        scale: int = 4,
        res_scale: float = 1.0,
        **kwargs,
    ):
        super().__init__()

        if scale not in (2, 3, 4):
            raise NotImplementedError(f"MSRResNet supports scales 2, 3, 4. Got: {scale}")

        self.head = nn.Conv2d(in_channels, n_features, 3, 1, 1, bias=True)
        self.body = nn.Sequential(*[ResidualBlock(n_features, res_scale) for _ in range(n_blocks)])
        self.body_tail = nn.Conv2d(n_features, n_features, 3, 1, 1, bias=True)

        if scale in (2, 3):
            self.upsample = nn.Sequential(UpsampleBlock(n_features, scale))
        else:
            self.upsample = nn.Sequential(
                UpsampleBlock(n_features, 2),
                UpsampleBlock(n_features, 2),
            )

        self.tail = nn.Conv2d(n_features, out_channels, 3, 1, 1, bias=True)

    def forward(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        x = batch["lr"]
        feat = self.head(x)
        body = self.body_tail(self.body(feat))
        feat = feat + body
        feat = self.upsample(feat)
        return self.tail(feat)
