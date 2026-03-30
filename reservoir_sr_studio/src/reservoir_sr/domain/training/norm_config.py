from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Literal

NormStrategy = Literal["minmax", "zscore", "log_minmax", "log_zscore", "none"]

# ===================================================================
# Per-group config dataclasses
# ===================================================================


@dataclass(frozen=True)
class FieldNormConfig:
    P: NormStrategy = "zscore"
    ST: NormStrategy = "minmax"
    SB: NormStrategy = "minmax"


@dataclass(frozen=True)
class LayerNormConfig:
    geometry: NormStrategy = "minmax"       # NZM, HBM
    porosity: NormStrategy = "minmax"       # VMB, VMT
    saturation: NormStrategy = "minmax"     # SNT, SNB, SVT, SVB
    permeability: NormStrategy = "log_minmax"  # AKT, AKB
    flags: NormStrategy = "none"            # LWN, LWD


@dataclass(frozen=True)
class DynamicNormConfig:
    time: NormStrategy = "none"             # time
    accumulation: NormStrategy = "minmax"   # AI, AIT, AIB
    well_dynamic: NormStrategy = "minmax"   # P_zab, Q_fld, Q_oil_*
    dissipation: NormStrategy = "zscore"    # DISS, DISQ
    temperature: NormStrategy = "minmax"    # TBT, TB, TT


@dataclass(frozen=True)
class StaticNormConfig:
    fluid_props: NormStrategy = "minmax"    # density, viscosity, thermal, gas
    reservoir: NormStrategy = "minmax"      # geometry, compressibility
    well_ops: NormStrategy = "minmax"       # pressures, flow rates
    time_config: NormStrategy = "none"      # time steps, durations
    grid: NormStrategy = "none"             # NB, NX, N_Dr
    flags: NormStrategy = "none"            # LOD, LIZ, LTVK, LTK
    solver: NormStrategy = "none"           # convergence tolerances


# ===================================================================
# Top-level config
# ===================================================================


@dataclass(frozen=True)
class NormConfig:
    fields: FieldNormConfig = field(default_factory=FieldNormConfig)
    layers: LayerNormConfig = field(default_factory=LayerNormConfig)
    dynamic: DynamicNormConfig = field(default_factory=DynamicNormConfig)
    static: StaticNormConfig = field(default_factory=StaticNormConfig)


# ===================================================================
# Parameter → group mappings
# ===================================================================

FIELD_GROUPS: dict[str, list[str]] = {
    "P": ["P"],
    "ST": ["ST"],
    "SB": ["SB"],
}

LAYER_GROUPS: dict[str, list[str]] = {
    "geometry": ["NZM", "HBM"],
    "porosity": ["VMB", "VMT"],
    "saturation": ["SNT", "SNB", "SVT", "SVB"],
    "permeability": ["AKT", "AKB"],
    "flags": ["LWN", "LWD"],
}

DYNAMIC_GROUPS: dict[str, list[str]] = {
    "time": ["time"],
    "accumulation": ["AI", "AIT", "AIB"],
    "well_dynamic": ["P_zab", "Q_fld", "Q_oil_total", "Q_oil_blocks", "Q_oil_fractures"],
    "dissipation": ["DISS", "DISQ"],
    "temperature": ["TBT", "TB", "TT"],
}

STATIC_GROUPS: dict[str, list[str]] = {
    "fluid_props": [
        "Ro1_PL", "Ro1_deg", "Ro3_PL",
        "Mu1_PL", "Mu_Deg", "Mu3_PL", "MU_pazp", "YTAP2",
        "AP1", "AT1", "AP3", "AT3",
        "C_P_1", "C_P_2", "C_P_3",
        "R00", "VesGMol", "DZT", "ZG",
    ],
    "reservoir": [
        "VL", "R_Skv", "RADZ0",
        "SM", "S_T_R", "BT", "BG", "Bt_Cp", "Bt_Tr",
    ],
    "well_ops": [
        "R_C_R", "QUNT_CR", "X_A", "X_D", "VG0",
        "Q_zab", "OBV_P", "QQ", "P32", "PH0",
    ],
    "time_config": ["TVK", "TK", "DSO", "TU", "Tim_0", "Tim_1", "Tim_2"],
    "grid": ["NB", "NX", "N_Dr"],
    "flags": ["LOD", "LIZ", "LTVK", "LTK"],
    "solver": ["EPSP", "ENB", "EVB", "ENT", "EVT"],
}

ALL_GROUP_TABLES: dict[str, dict[str, list[str]]] = {
    "fields": FIELD_GROUPS,
    "layers": LAYER_GROUPS,
    "dynamic": DYNAMIC_GROUPS,
    "static": STATIC_GROUPS,
}


def _invert(groups: dict[str, list[str]]) -> dict[str, str]:
    return {param: group for group, params in groups.items() for param in params}


_RESOLVERS: dict[str, dict[str, str]] = {
    section: _invert(groups) for section, groups in ALL_GROUP_TABLES.items()
}


def resolve_strategy(config: NormConfig, section: str, param_name: str) -> NormStrategy:
    """Resolve the normalization strategy for a specific parameter.

    ``section`` is one of ``"fields"``, ``"layers"``, ``"dynamic"``, ``"static"``.
    ``param_name`` is the parameter name as it appears in the archive metadata.
    Raises ``KeyError`` if the parameter is unknown.
    """
    resolver = _RESOLVERS[section]
    group_name = resolver[param_name]
    sub_config = getattr(config, section)
    return getattr(sub_config, group_name)


def validate_config(config: NormConfig, stats_names: dict[str, set[str]]) -> None:
    """Check that every parameter in stats is covered by the config mappings.

    ``stats_names`` maps section name to the set of parameter names
    present in ``NormalizationStats`` (e.g. ``{"fields": {"P","ST","SB"}, ...}``).
    Raises ``ValueError`` listing any unmapped parameters.
    """
    unmapped: list[str] = []
    for section, names in stats_names.items():
        resolver = _RESOLVERS.get(section, {})
        for name in names:
            if name not in resolver:
                unmapped.append(f"{section}/{name}")
    if unmapped:
        raise ValueError(f"Parameters not covered by NormConfig: {unmapped}")
