from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset

from reservoir_sr.domain.simulation.dataset_models import (
    ConditionSpec,
    LoadedDataset,
    normalize_condition_spec,
)
from reservoir_sr.infrastructure.storage.sr_archive_io import load_sr_archive


class SrFrameDataset(Dataset):
    """Frame-level SR dataset with LRU-cached archive loading.

    Each sample is one timestep from one simulation archive,
    returning an LR/HR field pair and an optional condition vector
    assembled from the requested scalar groups.
    """

    def __init__(
        self,
        archive_paths: list[Path],
        cache_size: int = 32,
        condition: ConditionSpec = ("dynamic", "static", "layers"),
    ) -> None:
        self._paths = archive_paths
        self._condition = normalize_condition_spec(condition)
        self._load_cached = lru_cache(maxsize=cache_size)(self._load)

        self._index: list[tuple[int, int]] = []
        for archive_idx in range(len(archive_paths)):
            ds = self._load_cached(archive_idx)
            for t in range(ds.total_steps):
                self._index.append((archive_idx, t))

    def __len__(self) -> int:
        return len(self._index)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        archive_idx, t = self._index[idx]
        ds = self._load_cached(archive_idx)

        result: dict[str, torch.Tensor] = {
            "lr": torch.from_numpy(ds.field_tensor(t, "lr")),
            "hr": torch.from_numpy(ds.field_tensor(t, "hr")),
        }

        extractors = LoadedDataset.CONDITION_EXTRACTORS
        parts = [extractors[g](ds, t, names) for g, names in self._condition.items()]
        if parts:
            result["condition"] = torch.from_numpy(
                np.concatenate(parts).astype(np.float32)
            )

        return result

    def _load(self, archive_idx: int) -> LoadedDataset:
        arrays, metadata = load_sr_archive(self._paths[archive_idx])
        return LoadedDataset(arrays, metadata)
