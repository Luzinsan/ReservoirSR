from __future__ import annotations

from typing import Any

import numpy as np


_METRIC_NAMES = ("time", "AI", "AIT", "AIB")


class LoadedDataset:
    """Immutable view over a loaded simulation archive with typed data access."""

    __slots__ = ("_arrays", "_metadata", "_channel_index", "_dynamic_index")

    def __init__(self, arrays: dict[str, np.ndarray], metadata: dict[str, Any]) -> None:
        self._arrays = arrays
        self._metadata = metadata
        self._channel_index: dict[str, int] = {
            name: idx for idx, name in enumerate(metadata.get("channels", []))
        }
        self._dynamic_index: dict[str, int] = {
            name: idx for idx, name in enumerate(metadata.get("dynamic_scalar_names", []))
        }

    # ------------------------------------------------------------------
    # Scalars
    # ------------------------------------------------------------------

    @property
    def total_steps(self) -> int:
        return int(self._arrays["dynamic_scalars"].shape[0])

    def dynamic_value(self, name: str, step: int) -> float:
        return float(self._arrays["dynamic_scalars"][step, self._dynamic_index[name]])

    # ------------------------------------------------------------------
    # Field arrays
    # ------------------------------------------------------------------

    def field_arrays(self, step: int, resolution: str) -> dict[str, np.ndarray]:
        key = "lr_fields" if resolution == "lr" else "hr_fields"
        tensor = self._arrays[key][step]
        return {
            name: tensor[idx].astype(np.float64, copy=False)
            for name, idx in self._channel_index.items()
        }

    def grid_dims(self, resolution: str) -> tuple[int, int]:
        key = "lr_fields" if resolution == "lr" else "hr_fields"
        _, _, nz, nx = self._arrays[key].shape
        return int(nz), int(nx)

    def scene_dims(self) -> tuple[float, float]:
        lr_grid = self._metadata.get("lr_grid", {})
        return float(lr_grid.get("nx", 100)), float(lr_grid.get("nz", 1))

    # ------------------------------------------------------------------
    # Metrics (numpy views, O(1))
    # ------------------------------------------------------------------

    def metrics_arrays(
        self, up_to_step: int,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        scalars = self._arrays["dynamic_scalars"][:up_to_step + 1]
        ix = self._dynamic_index
        return tuple(scalars[:, ix[name]] for name in _METRIC_NAMES)  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Info (for labels)
    # ------------------------------------------------------------------

    @property
    def channels(self) -> list[str]:
        return self._metadata.get("channels", [])

    @property
    def archive_count(self) -> int:
        return len(self._metadata.get("source_archives", []))

    @property
    def lr_shape(self) -> tuple[int, ...]:
        return tuple(self._arrays["lr_fields"].shape)

    @property
    def hr_shape(self) -> tuple[int, ...]:
        return tuple(self._arrays["hr_fields"].shape)

    @property
    def dynamic_shape(self) -> tuple[int, ...]:
        return tuple(self._arrays["dynamic_scalars"].shape)

    @property
    def static_shape(self) -> tuple[int, ...]:
        return tuple(self._arrays["static_scalars"].shape)

    @property
    def layer_shape(self) -> tuple[int, ...]:
        return tuple(self._arrays["layer_scalars"].shape)
