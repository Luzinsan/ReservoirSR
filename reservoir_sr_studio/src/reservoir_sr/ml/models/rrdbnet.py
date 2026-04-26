from __future__ import annotations

import torch
import torch.nn as nn


class ResidualDenseBlock(nn.Module):
    """5-layer dense block with residual scaling (as in ESRGAN).

    Each conv receives the concatenation of the original input and
    all preceding conv outputs.  Growth rate ``gc`` controls how many
    channels each internal layer adds.
    """

    def __init__(self, n_features: int = 64, growth_channels: int = 32, res_scale: float = 0.2):
        super().__init__()
        gc = growth_channels
        self.conv1 = nn.Conv2d(n_features, gc, 3, 1, 1, bias=True)
        self.conv2 = nn.Conv2d(n_features + gc, gc, 3, 1, 1, bias=True)
        self.conv3 = nn.Conv2d(n_features + 2 * gc, gc, 3, 1, 1, bias=True)
        self.conv4 = nn.Conv2d(n_features + 3 * gc, gc, 3, 1, 1, bias=True)
        self.conv5 = nn.Conv2d(n_features + 4 * gc, n_features, 3, 1, 1, bias=True)
        self.act = nn.LeakyReLU(negative_slope=0.2, inplace=True)
        self.res_scale = res_scale

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x1 = self.act(self.conv1(x))
        x2 = self.act(self.conv2(torch.cat((x, x1), 1)))
        x3 = self.act(self.conv3(torch.cat((x, x1, x2), 1)))
        x4 = self.act(self.conv4(torch.cat((x, x1, x2, x3), 1)))
        x5 = self.conv5(torch.cat((x, x1, x2, x3, x4), 1))
        return x + x5 * self.res_scale


class RRDB(nn.Module):
    """Residual-in-Residual Dense Block: 3 cascaded RDBs with outer residual."""

    def __init__(self, n_features: int = 64, growth_channels: int = 32, res_scale: float = 0.2):
        super().__init__()
        self.rdb1 = ResidualDenseBlock(n_features, growth_channels, res_scale)
        self.rdb2 = ResidualDenseBlock(n_features, growth_channels, res_scale)
        self.rdb3 = ResidualDenseBlock(n_features, growth_channels, res_scale)
        self.res_scale = res_scale

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.rdb1(x)
        out = self.rdb2(out)
        out = self.rdb3(out)
        return x + out * self.res_scale


class RRDBNet(nn.Module):
    """ESRGAN generator based on Residual-in-Residual Dense Blocks.

    Unconditional SR: predicts HR fields from LR fields only.
    Accepts the full batch dict from the dataloader, uses only ``lr``.

    Architecture:
        head  → 23 × RRDB → body_tail + global skip →
        2 × (Conv + PixelShuffle(2) + LeakyReLU) → hr_conv → tail
    """

    def __init__(
        self,
        in_channels: int = 3,
        out_channels: int = 3,
        n_features: int = 64,
        n_blocks: int = 23,
        growth_channels: int = 32,
        scale: int = 4,
        res_scale: float = 0.2,
        **kwargs,
    ):
        super().__init__()

        self.head = nn.Conv2d(in_channels, n_features, 3, 1, 1, bias=True)

        self.blocks = nn.ModuleList(
            [RRDB(n_features, growth_channels, res_scale) for _ in range(n_blocks)]
        )
        self.body_tail = nn.Conv2d(n_features, n_features, 3, 1, 1, bias=True)

        # PixelShuffle upsampling: two ×2 stages for ×4 total
        self.up1_conv = nn.Conv2d(n_features, n_features * 4, 3, 1, 1, bias=True)
        self.up1_shuffle = nn.PixelShuffle(2)
        self.up2_conv = nn.Conv2d(n_features, n_features * 4, 3, 1, 1, bias=True)
        self.up2_shuffle = nn.PixelShuffle(2)

        self.hr_conv = nn.Conv2d(n_features, n_features, 3, 1, 1, bias=True)
        self.tail = nn.Conv2d(n_features, out_channels, 3, 1, 1, bias=True)

        self.act = nn.LeakyReLU(negative_slope=0.2, inplace=True)

        if scale != 4:
            raise NotImplementedError(
                f"RRDBNet only supports scale=4, got {scale}. "
                "Adjust the upsampling stages for other factors."
            )

    def forward(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        x = batch["lr"]

        head = self.head(x)

        body = head
        for block in self.blocks:
            body = block(body)
        body = self.body_tail(body)
        feat = head + body

        feat = self.act(self.up1_shuffle(self.up1_conv(feat)))
        feat = self.act(self.up2_shuffle(self.up2_conv(feat)))

        feat = self.act(self.hr_conv(feat))
        return self.tail(feat)
