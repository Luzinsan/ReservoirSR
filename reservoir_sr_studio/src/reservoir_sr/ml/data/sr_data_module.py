from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import pytorch_lightning as pl
from omegaconf import DictConfig, ListConfig
from torch.utils.data import DataLoader

from reservoir_sr.domain.training.norm_config import (
    DYNAMIC_GROUPS,
    LAYER_GROUPS,
    STATIC_GROUPS,
)
from reservoir_sr.domain.training.normalization_stats import NormalizationStats
from reservoir_sr.ml.data.sr_frame_dataset import SrFrameDataset
from reservoir_sr.ml.preprocessing.normalizer import Normalizer
from reservoir_sr.ml.preprocessing.stats_service import compute_stats

_N_LAYERS = 5

_ALL_PARAMS: dict[str, list[str]] = {
    "dynamic": [p for names in DYNAMIC_GROUPS.values() for p in names],
    "static": [p for names in STATIC_GROUPS.values() for p in names],
    "layers": [p for names in LAYER_GROUPS.values() for p in names],
}


class SrDataModule(pl.LightningDataModule):
    """LightningDataModule for Reservoir SR.

    Loads all parameters from the Hydra `data` config.
    Handles dataset discovery, train/val/test splitting,
    stats computation (once), normalization setup,
    and dataloader construction.
    """

    def __init__(
        self,
        data_cfg: DictConfig | dict[str, Any],
    ) -> None:
        super().__init__()
        self.cfg = data_cfg
            
        # 1. Extract config sections
        source_cfg = self.cfg.get("source", {})
        split_cfg = self.cfg.get("split", {})
        self.loader_cfg = self.cfg.get("loader", {})
        
        self.stats_path = Path(source_cfg.get("stats_path", "stats.json"))
        
        # true = all params (None downstream), [list] = specific, false/null = disabled
        cond_cfg = self.cfg.get("condition", {})
        self.condition: dict[str, list[str] | None] = {}
        for g in ("dynamic", "static", "layers"):
            v = cond_cfg.get(g)
            if isinstance(v, (list, ListConfig)):
                self.condition[g] = list(v)
            elif v:
                self.condition[g] = None
                
        # 3. Norm setup
        self.norm_config = self.cfg.get("norm", {})

        self.dataset_dir = Path(source_cfg.get("dataset_dir", "./dataset"))
        self.cache_size = source_cfg.get("cache_size", 32)
        
        self.seed = split_cfg.get("seed", 42)
        self.val_fraction = split_cfg.get("val_fraction", 0.15)
        self.test_fraction = split_cfg.get("test_fraction", 0.15)

        self.train_paths: list[Path] = []
        self.val_paths: list[Path] = []
        self.test_paths: list[Path] = []

        self.train_dataset: SrFrameDataset | None = None
        self.val_dataset: SrFrameDataset | None = None
        self.test_dataset: SrFrameDataset | None = None
        self.normalizer: Normalizer | None = None

        self._discover_and_split_datasets()

    @property
    def condition_dim(self) -> int:
        """Total scalar dimension of the condition vector (0 if disabled)."""
        total = 0
        for group, names in self.condition.items():
            if names is not None:
                count = len(names)
            else:
                count = len(_ALL_PARAMS[group])
            if group == "layers":
                count *= _N_LAYERS
            total += count
        return total

    def _discover_and_split_datasets(self) -> None:
        """Finds all archives in dataset_dir and splits them deterministically."""
        if not self.dataset_dir.exists():
            print(f"Warning: Dataset directory {self.dataset_dir} does not exist.")
            return

        # Find all simulation archives (they typically have .npz, .sr, or .zip extension)
        all_archives = sorted(
            list(self.dataset_dir.glob("*.npz")) + 
            list(self.dataset_dir.glob("*.sr")) + 
            list(self.dataset_dir.glob("*.zip"))
        )
        if not all_archives:
            print(f"Warning: No archives found in {self.dataset_dir}.")
            return

        # Deterministic shuffle
        rng = random.Random(self.seed)
        rng.shuffle(all_archives)

        total = len(all_archives)
        val_count = int(total * self.val_fraction)
        test_count = int(total * self.test_fraction)
        train_count = total - val_count - test_count

        self.train_paths = all_archives[:train_count]
        self.val_paths = all_archives[train_count:train_count + val_count]
        self.test_paths = all_archives[train_count + val_count:]

        print(f"Discovered {total} archives.")
        print(f"Splits - Train: {len(self.train_paths)}, Val: {len(self.val_paths)}, Test: {len(self.test_paths)}")

    def prepare_data(self) -> None:
        """Compute and save normalization stats if they don't exist.
        
        This method is called only on 1 GPU in distributed settings.
        """
        if not self.train_paths:
            return
            
        if not self.stats_path.exists():
            print(f"Computing stats from train archives and saving to {self.stats_path}...")
            stats = compute_stats(self.train_paths)
            stats.to_json(self.stats_path)

    def setup(self, stage: str | None = None) -> None:
        """Load stats, initialize normalizer, and create datasets."""
        if not self.train_paths:
            return
            
        if self.normalizer is None:
            stats = NormalizationStats.from_json(self.stats_path)
            # Pass the full config (which contains both "condition" and "norm") to the normalizer
            self.normalizer = Normalizer(stats, self.cfg)

        if stage == "fit" or stage is None:
            self.train_dataset = SrFrameDataset(
                archive_paths=self.train_paths,
                cache_size=self.cache_size,
                condition=self.condition,  # type: ignore[arg-type]
                normalizer=self.normalizer,
            )
            self.val_dataset = SrFrameDataset(
                archive_paths=self.val_paths,
                cache_size=self.cache_size,
                condition=self.condition,  # type: ignore[arg-type]
                normalizer=self.normalizer,
            )

        if stage == "test" or stage is None:
            if self.test_paths:
                self.test_dataset = SrFrameDataset(
                    archive_paths=self.test_paths,
                    cache_size=self.cache_size,
                    condition=self.condition,  # type: ignore[arg-type]
                    normalizer=self.normalizer,
                )

    def train_dataloader(self) -> DataLoader:
        if self.train_dataset is None:
            raise RuntimeError("Train dataset not initialized. Call setup() first.")
        return DataLoader(
            self.train_dataset,
            batch_size=self.loader_cfg.get("batch_size", 8),
            shuffle=True,
            num_workers=self.loader_cfg.get("num_workers", 4),
            pin_memory=self.loader_cfg.get("pin_memory", True),
            persistent_workers=self.loader_cfg.get("persistent_workers", True),
            drop_last=True,
        )

    def val_dataloader(self) -> DataLoader:
        if self.val_dataset is None:
            raise RuntimeError("Val dataset not initialized. Call setup() first.")
        return DataLoader(
            self.val_dataset,
            batch_size=self.loader_cfg.get("batch_size", 8),
            shuffle=False,
            num_workers=self.loader_cfg.get("num_workers", 4),
            pin_memory=self.loader_cfg.get("pin_memory", True),
            persistent_workers=self.loader_cfg.get("persistent_workers", True),
        )

    def test_dataloader(self) -> DataLoader:
        if self.test_dataset is None:
            raise RuntimeError("Test dataset not initialized.")
        return DataLoader(
            self.test_dataset,
            batch_size=self.loader_cfg.get("batch_size", 8),
            shuffle=False,
            num_workers=self.loader_cfg.get("num_workers", 4),
            pin_memory=self.loader_cfg.get("pin_memory", True),
            persistent_workers=self.loader_cfg.get("persistent_workers", True),
        )
