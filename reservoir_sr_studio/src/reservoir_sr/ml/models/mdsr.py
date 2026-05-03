from __future__ import annotations

import torch
import torch.nn as nn


class ResBlock(nn.Module):
    """Residual block without BatchNorm (as in EDSR/MDSR).

    Supports optional FiLM conditioning: when ``film_params`` is passed
    to ``forward``, an affine modulation is applied after the second conv.
    """

    def __init__(self, n_features: int, res_scale: float = 1.0):
        super().__init__()
        self.res_scale = res_scale
        self.body = nn.Sequential(
            nn.Conv2d(n_features, n_features, kernel_size=3, padding=1, bias=True),
            nn.ReLU(inplace=True),
            nn.Conv2d(n_features, n_features, kernel_size=3, padding=1, bias=True),
        )

    def forward(
        self,
        x: torch.Tensor,
        film_params: tuple[torch.Tensor, torch.Tensor] | None = None,
    ) -> torch.Tensor:
        out = self.body(x)
        if film_params is not None:
            gamma, beta = film_params
            out = gamma * out + beta
        return x + out.mul(self.res_scale)


class Upsampler(nn.Sequential):
    """PixelShuffle-based upsampling block."""

    def __init__(self, scale: int, n_features: int):
        layers: list[nn.Module] = []
        if (scale & (scale - 1)) == 0:
            for _ in range(int(scale).bit_length() - 1):
                layers.append(nn.Conv2d(n_features, n_features * 4, kernel_size=3, padding=1))
                layers.append(nn.PixelShuffle(2))
        elif scale == 3:
            layers.append(nn.Conv2d(n_features, n_features * 9, kernel_size=3, padding=1))
            layers.append(nn.PixelShuffle(3))
        else:
            raise NotImplementedError(f"Upsample scale {scale} is not supported.")
        super().__init__(*layers)


class ConditionEncoder(nn.Module):
    """MLP that maps a variable-length condition vector to a fixed embedding."""

    def __init__(self, condition_dim: int, embed_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(condition_dim, embed_dim),
            nn.ReLU(inplace=True),
            nn.Linear(embed_dim, embed_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class FiLMGenerator(nn.Module):
    """Produces per-block (gamma, beta) pairs from the condition embedding.

    gamma is initialised to 1 and beta to 0 so that FiLM starts
    as an identity transform.
    """

    def __init__(self, embed_dim: int, n_features: int, n_blocks: int):
        super().__init__()
        self.n_blocks = n_blocks
        self.n_features = n_features
        self.proj = nn.Linear(embed_dim, n_blocks * n_features * 2)
        self._init_identity()

    def _init_identity(self) -> None:
        nn.init.zeros_(self.proj.weight)
        bias = self.proj.bias.data.view(self.n_blocks, 2, self.n_features)
        bias[:, 0, :] = 1.0  # gamma
        bias[:, 1, :] = 0.0  # beta

    def forward(self, emb: torch.Tensor) -> list[tuple[torch.Tensor, torch.Tensor]]:
        raw = self.proj(emb)  # (B, n_blocks * n_features * 2)
        raw = raw.view(-1, self.n_blocks, 2, self.n_features)
        pairs: list[tuple[torch.Tensor, torch.Tensor]] = []
        for i in range(self.n_blocks):
            gamma = raw[:, i, 0, :].unsqueeze(-1).unsqueeze(-1)  # (B, C, 1, 1)
            beta = raw[:, i, 1, :].unsqueeze(-1).unsqueeze(-1)
            pairs.append((gamma, beta))
        return pairs


class MDSRBaseline(nn.Module):
    """Multiscale Deep Super-Resolution (MDSR) model.

    Works in two modes depending on ``condition_dim``:
    - **Unconditional** (``condition_dim=0``): pure image SR from ``lr`` only.
    - **Conditional** (``condition_dim>0``): each ResBlock is modulated via FiLM
      using the ``condition`` vector from the batch.
    """

    def __init__(
        self,
        in_channels: int = 3,
        out_channels: int = 3,
        n_features: int = 64,
        n_blocks: int = 16,
        scale: int = 4,
        res_scale: float = 1.0,
        condition_dim: int = 0,
        condition_embed_dim: int = 256,
        **kwargs,
    ):
        super().__init__()
        self.condition_dim = condition_dim
        self.n_blocks = n_blocks

        self.head = nn.Conv2d(in_channels, n_features, kernel_size=3, padding=1)

        self.pre_process = nn.Sequential(
            nn.Conv2d(n_features, n_features, kernel_size=5, padding=2),
            nn.Conv2d(n_features, n_features, kernel_size=5, padding=2),
        )

        self.blocks = nn.ModuleList(
            [ResBlock(n_features, res_scale) for _ in range(n_blocks)]
        )
        self.body_tail = nn.Conv2d(n_features, n_features, kernel_size=3, padding=1)

        if condition_dim > 0:
            self.cond_encoder = ConditionEncoder(condition_dim, condition_embed_dim)
            self.film_gen = FiLMGenerator(condition_embed_dim, n_features, n_blocks)

        self.upsample = Upsampler(scale, n_features)
        self.tail = nn.Conv2d(n_features, out_channels, kernel_size=3, padding=1)

    def forward(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        x = batch["lr"]

        film_pairs: list[tuple[torch.Tensor, torch.Tensor]] | None = None
        if self.condition_dim > 0 and "condition" in batch:
            emb = self.cond_encoder(batch["condition"])
            film_pairs = self.film_gen(emb)

        x = self.head(x)
        x = self.pre_process(x)

        res = x
        for i, block in enumerate(self.blocks):
            fp = film_pairs[i] if film_pairs is not None else None
            res = block(res, fp)
        res = self.body_tail(res)
        x = x + res

        x = self.upsample(x)
        return self.tail(x)
