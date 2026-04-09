from __future__ import annotations

from typing import Literal, get_args

import numpy as np

from reservoir_sr.domain.training.norm_config import (
    NormConfig,
    NormStrategy,
    resolve_strategy,
    validate_config,
)
from reservoir_sr.domain.training.normalization_stats import (
    FeatureStats,
    NormalizationStats,
)
from reservoir_sr.ml.data.loaded_archive import ConditionGroup


class Normalizer:
    """Precomputed normalizer for the SR pipeline.

    Builds shift/scale/log_mask arrays once at init for **all** field
    channels and **all** scalar parameters present in stats.
    Hot-path methods are pure arithmetic.
    """

    _EPS = 1e-8
    _SCALAR_SECTIONS: tuple[str, ...] = get_args(ConditionGroup)

    def __init__(
        self,
        stats: NormalizationStats,
        config: NormConfig | None = None,
        n_layers: int = 5,
    ) -> None:
        self._config = config or NormConfig()
        self._stats = stats
        self._n_layers = n_layers

        validate_config(self._config, {
            "fields": set(stats.lr_fields.keys()),
            "dynamic": set(stats.dynamic.keys()),
            "static": set(stats.static.keys()),
            "layers": set(stats.layers.keys()),
        })

        self._lr_shift, self._lr_scale, self._lr_log = self._build_field_params("lr")
        self._hr_shift, self._hr_scale, self._hr_log = self._build_field_params("hr")

        self._scalar_shift, self._scalar_scale, self._scalar_log, self._scalar_index = (
            self._build_scalar_params()
        )

    # ------------------------------------------------------------------
    # Fields  (C, Z, X) → (C, Z, X)
    # ------------------------------------------------------------------

    def normalize_fields(
        self, arr: np.ndarray, resolution: Literal["lr", "hr"],
    ) -> np.ndarray:
        shift, scale, log_mask = self._field_triple(resolution)
        if log_mask is not None:
            arr = np.where(log_mask, np.log(np.maximum(arr, self._EPS)), arr)
        return (arr - shift) / scale

    def denormalize_fields(
        self, arr: np.ndarray, resolution: Literal["lr", "hr"],
    ) -> np.ndarray:
        shift, scale, log_mask = self._field_triple(resolution)
        out = arr * scale + shift
        if log_mask is not None:
            out = np.where(log_mask, np.exp(np.where(log_mask, out, 0.0)), out)
        return out

    # ------------------------------------------------------------------
    # Scalars  (F,) → (F,)
    # ------------------------------------------------------------------

    def normalize_scalars(
        self,
        arr: np.ndarray,
        group: ConditionGroup,
        names: list[str] | None = None,
    ) -> np.ndarray:
        shift, scale, mask = self._scalar_triple(group, names)
        if mask is not None:
            arr = np.where(mask, np.log(np.maximum(arr, self._EPS)), arr)
        return (arr - shift) / scale

    def denormalize_scalars(
        self,
        arr: np.ndarray,
        group: ConditionGroup,
        names: list[str] | None = None,
    ) -> np.ndarray:
        shift, scale, mask = self._scalar_triple(group, names)
        out = arr * scale + shift
        if mask is not None:
            out = np.where(mask, np.exp(np.where(mask, out, 0.0)), out)
        return out

    # ------------------------------------------------------------------
    # Init helpers
    # ------------------------------------------------------------------

    def _build_field_params(
        self, resolution: Literal["lr", "hr"],
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
        """Build ``(C, 1, 1)`` shift/scale/log_mask for one resolution."""
        group = self._stats.lr_fields if resolution == "lr" else self._stats.hr_fields
        strategies = [resolve_strategy(self._config, "fields", ch) for ch in group]
        pairs = [self._shift_scale(fs, s) for fs, s in zip(group.values(), strategies)]

        shift = np.array([p[0] for p in pairs], dtype=np.float32).reshape(-1, 1, 1)
        scale = np.array([p[1] for p in pairs], dtype=np.float32).reshape(-1, 1, 1)
        mask = self._log_mask(strategies)
        if mask is not None:
            mask = mask.reshape(-1, 1, 1)
        return shift, scale, mask

    def _build_scalar_params(
        self,
    ) -> tuple[
        dict[str, np.ndarray],
        dict[str, np.ndarray],
        dict[str, np.ndarray | None],
        dict[str, dict[str, int]],
    ]:
        """Build base ``(F,)`` shift/scale/log_mask per scalar section.

        Arrays are stored **untiled** — tiling for layers happens
        inside ``_scalar_triple`` for name-based filtering.
        """
        shifts: dict[str, np.ndarray] = {}
        scales: dict[str, np.ndarray] = {}
        logs: dict[str, np.ndarray | None] = {}
        indices: dict[str, dict[str, int]] = {}

        for section in self._SCALAR_SECTIONS:
            group_stats: dict[str, FeatureStats] = getattr(self._stats, section)
            ordered = list(group_stats.keys())
            strategies = [resolve_strategy(self._config, section, n) for n in ordered]
            pairs = [self._shift_scale(group_stats[n], s) for n, s in zip(ordered, strategies)]

            shifts[section] = np.array([p[0] for p in pairs], dtype=np.float32)
            scales[section] = np.array([p[1] for p in pairs], dtype=np.float32)
            logs[section] = self._log_mask(strategies)
            indices[section] = {n: i for i, n in enumerate(ordered)}

        return shifts, scales, logs, indices

    def _field_triple(
        self, resolution: Literal["lr", "hr"],
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
        if resolution == "lr":
            return self._lr_shift, self._lr_scale, self._lr_log
        return self._hr_shift, self._hr_scale, self._hr_log

    def _scalar_triple(
        self,
        group: ConditionGroup,
        names: list[str] | None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
        shift = self._scalar_shift[group]
        scale = self._scalar_scale[group]
        mask = self._scalar_log[group]

        if names is not None:
            idx = [self._scalar_index[group][n] for n in names]
            shift = shift[idx]
            scale = scale[idx]
            if mask is not None:
                mask = mask[idx]
                if not mask.any():
                    mask = None

        if group == "layers":
            shift = np.tile(shift, self._n_layers)
            scale = np.tile(scale, self._n_layers)
            if mask is not None:
                mask = np.tile(mask, self._n_layers)

        return shift, scale, mask

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _shift_scale(fs: FeatureStats, strategy: NormStrategy) -> tuple[float, float]:
        eps = Normalizer._EPS
        if strategy == "minmax":
            return fs.min, max(fs.max - fs.min, eps)
        if strategy == "zscore":
            return fs.mean, max(fs.std, eps)
        if strategy == "log_minmax":
            assert fs.log_min is not None and fs.log_max is not None
            return fs.log_min, max(fs.log_max - fs.log_min, eps)
        if strategy == "log_zscore":
            assert fs.log_mean is not None and fs.log_std is not None
            return fs.log_mean, max(fs.log_std, eps)
        return 0.0, 1.0  # "none"

    @staticmethod
    def _log_mask(strategies: list[NormStrategy]) -> np.ndarray | None:
        flags = [s in ("log_minmax", "log_zscore") for s in strategies]
        if not any(flags):
            return None
        return np.array(flags, dtype=bool)
