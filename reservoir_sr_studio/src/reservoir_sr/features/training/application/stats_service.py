from __future__ import annotations

from pathlib import Path

import numpy as np

from reservoir_sr.domain.training.normalization_stats import (
    FeatureStats,
    NormalizationStats,
)
from reservoir_sr.infrastructure.storage.sr_archive_io import load_sr_archive


class _Accumulator:
    """Running min / max / mean / variance in both linear and log domains."""

    __slots__ = (
        "vmin", "vmax", "vsum", "vsum_sq", "count",
        "log_min", "log_max", "log_sum", "log_sum_sq", "has_nonpositive",
    )

    def __init__(self) -> None:
        self.vmin = np.inf
        self.vmax = -np.inf
        self.vsum = 0.0
        self.vsum_sq = 0.0
        self.count = 0

        self.log_min = np.inf
        self.log_max = -np.inf
        self.log_sum = 0.0
        self.log_sum_sq = 0.0
        self.has_nonpositive = False

    def update(self, arr: np.ndarray) -> None:
        flat = arr.astype(np.float64).ravel()
        self.vmin = min(self.vmin, float(flat.min()))
        self.vmax = max(self.vmax, float(flat.max()))
        self.vsum += float(flat.sum())
        self.vsum_sq += float((flat * flat).sum())
        self.count += flat.size

        if self.has_nonpositive:
            return
        if float(flat.min()) <= 0.0:
            self.has_nonpositive = True
            return
        log_flat = np.log(flat)
        self.log_min = min(self.log_min, float(log_flat.min()))
        self.log_max = max(self.log_max, float(log_flat.max()))
        self.log_sum += float(log_flat.sum())
        self.log_sum_sq += float((log_flat * log_flat).sum())

    def build(self) -> FeatureStats:
        n = max(self.count, 1)
        mean = self.vsum / n
        var = self.vsum_sq / n - mean * mean

        log_min: float | None = None
        log_max: float | None = None
        log_mean: float | None = None
        log_std: float | None = None

        if not self.has_nonpositive and self.count > 0:
            log_min = self.log_min
            log_max = self.log_max
            log_mean = self.log_sum / n
            log_var = self.log_sum_sq / n - log_mean * log_mean
            log_std = max(log_var, 0.0) ** 0.5

        return FeatureStats(
            min=self.vmin,
            max=self.vmax,
            mean=mean,
            std=max(var, 0.0) ** 0.5,
            log_min=log_min,
            log_max=log_max,
            log_mean=log_mean,
            log_std=log_std,
        )


def compute_stats(archive_paths: list[Path]) -> NormalizationStats:
    """Single pass over archives to compute per-parameter statistics."""
    lr_acc: dict[str, _Accumulator] = {}
    hr_acc: dict[str, _Accumulator] = {}
    dyn_acc: dict[str, _Accumulator] = {}
    stat_acc: dict[str, _Accumulator] = {}
    lay_acc: dict[str, _Accumulator] = {}

    for path in archive_paths:
        arrays, meta = load_sr_archive(path)
        channels: list[str] = meta["channels"]
        lr = arrays["lr_fields"]   # (T, C, Z, X)
        hr = arrays["hr_fields"]

        for c, ch in enumerate(channels):
            lr_acc.setdefault(ch, _Accumulator()).update(lr[:, c])
            hr_acc.setdefault(ch, _Accumulator()).update(hr[:, c])

        dyn = arrays["dynamic_scalars"]  # (T, F)
        for i, name in enumerate(meta["dynamic_scalar_names"]):
            dyn_acc.setdefault(name, _Accumulator()).update(dyn[:, i])

        stat = arrays["static_scalars"]  # (F,)
        for i, name in enumerate(meta["static_scalar_names"]):
            stat_acc.setdefault(name, _Accumulator()).update(stat[i : i + 1])

        lay = arrays["layer_scalars"]  # (5, F)
        for j, name in enumerate(meta["layer_scalar_names"]):
            lay_acc.setdefault(name, _Accumulator()).update(lay[:, j])

    def _build(acc: dict[str, _Accumulator]) -> dict[str, FeatureStats]:
        return {name: a.build() for name, a in acc.items()}

    return NormalizationStats(
        lr_fields=_build(lr_acc),
        hr_fields=_build(hr_acc),
        dynamic=_build(dyn_acc),
        static=_build(stat_acc),
        layers=_build(lay_acc),
    )
