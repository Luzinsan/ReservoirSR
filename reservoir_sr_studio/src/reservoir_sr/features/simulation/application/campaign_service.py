from __future__ import annotations

from dataclasses import replace

from reservoir_sr.features.simulation.application.campaign_constraints import validate_physics
from reservoir_sr.features.simulation.application.campaign_models import (
    ParameterRange,
    RejectedCase,
    SamplingScale,
    SimulationCampaignPlan,
    SimulationCampaignRequest,
)
from reservoir_sr.features.simulation.application.campaign_strategies import (
    CampaignSamplingStrategy,
    LatinHypercubeSamplingStrategy,
)


class SimulationCampaignService:
    def __init__(self, strategies: dict[str, CampaignSamplingStrategy] | None = None) -> None:
        self._strategies = strategies or {LatinHypercubeSamplingStrategy.strategy_id: LatinHypercubeSamplingStrategy()}

    def available_strategies(self) -> tuple[str, ...]:
        return tuple(sorted(self._strategies.keys()))

    def build_plan(self, request: SimulationCampaignRequest, strategy_id: str) -> SimulationCampaignPlan:
        if strategy_id not in self._strategies:
            raise KeyError(f"Unknown strategy: {strategy_id}")
        raw_cases = self._strategies[strategy_id].build_cases(request)
        valid_cases = []
        rejected: list[RejectedCase] = []
        for case in raw_cases:
            verdict = validate_physics(case.config, request)
            if verdict.ok:
                valid_cases.append(case)
            else:
                rejected.append(RejectedCase(case_id=case.case_id, reason=verdict.reason))
        return SimulationCampaignPlan(cases=valid_cases, rejected=rejected)


def default_sr_parameter_ranges() -> tuple[ParameterRange, ...]:
    return (
        ParameterRange(name="n_dr", low=8, high=20, integer=True),
        ParameterRange(name="q_zab", low=15.0, high=70.0),
        ParameterRange(name="qq", low=120.0, high=480.0),
        ParameterRange(name="r_skv", low=0.05, high=0.35),
        ParameterRange(name="p32", low=90.0, high=210.0),
        ParameterRange(name="obv_p", low=80.0, high=360.0),
        ParameterRange(name="mu_pazp", low=4.0, high=18.0),
        ParameterRange(name="x_a", low=0.7, high=1.8),
        ParameterRange(name="x_d", low=0.05, high=0.6),
        ParameterRange(name="radz0", low=3.0, high=12.0),
        ParameterRange(name="dzt", low=0.0015, high=0.0060),
        ParameterRange(name="enb", low=1e-5, high=5e-3, scale=SamplingScale.LOG10),
        ParameterRange(name="evb", low=1e-5, high=5e-3, scale=SamplingScale.LOG10),
        ParameterRange(name="ent", low=1e-6, high=1e-3, scale=SamplingScale.LOG10),
        ParameterRange(name="evt", low=1e-5, high=5e-3, scale=SamplingScale.LOG10),
        ParameterRange(name="layer_akt_scale", low=0.2, high=3.5, scale=SamplingScale.LOG10),
        ParameterRange(name="layer_akb_scale", low=0.2, high=3.5, scale=SamplingScale.LOG10),
        ParameterRange(name="layer_snt_shift", low=-0.15, high=0.15),
        ParameterRange(name="layer_snb_shift", low=-0.15, high=0.15),
        ParameterRange(name="layer_svt_shift", low=-0.15, high=0.15),
        ParameterRange(name="layer_svb_shift", low=-0.15, high=0.15),
    )
