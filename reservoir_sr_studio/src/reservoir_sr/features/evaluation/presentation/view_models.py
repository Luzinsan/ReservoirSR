from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from reservoir_sr.common.observable import ObservableModel


@dataclass
class EvaluationState(ObservableModel):
    model_path: Path | None = None
    split: str = "test"
    archive_path: Path | None = None
    step_index: int = 0
    is_prefetching: bool = False