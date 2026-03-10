from __future__ import annotations

from pathlib import Path

import numpy as np

from reservoir_sr.domain.simulation.archive_models import DatasetFrame, LoadedArchive
from reservoir_sr.infrastructure.storage.sr_archive_io import load_sr_archive


class DatasetViewService:
    def load_archive(self, path: Path) -> LoadedArchive:
        arrays, metadata = load_sr_archive(path)
        return LoadedArchive(arrays=arrays, metadata=metadata)

    def frame(self, archive: LoadedArchive, field_name: str, step_index: int, channel_index: int = 0) -> DatasetFrame:
        values = np.asarray(archive.arrays[field_name])
        if values.ndim == 4:
            frame_values = values[step_index, channel_index]
        elif values.ndim == 3:
            frame_values = values[step_index]
        else:
            raise ValueError(f"Unsupported array rank for {field_name}: {values.ndim}")
        return DatasetFrame(
            field_name=field_name,
            step_index=step_index,
            channel_index=channel_index,
            values=frame_values,
        )

    def describe(self, archive: LoadedArchive) -> dict[str, object]:
        return {
            "arrays": {name: tuple(np.asarray(values).shape) for name, values in archive.arrays.items()},
            "metadata": archive.metadata,
        }
