from __future__ import annotations

import torch
import pytorch_lightning as pl
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.figure
import numpy as np
from pathlib import Path
import tempfile
from typing import Any


CHANNEL_NAMES = ("P", "ST", "SB")


def _linear_cmap(c1: tuple[int, ...], c2: tuple[int, ...], name: str, n: int = 256) -> mcolors.LinearSegmentedColormap:
    a = np.array(c1, dtype=np.float64) / 255.0
    b = np.array(c2, dtype=np.float64) / 255.0
    colors = np.linspace(a, b, n)
    return mcolors.ListedColormap(colors, name=name)


def _geographical_cmap(n: int = 256) -> mcolors.ListedColormap:
    """Reproduce the geographical palette from FieldPlotRenderer."""
    third = n // 3
    colors = np.zeros((n, 3), dtype=np.float64)

    def _fill(start: int, count: int, r: tuple, g: tuple, b: tuple):
        for i in range(count):
            t = i / max(count - 1, 1)
            colors[start + i] = [
                (r[0] + (r[1] - r[0]) * t) / 255.0,
                (g[0] + (g[1] - g[0]) * t) / 255.0,
                (b[0] + (b[1] - b[0]) * t) / 255.0,
            ]

    _fill(0, third, (103, 114), (237, 103), (255, 255))
    _fill(third, third, (207, 63), (247, 141), (186, 16))
    _fill(2 * third, n - 2 * third, (237, 97), (231, 81), (207, 37))
    return mcolors.ListedColormap(colors, name="geographical")


CMAP_P = _geographical_cmap()
CMAP_ST = _linear_cmap((94, 94, 94), (120, 255, 255), "water_oil")
CMAP_SB = _linear_cmap((94, 94, 94), (120, 255, 255), "water_oil_sb")
CMAP_DIFF = plt.get_cmap("hot")
CHANNEL_CMAPS = (CMAP_P, CMAP_ST, CMAP_SB)


class SrVisualizationCallback(pl.Callback):
    """Logs fixed validation SR samples to active logger.

    Selection policy:
    1) Collect samples across the whole validation epoch grouped by archive_idx.
    2) For each archive keep only the latest timestep (max step_idx).
    3) Pick a fixed subset of archives (size n_samples) and log those every epoch.
    """

    def __init__(self, n_samples: int = 2):
        self.n_samples = n_samples
        self._latest_by_archive: dict[int, dict[str, torch.Tensor]] = {}
        self._fixed_archives: list[int] | None = None

    def on_validation_epoch_start(self, trainer, pl_module):
        self._latest_by_archive = {}

    def on_validation_batch_end(self, trainer, pl_module, outputs, batch, batch_idx, dataloader_idx=0):
        if "archive_idx" not in batch or "step_idx" not in batch:
            return

        archive_idx = batch["archive_idx"].detach().cpu()
        step_idx = batch["step_idx"].detach().cpu()

        bs = int(archive_idx.shape[0])
        for i in range(bs):
            a = int(archive_idx[i].item())
            s = int(step_idx[i].item())
            prev = self._latest_by_archive.get(a)
            prev_step = int(prev["step_idx"].item()) if prev is not None else -1
            if s >= prev_step:
                sample: dict[str, torch.Tensor] = {}
                for k, v in batch.items():
                    sample[k] = v[i].detach().cpu()
                self._latest_by_archive[a] = sample

    def on_validation_epoch_end(self, trainer, pl_module):
        if not self._latest_by_archive or trainer.logger is None:
            return

        samples = self._select_fixed_samples()
        if not samples:
            return

        vis_batch = _stack_samples(samples)
        model_batch = {
            k: v.to(pl_module.device)
            for k, v in vis_batch.items()
            if k not in {"hr", "archive_idx", "step_idx"}
        }

        with torch.no_grad():
            pred = pl_module.model(model_batch).float().cpu()
        target = vis_batch["hr"].float()
        lr = vis_batch["lr"].float()

        for i in range(pred.shape[0]):
            archive_id = int(vis_batch["archive_idx"][i].item())
            step_id = int(vis_batch["step_idx"][i].item())
            tag = f"fields/archive_{archive_id:03d}_step_{step_id:05d}"
            fig = _make_figure(
                lr[i].numpy(),
                target[i].numpy(),
                pred[i].numpy(),
            )
            self._log_figure(trainer, fig, tag)
            plt.close(fig)

        self._latest_by_archive = {}

    def _select_fixed_samples(self) -> list[dict[str, torch.Tensor]]:
        archives = sorted(self._latest_by_archive.keys())
        if not archives:
            return []

        n = min(self.n_samples, len(archives))
        if self._fixed_archives is None:
            # Deterministic fixed subset: tail archives in validation ordering.
            self._fixed_archives = archives[-n:]
        else:
            # Keep previous selection if available; backfill missing slots deterministically.
            keep = [a for a in self._fixed_archives if a in self._latest_by_archive]
            needed = n - len(keep)
            if needed > 0:
                pool = [a for a in archives if a not in keep]
                keep.extend(pool[-needed:])
            self._fixed_archives = keep[:n]

        return [self._latest_by_archive[a] for a in self._fixed_archives]

    def _log_figure(self, trainer: pl.Trainer, fig: matplotlib.figure.Figure, tag: str) -> None:
        logger = trainer.logger
        if logger is None:
            return

        experiment = getattr(logger, "experiment", None)

        # TensorBoard-like API.
        if experiment is not None and hasattr(experiment, "add_figure"):
            experiment.add_figure(tag, fig, global_step=trainer.global_step)
            return

        # MLflow logger API via MlflowClient.
        run_id = getattr(logger, "run_id", None)
        if experiment is not None and run_id is not None and hasattr(experiment, "log_artifact"):
            with tempfile.TemporaryDirectory(prefix="sr_viz_") as tmp_dir:
                file_name = f"{tag.replace('/', '_')}_step_{trainer.global_step}.png"
                local_path = Path(tmp_dir) / file_name
                fig.savefig(local_path, dpi=120, bbox_inches="tight")
                experiment.log_artifact(run_id, str(local_path), artifact_path="figures")


def _stack_samples(samples: list[dict[str, torch.Tensor]]) -> dict[str, torch.Tensor]:
    keys = samples[0].keys()
    out: dict[str, torch.Tensor] = {}
    for k in keys:
        out[k] = torch.stack([s[k] for s in samples], dim=0)
    return out


def _make_figure(lr: np.ndarray, hr: np.ndarray, sr: np.ndarray) -> matplotlib.figure.Figure:
    """Create a (C x 4) grid: LR | HR | SR | |SR-HR|."""
    n_ch = hr.shape[0]
    fig, axes = plt.subplots(n_ch, 4, figsize=(16, 3.5 * n_ch), squeeze=False)

    for c in range(n_ch):
        ch_name = CHANNEL_NAMES[c] if c < len(CHANNEL_NAMES) else f"ch{c}"
        cmap = CHANNEL_CMAPS[c] if c < len(CHANNEL_CMAPS) else CMAP_P
        vmin, vmax = hr[c].min(), hr[c].max()
        diff = np.abs(sr[c] - hr[c])

        for ax in axes[c]:
            ax.set_xticks([])
            ax.set_yticks([])

        axes[c, 0].imshow(lr[c], cmap=cmap, aspect="auto")
        axes[c, 0].set_title(f"{ch_name} LR")

        axes[c, 1].imshow(hr[c], cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
        axes[c, 1].set_title(f"{ch_name} HR (GT)")

        axes[c, 2].imshow(sr[c], cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
        axes[c, 2].set_title(f"{ch_name} SR (pred)")

        im = axes[c, 3].imshow(diff, cmap=CMAP_DIFF, vmin=0, aspect="auto")
        axes[c, 3].set_title(f"{ch_name} |diff|")
        fig.colorbar(im, ax=axes[c, 3], fraction=0.046, pad=0.04)

    fig.tight_layout()
    return fig
