from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import TYPE_CHECKING

from reservoir_sr.domain.simulation.config_models import SimulationConfig

if TYPE_CHECKING:
    from reservoir_sr.features.simulation.presentation.view_models import (
        CampaignSessionState,
        GenerationSessionState,
    )


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
    output_dir: str
    strategy: str
    sample_count: int
    steps: int
    snapshot_stride: int
    hr_nx: int
    seed: int
    base_config: SimulationConfig
    ranges: tuple[ParameterRange, ...]

    @classmethod
    def build(
        cls,
        generation: GenerationSessionState,
        campaign: CampaignSessionState,
        base_config: SimulationConfig,
        ranges: tuple[ParameterRange, ...],
    ) -> SimulationCampaignRequest:
        return cls(
            campaign_id=generation.job_id.strip() or f"campaign_{uuid.uuid4().hex[:10]}",
            output_dir=generation.output_dir,
            steps=generation.steps,
            snapshot_stride=generation.snapshot_stride,
            hr_nx=generation.hr_nx,
            strategy=campaign.strategy,
            sample_count=campaign.sample_count,
            seed=campaign.seed,
            base_config=replace(
                base_config,
                nx=generation.lr_nx,
                tu_seconds=generation.fixed_tu_seconds,
                epsp=generation.fixed_epsp,
            ),
            ranges=ranges,
        )


@dataclass(frozen=True)
class SimulationCampaignCase:
    case_id: str
    config: SimulationConfig


class CampaignCaseStream:
    """Frozen campaign request + lazy iterator over generated cases."""

    def __init__(
        self,
        request: SimulationCampaignRequest,
        cases: Iterator[SimulationCampaignCase],
    ) -> None:
        self.request = request
        self._cases = cases
        self._exhausted = False

    @property
    def exhausted(self) -> bool:
        return self._exhausted

    def take(self) -> SimulationCampaignCase | None:
        case = next(self._cases, None)
        if case is None:
            self._exhausted = True
        return case
