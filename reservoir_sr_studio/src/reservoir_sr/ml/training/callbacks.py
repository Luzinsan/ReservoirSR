from __future__ import annotations

import torch
import pytorch_lightning as pl
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.figure
import numpy as np


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
    """Logs LR / HR / SR / |diff| field images to TensorBoard.

    Buffers the last validation batch (late timesteps with more detail)
    and logs visualizations at the end of every validation epoch.
    Frequency is controlled by ``check_val_every_n_epoch`` in the Trainer.
    """

    def __init__(self, n_samples: int = 2):
        self.n_samples = n_samples
        self._last_batch: dict[str, torch.Tensor] | None = None

    def on_validation_batch_end(self, trainer, pl_module, outputs, batch, batch_idx, dataloader_idx=0):
        self._last_batch = {k: v.detach().cpu() for k, v in batch.items()}

    def on_validation_epoch_end(self, trainer, pl_module):
        if self._last_batch is None or trainer.logger is None:
            return

        batch = {k: v.to(pl_module.device) for k, v in self._last_batch.items()}
        with torch.no_grad():
            pred = pl_module.model(batch).float().cpu()
        target = self._last_batch["hr"].float()
        lr = self._last_batch["lr"].float()

        bs = pred.shape[0]
        indices = torch.randperm(bs)[: self.n_samples]

        for sample_idx in indices:
            fig = _make_figure(
                lr[sample_idx].numpy(),
                target[sample_idx].numpy(),
                pred[sample_idx].numpy(),
            )
            trainer.logger.experiment.add_figure(
                f"fields/sample_{sample_idx.item()}",
                fig,
                global_step=trainer.global_step,
            )
            plt.close(fig)

        self._last_batch = None


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
