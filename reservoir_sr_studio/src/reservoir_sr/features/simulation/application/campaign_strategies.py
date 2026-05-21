from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from typing import Protocol

import numpy as np

from reservoir_sr.domain.simulation.config_models import SimulationConfig
from reservoir_sr.domain.simulation.value_objects import (
    ParameterRange,
    SamplingScale,
    SimulationCampaignCase,
)
from reservoir_sr.features.simulation.application.campaign_models import (
    SimulationCampaignRequest,
)


class CampaignSamplingStrategy(Protocol):
    strategy_id: str

    def build_cases(self, request: SimulationCampaignRequest) -> Iterator[SimulationCampaignCase]: ...


def _apply_parameter(config: SimulationConfig, name: str, value: object) -> SimulationConfig:
    if name.startswith("layer_") and name.endswith("_akt"):
        layer_idx = int(name.split("_")[1])
        updated = list(config.layers)
        updated[layer_idx] = replace(updated[layer_idx], akt=max(1e-8, float(value)))
        return replace(config, layers=updated)
    if name.startswith("layer_") and name.endswith("_akb"):
        layer_idx = int(name.split("_")[1])
        updated = list(config.layers)
        updated[layer_idx] = replace(updated[layer_idx], akb=max(1e-8, float(value)))
        return replace(config, layers=updated)
    if name == "layer_snt_shift":
        shift = float(value)
        updated = []
        for layer in config.layers:
            snt = float(layer.snt) + shift
            svt = float(layer.svt)
            snt = min(max(snt, 0.0), svt - 1e-6)
            updated.append(replace(layer, snt=snt))
        return replace(config, layers=updated)
    if name == "layer_snb_shift":
        shift = float(value)
        updated = []
        for layer in config.layers:
            snb = float(layer.snb) + shift
            svb = float(layer.svb)
            snb = min(max(snb, 0.0), svb - 1e-6)
            updated.append(replace(layer, snb=snb))
        return replace(config, layers=updated)
    if name == "layer_svt_shift":
        shift = float(value)
        updated = []
        for layer in config.layers:
            svt = float(layer.svt) + shift
            snt = float(layer.snt)
            svt = max(min(svt, 1.0), snt + 1e-6)
            updated.append(replace(layer, svt=svt))
        return replace(config, layers=updated)
    if name == "layer_svb_shift":
        shift = float(value)
        updated = []
        for layer in config.layers:
            svb = float(layer.svb) + shift
            snb = float(layer.snb)
            svb = max(min(svb, 1.0), snb + 1e-6)
            updated.append(replace(layer, svb=svb))
        return replace(config, layers=updated)
    payload = dict(config.__dict__)
    payload[name] = value
    return replace(config, **payload)


class LatinHypercubeSamplingStrategy:
    strategy_id = "lhs"

    def build_cases(self, request: SimulationCampaignRequest) -> Iterator[SimulationCampaignCase]:
        rng = np.random.default_rng(request.seed)
        n = request.sample_count
        ranges = request.ranges
        if n <= 0:
            return

        u = (np.arange(n, dtype=np.float64) + rng.random(n)) / n
        dims = np.zeros((n, len(ranges)), dtype=np.float64)
        for idx, parameter_range in enumerate(ranges):
            perm = rng.permutation(u)
            dims[:, idx] = _map_unit_to_range(perm, parameter_range)

        for case_index in range(n):
            cfg = request.base_config
            for dim_idx, parameter_range in enumerate(ranges):
                value = float(dims[case_index, dim_idx])
                if parameter_range.integer:
                    value = int(round(value))
                cfg = _apply_parameter(cfg, parameter_range.name, value)
            yield SimulationCampaignCase(
                case_id=f"{request.campaign_id}_case_{case_index:05d}",
                config=cfg,
            )


def _map_unit_to_range(unit: np.ndarray, parameter_range: ParameterRange) -> np.ndarray:
    low = float(parameter_range.low)
    high = float(parameter_range.high)
    if parameter_range.scale == SamplingScale.LOG10:
        low = np.log10(low)
        high = np.log10(high)
        mapped = np.power(10.0, low + (high - low) * unit)
    else:
        mapped = low + (high - low) * unit
    return mapped
