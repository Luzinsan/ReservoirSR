from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

import numpy as np


_METRIC_NAMES = ("time", "AI", "AIT", "AIB")

# ------------------------------------------------------------------
# Condition extraction types
# ------------------------------------------------------------------

ConditionGroup = Literal["dynamic", "static", "layers"]

ConditionSpec = (
    tuple[ConditionGroup, ...]
    | dict[ConditionGroup, list[str] | None]
)


def normalize_condition_spec(
    spec: ConditionSpec,
) -> dict[ConditionGroup, list[str] | None]:
    """Convert tuple shorthand to the canonical dict form."""
    if isinstance(spec, dict):
        return spec
    return {group: None for group in spec}


class LoadedDataset:
    """Immutable view over a loaded simulation archive with typed data access."""

    __slots__ = (
        "_arrays", "_metadata", "_channel_index",
        "_dynamic_index", "_static_index", "_layer_feature_index",
    )

    CONDITION_EXTRACTORS: dict[
        ConditionGroup,
        Callable[[LoadedDataset, int, list[str] | None], np.ndarray],
    ] = {}  # populated after class body

    def __init__(self, arrays: dict[str, np.ndarray], metadata: dict[str, Any]) -> None:
        self._arrays = arrays
        self._metadata = metadata
        self._channel_index: dict[str, int] = {
            name: idx for idx, name in enumerate(metadata.get("channels", []))
        }
        self._dynamic_index: dict[str, int] = {
            name: idx for idx, name in enumerate(metadata.get("dynamic_scalar_names", []))
        }
        self._static_index: dict[str, int] = {
            name: idx for idx, name in enumerate(metadata.get("static_scalar_names", []))
        }
        self._layer_feature_index: dict[str, int] = {
            name: idx for idx, name in enumerate(metadata.get("layer_scalar_names", []))
        }

    # ------------------------------------------------------------------
    # Scalars (single-value, for UI)
    # ------------------------------------------------------------------

    @property
    def total_steps(self) -> int:
        return int(self._arrays["dynamic_scalars"].shape[0])

    def dynamic_value(self, name: str, step: int) -> float:
        return float(self._arrays["dynamic_scalars"][step, self._dynamic_index[name]])

    # ------------------------------------------------------------------
    # Field arrays
    # ------------------------------------------------------------------

    def field_tensor(self, step: int, resolution: str) -> np.ndarray:
        """Return a single frame as a contiguous (3, Z, X) float32 array."""
        key = "lr_fields" if resolution == "lr" else "hr_fields"
        return np.ascontiguousarray(self._arrays[key][step], dtype=np.float32)

    def field_arrays(self, step: int, resolution: str) -> dict[str, np.ndarray]:
        key = "lr_fields" if resolution == "lr" else "hr_fields"
        tensor = self._arrays[key][step]
        return {
            name: tensor[idx].astype(np.float64, copy=False)
            for name, idx in self._channel_index.items()
        }


    # ------------------------------------------------------------------
    # Condition scalars (for training pipeline)
    # ------------------------------------------------------------------

    def _pick(self, arr: np.ndarray, index: dict[str, int], names: list[str] | None) -> np.ndarray:
        return arr if names is None else arr[..., [index[n] for n in names]]

    def dynamic_scalars_at(self, step: int, names: list[str] | None = None) -> np.ndarray:
        """(F,) float32 -- dynamic scalars at a given step, optionally filtered."""
        return self._pick(self._arrays["dynamic_scalars"][step], self._dynamic_index, names)

    def static_scalars(self, names: list[str] | None = None) -> np.ndarray:
        """(F,) float32 -- global simulation parameters, optionally filtered."""
        return self._pick(self._arrays["static_scalars"], self._static_index, names)

    def layer_scalars_flat(self, names: list[str] | None = None) -> np.ndarray:
        """(5 * F,) float32 -- layer features flattened, optionally filtered."""
        return self._pick(self._arrays["layer_scalars"], self._layer_feature_index, names).reshape(-1)

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


LoadedDataset.CONDITION_EXTRACTORS = {
    "dynamic": lambda ds, t, names: ds.dynamic_scalars_at(t, names),
    "static":  lambda ds, t, names: ds.static_scalars(names),
    "layers":  lambda ds, t, names: ds.layer_scalars_flat(names),
}
