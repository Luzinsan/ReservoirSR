from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np


@dataclass(frozen=True)
class SimulationInitialization:
    simulation_id: str
    ok: bool
    message: str
    nx: int
    nz: int


@dataclass(frozen=True)
class SimulationStepResult:
    ok: bool
    message: str
    steps_performed: int
    time: float
    ai: float
    ait: float
    aib: float
    p_zab: float
    q_fld: float
    diss: float
    disq: float
    tbt: float
    tb: float
    tt: float
    q_oil_total: float
    q_oil_blocks: float
    q_oil_fractures: float


@dataclass(frozen=True)
class FieldGrid:
    name: str
    values: np.ndarray


@dataclass(frozen=True)
class SimulationFields:
    nx: int
    nz: int
    data: dict[str, FieldGrid]


class DatasetJobState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class DatasetJobHandle:
    ok: bool
    message: str
    job_id: str


@dataclass(frozen=True)
class DatasetJobStatus:
    job_id: str
    state: DatasetJobState
    message: str
    steps_done: int
    steps_total: int
    output_path: str


@dataclass(frozen=True)
class DatasetJobCancellation:
    ok: bool
    message: str


@dataclass(frozen=True)
class DatasetJobPause:
    ok: bool
    message: str


@dataclass(frozen=True)
class DatasetJobResume:
    ok: bool
    message: str
