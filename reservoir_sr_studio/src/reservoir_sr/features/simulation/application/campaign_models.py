from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from reservoir_sr.domain.simulation.config_models import SimulationConfig


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
class SimulationCampaignRequest:
    campaign_id: str
    sample_count: int
    steps: int
    lr_nx: int
    hr_nx: int
    fixed_tu_seconds: float
    fixed_epsp: float
    seed: int
    base_config: SimulationConfig
    ranges: tuple[ParameterRange, ...]


@dataclass(frozen=True)
class SimulationCampaignCase:
    case_id: str
    config: SimulationConfig


@dataclass(frozen=True)
class RejectedCase:
    case_id: str
    reason: str


@dataclass(frozen=True)
class SimulationCampaignPlan:
    cases: list[SimulationCampaignCase]
    rejected: list[RejectedCase]
