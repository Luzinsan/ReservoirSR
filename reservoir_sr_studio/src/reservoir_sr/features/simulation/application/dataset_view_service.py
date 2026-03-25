from __future__ import annotations

from pathlib import Path

import numpy as np

from reservoir_sr.domain.simulation.archive_models import DatasetFrame, LoadedArchive
from reservoir_sr.infrastructure.storage.sr_archive_io import load_sr_archive


class DatasetViewService:
    def load_archive(self, path: Path) -> LoadedArchive:
        arrays, metadata = load_sr_archive(path)
        return LoadedArchive(arrays=arrays, metadata=metadata)

    def load_archive_folder(self, folder: Path, max_archives: int) -> LoadedArchive:
        if not folder.exists() or not folder.is_dir():
            raise FileNotFoundError(f"Archive folder not found: {folder}")
        limit = max(1, int(max_archives))
        archive_paths = sorted(
            [path for path in folder.iterdir() if path.is_file() and path.suffix.lower() == ".npz"]
        )[:limit]
        if not archive_paths:
            raise FileNotFoundError(f"No .npz archives found in folder: {folder}")

        loaded = [self.load_archive(path) for path in archive_paths]
        base = loaded[0]
        merged_arrays: dict[str, np.ndarray] = {key: np.asarray(values) for key, values in base.arrays.items()}
        base_name = archive_paths[0].name
        for archive_index, current in enumerate(loaded[1:], start=1):
            current_name = archive_paths[archive_index].name
            for key, values in current.arrays.items():
                current_arr = np.asarray(values)
                if key not in merged_arrays:
                    raise ValueError(
                        f"Archive schema mismatch between '{base_name}' and '{current_name}': "
                        f"missing key '{key}' in first archive"
                    )
                target_arr = merged_arrays[key]
                if _is_time_series_key(key):
                    if target_arr.ndim != current_arr.ndim or target_arr.shape[1:] != current_arr.shape[1:]:
                        raise ValueError(
                            f"Shape mismatch for time-series field '{key}' between '{base_name}' and '{current_name}': "
                            f"{target_arr.shape} vs {current_arr.shape}. "
                            "This usually means mixed grid/layer dimensions across archives."
                        )
                    merged_arrays[key] = np.concatenate([target_arr, current_arr], axis=0)
                else:
                    if target_arr.shape != current_arr.shape:
                        raise ValueError(
                            f"Shape mismatch for static field '{key}' between '{base_name}' and '{current_name}': "
                            f"{target_arr.shape} vs {current_arr.shape}."
                        )

        merged_metadata = dict(base.metadata)
        merged_metadata["steps"] = int(_resolve_steps(merged_arrays, merged_metadata))
        merged_metadata["source_folder"] = str(folder)
        merged_metadata["source_archives"] = [path.name for path in archive_paths]
        merged_metadata["source_archives_limit"] = limit
        return LoadedArchive(arrays=merged_arrays, metadata=merged_metadata)

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


def _resolve_steps(arrays: dict[str, object], metadata: dict[str, object]) -> int:
    if "dynamic_scalars" in arrays:
        return int(np.asarray(arrays["dynamic_scalars"]).shape[0])
    raw_steps = metadata.get("steps", 0)
    if isinstance(raw_steps, int) and raw_steps > 0:
        return raw_steps
    for values in arrays.values():
        arr = np.asarray(values)
        if arr.ndim >= 1:
            return int(arr.shape[0])
    return 0


def _is_time_series_key(key: str) -> bool:
    return key in {"lr_fields", "hr_fields", "dynamic_scalars"}
