from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping


@dataclass(frozen=True)
class ReservoirLayerConfig:
    nzm: int = 4
    hbm: float = 2.0
    vmb: float = 0.2
    vmt: float = 0.04
    lwn: int = 1
    lwd: int = 0
    snt: float = 0.1
    snb: float = 0.2
    svt: float = 0.9
    svb: float = 0.8
    akt: float = 0.1
    akb: float = 0.01


def default_layer_configs() -> list[ReservoirLayerConfig]:
    layers = [ReservoirLayerConfig() for _ in range(5)]
    layers[3] = replace(layers[3], lwn=0, akt=0.03, akb=0.001)
    layers[4] = replace(layers[4], snt=0.0, svt=1.0, snb=0.0, svb=1.0, lwn=0, lwd=1)
    return layers


@dataclass(frozen=True)
class SimulationConfig:
    nb: int = 5
    vl: float = 100.0
    lod: int = 0
    liz: int = 1
    r_skv: float = 0.1
    ro1_pl: float = 806.0
    ro1_deg: float = 870.0
    mu1_pl: float = 40.0
    mu_deg: float = 26.0
    ap1: float = 0.0009
    at1: float = 0.00125
    c_p_1: float = 1.88
    ro3_pl: float = 1020.0
    mu3_pl: float = 1.6
    c_p_3: float = 4.15
    ap3: float = 0.0004
    at3: float = 0.0008
    r00: float = 1.12
    c_p_2: float = 2.7
    ves_g_mol: float = 16.04
    ytap2: float = 0.0008
    dzt: float = 0.0035
    zg: float = 0.941
    r_c_r: float = 1.0
    qunt_cr: float = 140.0
    radz0: float = 6.0
    sm: float = 0.025
    s_t_r: float = 167.5
    vg0: float = 40.0
    ph0: float = 12.0
    bt: float = 0.02
    bg: float = 0.004
    bt_cp: float = 1e-5
    bt_tr: float = 1e-5
    mu_pazp: float = 8.0
    x_a: float = 1.0
    x_d: float = 0.25
    q_zab: float = 50.0
    obv_p: float = 180.0
    qq: float = 300.0
    p32: float = 130.0
    tvk: float = 6.0
    tk_days: float = 1000.3
    ltvk: int = 0
    ltk: int = 1
    dso: float = 30.0
    tu_seconds: float = 86.4
    n_dr: int = 10
    nx: int = 100
    epsp: float = 1e-6
    enb: float = 0.001
    evb: float = 0.001
    ent: float = 1e-4
    evt: float = 0.001
    tim_0: float = 5000.0
    tim_1: float = 10000.0
    tim_2: float = 10000.0
    layers: list[ReservoirLayerConfig] = field(default_factory=default_layer_configs)

    def with_layer_nzm(self, nzm: int) -> "SimulationConfig":
        return replace(self, layers=[replace(layer, nzm=nzm) for layer in self.layers])


def build_simulation_config(**overrides: Any) -> SimulationConfig:

    return replace(SimulationConfig(), **overrides)


def simulation_config_from_mapping(payload: Mapping[str, Any]) -> SimulationConfig:
    layers = payload.get("layers")
    resolved_payload = dict(payload)
    if layers is not None:
        resolved_payload["layers"] = [
            layer if isinstance(layer, ReservoirLayerConfig) else ReservoirLayerConfig(**layer) for layer in layers
        ]
    return build_simulation_config(**resolved_payload)
