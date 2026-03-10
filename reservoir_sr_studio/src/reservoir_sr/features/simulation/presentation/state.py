from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import numpy as np


class ViewMode(StrEnum):
    RUNTIME = "runtime"
    DATASET = "dataset"


@dataclass
class RuntimeViewState:
    endpoint: str = "localhost:5000"
    simulation_id: str = "sim_main"
    field_name: str = "ST"
    step_batch: int = 10
    timer_ms: int = 50
    runtime_nx: int = 100
    runtime_nz: int = 1
    runtime_needs_init: bool = False
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class DatasetJobViewState:
    output_dir: Path = Path.cwd() / "dataset_out"
    job_id: str = ""
    steps: int = 500
    status_text: str = "idle"
    active_job_id: str | None = None


@dataclass
class DatasetViewState:
    archive_path: Path | None = None
    arrays: dict[str, np.ndarray] | None = None
    metadata: dict[str, Any] | None = None
    step_index: int = 0
    channel_index: int = 0
    dynamic_index: dict[str, int] = field(default_factory=dict)


@dataclass
class RenderViewState:
    current_field: str = "ST"
    render_mode: str = "smooth"
    isoline_layer_mode: str = "off"
    palette_name: str = "geographical"
    show_legend: bool = True
    live_render: bool = True
    isoline_width: int = 2
    isoline_level_stride: int = 1
    viewport_signature: tuple[float, float] | None = None
    overlay_signature: tuple[float, float] | None = None
    vector_color_name: str = "#ff0000"


@dataclass
class MetricsState:
    time: list[float] = field(default_factory=list)
    ai: list[float] = field(default_factory=list)
    ait: list[float] = field(default_factory=list)
    aib: list[float] = field(default_factory=list)


@dataclass
class RuntimeTrackingState:
    prev_q: float | None = None
    prev_pz: float | None = None
    prev_st: np.ndarray | None = None
