from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LoadedArchive:
    arrays: dict[str, object]
    metadata: dict[str, object]


@dataclass(frozen=True)
class DatasetFrame:
    field_name: str
    step_index: int
    channel_index: int
    values: object
