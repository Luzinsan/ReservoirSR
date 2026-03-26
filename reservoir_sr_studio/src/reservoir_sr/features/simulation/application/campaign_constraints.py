from __future__ import annotations

from dataclasses import dataclass

from reservoir_sr.domain.simulation.config_models import SimulationConfig
from reservoir_sr.features.simulation.application.campaign_models import SimulationCampaignRequest


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    reason: str = ""


def validate_physics(config: SimulationConfig, request: SimulationCampaignRequest) -> ValidationResult:
    if config.epsp <= 0.0:
        return ValidationResult(ok=False, reason="epsp must be > 0")
    if config.n_dr <= 0:
        return ValidationResult(ok=False, reason="n_dr must be > 0")
    if config.tu_seconds <= 0.0:
        return ValidationResult(ok=False, reason="tu_seconds must be > 0")
    if config.tk_days <= 0.0:
        return ValidationResult(ok=False, reason="tk_days must be > 0")
    if request.hr_nx < config.nx:
        return ValidationResult(ok=False, reason="hr_nx must be >= lr_nx")
    # Ensure simulated time horizon is long enough for requested steps.
    total_seconds = config.tk_days * 24.0 * 3600.0
    required_seconds = request.steps * config.tu_seconds
    if total_seconds < required_seconds:
        return ValidationResult(ok=False, reason="tk_days * 86400 is lower than steps * tu_seconds")
    # Keep dr reasonable relative to spatial resolution.
    if config.n_dr > max(1, config.nx // 2):
        return ValidationResult(ok=False, reason="n_dr exceeds nx/2 physical limit")
    # Pairwise coupling for pressure / production rates.
    if config.qq <= 0.0 or config.q_zab <= 0.0:
        return ValidationResult(ok=False, reason="qq and q_zab must be > 0")
    if config.qq < config.q_zab * 0.25:
        return ValidationResult(ok=False, reason="qq is too low for chosen q_zab")
    if abs(config.x_a - config.x_d) < 1e-12:
        return ValidationResult(ok=False, reason="x_a and x_d must not be equal")
    if config.r_skv <= 0.0:
        return ValidationResult(ok=False, reason="r_skv must be > 0")
    if config.p32 <= 0.0:
        return ValidationResult(ok=False, reason="p32 must be > 0")
    for idx, layer in enumerate(config.layers):
        if layer.nzm <= 0:
            return ValidationResult(ok=False, reason=f"layer[{idx}].nzm must be > 0")
        if layer.hbm <= 0.0:
            return ValidationResult(ok=False, reason=f"layer[{idx}].hbm must be > 0")
        if layer.akt <= 0.0 or layer.akb <= 0.0:
            return ValidationResult(ok=False, reason=f"layer[{idx}] permeability must be > 0")
        if not (0.0 <= layer.snt <= layer.svt <= 1.0):
            return ValidationResult(ok=False, reason=f"layer[{idx}] top saturation bounds invalid")
        if not (0.0 <= layer.snb <= layer.svb <= 1.0):
            return ValidationResult(ok=False, reason=f"layer[{idx}] bottom saturation bounds invalid")
    return ValidationResult(ok=True)
