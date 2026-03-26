from __future__ import annotations

from reservoir_sr.domain.simulation.config_models import SimulationConfig
from reservoir_sr.features.simulation.application.campaign_models import SimulationCampaignRequest
from reservoir_sr.features.simulation.application.campaign_service import SimulationCampaignService


def test_campaign_plan_varies_spatial_and_runtime_parameters() -> None:
    from dataclasses import replace
    service = SimulationCampaignService()
    base = replace(SimulationConfig(), nx=100, tu_seconds=86.4, epsp=1e-6)
    request = SimulationCampaignRequest(
        campaign_id="test_campaign",
        output_dir="/tmp/test_out",
        strategy="lhs",
        sample_count=8,
        steps=500,
        snapshot_stride=1,
        hr_nx=200,
        seed=42,
        base_config=base,
        ranges=service.default_ranges(),
    )

    cases = list(service.generate_cases(request))

    assert len(cases) >= 4
    n_dr_values = {case.config.n_dr for case in cases}
    qz_values = {round(case.config.q_zab, 6) for case in cases}
    akt_values = {round(case.config.layers[0].akt, 8) for case in cases}
    nzm_values = {case.config.layers[0].nzm for case in cases}

    assert len(n_dr_values) > 1
    assert len(qz_values) > 1
    assert len(akt_values) > 1
    assert len(nzm_values) == 1
