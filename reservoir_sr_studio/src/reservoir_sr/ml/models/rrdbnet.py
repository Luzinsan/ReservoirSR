from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class ResidualDenseBlock(nn.Module):
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
        self._init_weights()

    def _init_weights(self) -> None:
        for m in [self.conv1, self.conv2, self.conv3, self.conv4, self.conv5]:
            nn.init.kaiming_normal_(m.weight, a=0.2, mode="fan_in", nonlinearity="leaky_relu")
            m.weight.data *= 0.1
            if m.bias is not None:
                nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x1 = self.act(self.conv1(x))
        x2 = self.act(self.conv2(torch.cat((x, x1), 1)))
        x3 = self.act(self.conv3(torch.cat((x, x1, x2), 1)))
        x4 = self.act(self.conv4(torch.cat((x, x1, x2, x3), 1)))
        x5 = self.conv5(torch.cat((x, x1, x2, x3, x4), 1))
        return x + x5 * self.res_scale


class RRDB(nn.Module):
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

    def __init__(
        self,
        in_channels: int = 3,
        out_channels: int = 3,
        n_features: int = 64,
        n_blocks: int = 23,
        growth_channels: int = 32,
        scale: int = 4,
        res_scale: float = 0.2,
        unshuffle_factor: int = 2,
        **kwargs,
    ):
        super().__init__()
        if scale != 4:
            raise NotImplementedError(f"RRDBNet supports scale=4 only, got {scale}.")

        self.unshuffle_factor = unshuffle_factor
        self.unshuffle = nn.PixelUnshuffle(unshuffle_factor) if unshuffle_factor > 1 else nn.Identity()
        head_in = in_channels * (unshuffle_factor ** 2)

        self.head = nn.Conv2d(head_in, n_features, 3, 1, 1, bias=True)
        self.blocks = nn.ModuleList(
            [RRDB(n_features, growth_channels, res_scale) for _ in range(n_blocks)]
        )
        self.body_tail = nn.Conv2d(n_features, n_features, 3, 1, 1, bias=True)

        total_up = scale * unshuffle_factor
        n_up = int(total_up).bit_length() - 1 
        self.upsample = nn.Sequential()
        for i in range(n_up):
            self.upsample.add_module(f"up_conv_{i}", nn.Conv2d(n_features, n_features * 4, 3, 1, 1))
            self.upsample.add_module(f"up_shuf_{i}", nn.PixelShuffle(2))
            self.upsample.add_module(f"up_act_{i}", nn.LeakyReLU(0.2, inplace=True))

        self.hr_conv = nn.Conv2d(n_features, n_features, 3, 1, 1, bias=True)
        self.tail = nn.Conv2d(n_features, out_channels, 3, 1, 1, bias=True)
        self.act = nn.LeakyReLU(0.2, inplace=True)

    def forward(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        x = batch["lr"]
        x = self.unshuffle(x)

        head = self.head(x)
        body = head
        for block in self.blocks:
            body = block(body)
        body = self.body_tail(body)
        feat = head + body

        feat = self.upsample(feat)
        feat = self.act(self.hr_conv(feat))
        return self.tail(feat)