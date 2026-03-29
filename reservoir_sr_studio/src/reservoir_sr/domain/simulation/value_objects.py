from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np

from reservoir_sr.domain.simulation.config_models import SimulationConfig


# ------------------------------------------------------------------
# Sampling / Campaign
# ------------------------------------------------------------------


class SamplingScale(StrEnum):
    LINEAR = "linear"
    LOG10 = "log10"


@dataclass(frozen=True)
class ParameterRange:
    name: str
    low: float
    high: float
    scale: SamplingScale = SamplingScale.LINEAR
    integer: bool = False


@dataclass(frozen=True)
class SimulationCampaignCase:
    case_id: str
    config: SimulationConfig


# ------------------------------------------------------------------
# Metrics / Fields
# ------------------------------------------------------------------


@dataclass
class MetricsSnapshot:
    """Временные ряды метрик для графиков.

    Поля принимают list[float] (runtime, инкрементальный append)
    или np.ndarray views (dataset, O(1) zero-copy).
    pyqtgraph setData принимает оба формата нативно.
    """

    time: list[float] | np.ndarray = field(default_factory=list)
    ai: list[float] | np.ndarray = field(default_factory=list)
    ait: list[float] | np.ndarray = field(default_factory=list)
    aib: list[float] | np.ndarray = field(default_factory=list)

    def append(self, t: float, ai: float, ait: float, aib: float) -> None:
        self.time.append(t)  # type: ignore[union-attr]
        self.ai.append(ai)  # type: ignore[union-attr]
        self.ait.append(ait)  # type: ignore[union-attr]
        self.aib.append(aib)  # type: ignore[union-attr]

    def clear(self) -> None:
        self.time = []
        self.ai = []
        self.ait = []
        self.aib = []


@dataclass
class FieldSnapshot:
    """Снимок полей для отрисовки — каналы + размеры сцены + опциональные метрики."""

    fields: dict[str, np.ndarray]
    scene_dims: tuple[float, float]
    metrics: MetricsSnapshot | None = None
    layer_boundaries: np.ndarray | None = None
