from __future__ import annotations

from pathlib import Path

import numpy as np

SPATIAL_FIELDS: tuple[str, ...] = (
    "P",
    "P0",
    "ST",
    "SB",
    "WT",
    "WB",
    "AVST",
    "AVSB",
    "AT",
    "AB",
    "BT",
    "BB",
    "BVT",
    "BVB",
    "CBET",
)

SCALAR_FIELDS: tuple[str, ...] = ("times", "AI", "AIT", "AIB", "P_zab", "Q_fld", "DISS", "DISQ")


def read_scalar_series(case_dir: Path, name: str, expected_steps: int) -> np.ndarray:
    arr = np.fromfile(case_dir / f"{name}.bin", dtype=np.float64)
    if arr.size != expected_steps:
        raise ValueError(f"{name}.bin has {arr.size} records, expected {expected_steps} in {case_dir}")
    return arr


def read_spatial_series(case_dir: Path, field: str, steps: int, nx: int, nz: int) -> np.ndarray:
    raw = np.fromfile(case_dir / f"{field}.bin", dtype=np.float64)
    expected = steps * nx * nz
    if raw.size != expected:
        raise ValueError(f"{field}.bin has {raw.size} values, expected {expected} in {case_dir}")
    return raw.reshape(steps, nz, nx)


def infer_nz(case_dir: Path, steps: int, nx: int, field: str = "P") -> int:
    raw = np.fromfile(case_dir / f"{field}.bin", dtype=np.float64)
    denom = steps * nx
    if denom <= 0 or raw.size % denom != 0:
        raise ValueError(f"Cannot infer nz from {field}.bin in {case_dir}: size={raw.size}, steps={steps}, nx={nx}")
    return raw.size // denom
