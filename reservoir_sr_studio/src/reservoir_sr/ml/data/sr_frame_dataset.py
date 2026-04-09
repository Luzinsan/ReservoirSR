from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset

from reservoir_sr.ml.data.loaded_archive import (
    ConditionSpec,
    LoadedArchive,
    normalize_condition_spec,
)
from reservoir_sr.infrastructure.storage.sr_archive_io import load_sr_archive
from reservoir_sr.ml.preprocessing.normalizer import Normalizer


class SrFrameDataset(Dataset):
    """Frame-level SR dataset with LRU-cached archive loading.

    Each sample is one timestep from one simulation archive,
    returning an LR/HR field pair and an optional condition vector
    assembled from the requested scalar groups.

    If a ``Normalizer`` is provided, fields and scalars are
    normalized inside ``__getitem__``.
    """

    def __init__(
        self,
        archive_paths: list[Path],
        cache_size: int = 32,
        condition: ConditionSpec = ("dynamic", "static", "layers"),
        normalizer: Normalizer | None = None,
    ) -> None:
        self._paths = archive_paths
        self._condition = normalize_condition_spec(condition)
        self._norm = normalizer
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
        norm = self._norm

        lr = ds.field_tensor(t, "lr")
        hr = ds.field_tensor(t, "hr")

        if norm is not None:
            lr = norm.normalize_fields(lr, "lr")
            hr = norm.normalize_fields(hr, "hr")

        result: dict[str, torch.Tensor] = {
            "lr": torch.from_numpy(lr),
            "hr": torch.from_numpy(hr),
        }

        extractors = LoadedArchive.CONDITION_EXTRACTORS
        parts: list[np.ndarray] = []
        for group, names in self._condition.items():
            raw = extractors[group](ds, t, names)
            if norm is not None:
                raw = norm.normalize_scalars(raw, group, names)
            parts.append(raw)

        if parts:
            result["condition"] = torch.from_numpy(
                np.concatenate(parts).astype(np.float32)
            )

        return result

    def _load(self, archive_idx: int) -> LoadedArchive:
        arrays, metadata = load_sr_archive(self._paths[archive_idx])
        return LoadedArchive(arrays, metadata)
