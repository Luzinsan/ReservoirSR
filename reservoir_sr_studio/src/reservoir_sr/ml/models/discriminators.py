from __future__ import annotations

import torch
import torch.nn as nn
from torch.nn.utils import spectral_norm


def _conv_block(
    in_channels: int,
    out_channels: int,
    stride: int,
    use_bn: bool,
    use_spectral_norm: bool,
) -> nn.Sequential:
    conv = nn.Conv2d(in_channels, out_channels, 3, stride, 1, bias=not use_bn)
    if use_spectral_norm:
        conv = spectral_norm(conv)

    layers: list[nn.Module] = [conv]
    if use_bn:
        layers.append(nn.BatchNorm2d(out_channels))
    layers.append(nn.LeakyReLU(0.2, inplace=True))
    return nn.Sequential(*layers)


class _BaseDiscriminator(nn.Module):
    def __init__(
        self,
        in_channels: int = 3,
        base_channels: int = 64,
        max_channels: int = 512,
        use_bn: bool = True,
        use_spectral_norm: bool = False,
    ):
        super().__init__()
        channels = [base_channels, base_channels, base_channels * 2, base_channels * 2, base_channels * 4, base_channels * 4, base_channels * 8, base_channels * 8]
        channels = [min(c, max_channels) for c in channels]
        strides = [1, 2, 1, 2, 1, 2, 1, 2]

        stem = nn.Conv2d(in_channels, channels[0], 3, 1, 1, bias=True)
        if use_spectral_norm:
            stem = spectral_norm(stem)

        layers: list[nn.Module] = [
            stem,
            nn.LeakyReLU(0.2, inplace=True),
        ]
        prev = channels[0]
        for c, s in zip(channels[1:], strides[1:]):
            layers.append(_conv_block(prev, c, s, use_bn=use_bn, use_spectral_norm=use_spectral_norm))
            prev = c

        self.features = nn.Sequential(*layers)
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(prev, max(128, prev // 2)),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(max(128, prev // 2), 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.features(x)
        return self.classifier(feat)


class SRResNetDiscriminator(_BaseDiscriminator):
    """SRGAN-style discriminator for MSRResNet generator."""

    def __init__(self, in_channels: int = 3, base_channels: int = 64, **kwargs):
        super().__init__(
            in_channels=in_channels,
            base_channels=base_channels,
            use_bn=True,
            use_spectral_norm=False,
        )


class ESRGANDiscriminator(_BaseDiscriminator):
    """ESRGAN-oriented discriminator (BN-free + spectral norm)."""

    def __init__(self, in_channels: int = 3, base_channels: int = 64, **kwargs):
        super().__init__(
            in_channels=in_channels,
            base_channels=base_channels,
            use_bn=False,
            use_spectral_norm=True,
        )
