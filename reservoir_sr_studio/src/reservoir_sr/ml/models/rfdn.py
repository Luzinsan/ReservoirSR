from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class ESA(nn.Module):
    """Enhanced Spatial Attention."""

    def __init__(self, n_features: int):
        super().__init__()
        f = n_features // 4
        self.conv1 = nn.Conv2d(n_features, f, 1)
        self.conv_f = nn.Conv2d(f, f, 1)
        self.conv_max = nn.Conv2d(f, f, 3, padding=1)
        self.conv2 = nn.Conv2d(f, f, 3, stride=2, padding=1)
        self.conv3 = nn.Conv2d(f, f, 3, padding=1)
        self.conv3_ = nn.Conv2d(f, f, 3, padding=1)
        self.conv4 = nn.Conv2d(f, n_features, 1)
        self.sigmoid = nn.Sigmoid()
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        c1_ = self.conv1(x)
        c1 = self.conv2(c1_)
        v_max = F.max_pool2d(c1, kernel_size=7, stride=3)
        v_range = self.relu(self.conv_max(v_max))
        c3 = self.relu(self.conv3(v_range))
        c3 = self.conv3_(c3)
        c3 = F.interpolate(c3, size=(x.size(2), x.size(3)), mode="bilinear", align_corners=False)
        cf = self.conv_f(c1_)
        c4 = self.conv4(c3 + cf)
        return x * self.sigmoid(c4)


class RFDB(nn.Module):
    """Residual Feature Distillation Block."""

    def __init__(self, n_features: int, distill_rate: float = 0.5):
        super().__init__()
        self.dc = int(n_features * distill_rate)  # distilled
        self.rc = n_features                       # refined

        self.c1_d = nn.Conv2d(n_features, self.dc, 1)
        self.c1_r = nn.Conv2d(n_features, self.rc, 3, padding=1)
        self.c2_d = nn.Conv2d(self.rc, self.dc, 1)
        self.c2_r = nn.Conv2d(self.rc, self.rc, 3, padding=1)
        self.c3_d = nn.Conv2d(self.rc, self.dc, 1)
        self.c3_r = nn.Conv2d(self.rc, self.rc, 3, padding=1)
        self.c4 = nn.Conv2d(self.rc, self.dc, 3, padding=1)
        self.act = nn.LeakyReLU(0.05, inplace=True)
        self.c5 = nn.Conv2d(self.dc * 4, n_features, 1)
        self.esa = ESA(n_features)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        d1 = self.act(self.c1_d(x))
        r1 = self.act(self.c1_r(x) + x)

        d2 = self.act(self.c2_d(r1))
        r2 = self.act(self.c2_r(r1) + r1)

        d3 = self.act(self.c3_d(r2))
        r3 = self.act(self.c3_r(r2) + r2)

        d4 = self.act(self.c4(r3))
        out = torch.cat([d1, d2, d3, d4], dim=1)
        out = self.c5(out)
        return self.esa(out) + x


class RFDN(nn.Module):
    """Residual Feature Distillation Network for efficient SR."""

    def __init__(
        self,
        in_channels: int = 3,
        out_channels: int = 3,
        n_features: int = 50,
        n_blocks: int = 6,
        scale: int = 4,
        **kwargs,
    ):
        super().__init__()
        self.head = nn.Conv2d(in_channels, n_features, 3, padding=1)
        self.blocks = nn.ModuleList([RFDB(n_features) for _ in range(n_blocks)])
        self.fusion = nn.Conv2d(n_features * n_blocks, n_features, 1)
        self.body_tail = nn.Conv2d(n_features, n_features, 3, padding=1)

        # PixelShuffle upsample (scale=4 = 2 stages of ×2)
        layers: list[nn.Module] = []
        if scale == 4:
            for _ in range(2):
                layers.extend([
                    nn.Conv2d(n_features, n_features * 4, 3, padding=1),
                    nn.PixelShuffle(2),
                ])
        elif scale == 2:
            layers.extend([
                nn.Conv2d(n_features, n_features * 4, 3, padding=1),
                nn.PixelShuffle(2),
            ])
        else:
            raise NotImplementedError(f"RFDN supports scale=2,4. Got: {scale}")
        self.upsample = nn.Sequential(*layers)
        self.tail = nn.Conv2d(n_features, out_channels, 3, padding=1)

    def forward(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        x = batch["lr"]
        feat = self.head(x)

        outs = []
        h = feat
        for block in self.blocks:
            h = block(h)
            outs.append(h)
        fused = self.fusion(torch.cat(outs, dim=1))
        fused = self.body_tail(fused) + feat

        out = self.upsample(fused)
        return self.tail(out)