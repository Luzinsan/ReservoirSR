from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

from reservoir_sr.features.simulation.presentation.field_plot_renderer import FieldPlotRenderer

_CHANNEL_NAMES = ("P", "ST", "SB")
_COLUMN_TITLES = ("LR", "HR (GT)", "SR (pred)", "|SR − HR|")
_PALETTE_PER_CHANNEL = {"P": "geographical", "ST": "water_oil", "SB": "water_oil"}
_DIFF_PALETTE = "rainbow"


class FieldComparisonGrid(QtWidgets.QWidget):

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._renderer = FieldPlotRenderer()
        self._images: list[list[pg.ImageItem]] = []
        self._plots: list[list[pg.PlotItem]] = []
        self._diff_max_labels: list[pg.LabelItem] = []

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        # Column headers
        for col, title in enumerate(_COLUMN_TITLES):
            header = QtWidgets.QLabel(title)
            header.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            header.setStyleSheet("font-weight: 600;")
            layout.addWidget(header, 0, col + 1)

        # Rows: one per channel
        for row, channel in enumerate(_CHANNEL_NAMES):
            row_label = QtWidgets.QLabel(channel)
            row_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            row_label.setStyleSheet("font-weight: 600;")
            layout.addWidget(row_label, row + 1, 0)

            row_plots: list[pg.PlotItem] = []
            row_images: list[pg.ImageItem] = []

            for col in range(4):
                gw = pg.GraphicsLayoutWidget()
                gw.setBackground("w")
                plot = gw.addPlot()
                plot.setMenuEnabled(False)
                plot.hideButtons()
                plot.setMouseEnabled(x=False, y=False)
                plot.getViewBox().invertY(True)
                plot.getViewBox().setAspectLocked(False)
                plot.showAxis("bottom", False)
                plot.showAxis("left", False)

                image = pg.ImageItem(axisOrder="row-major")
                image.setAutoDownsample(True)
                plot.addItem(image)

                gw.setMinimumHeight(150)
                layout.addWidget(gw, row + 1, col + 1)

                row_plots.append(plot)
                row_images.append(image)

            self._plots.append(row_plots)
            self._images.append(row_images)

        for col in range(1, 5):
            layout.setColumnStretch(col, 1)
        for row in range(1, 4):
            layout.setRowStretch(row, 1)

    def show_empty(self) -> None:
        empty = np.zeros((1, 1, 3), dtype=np.uint8)
        for row_imgs in self._images:
            for img in row_imgs:
                img.setImage(empty, autoLevels=False)

    def update_frame(self, lr: np.ndarray, hr: np.ndarray, sr: np.ndarray) -> None:
        """lr, hr, sr — (C, Z, X) physical units."""
        for ch_idx, channel in enumerate(_CHANNEL_NAMES):
            palette = _PALETTE_PER_CHANNEL[channel]
            lr_ch, hr_ch, sr_ch = lr[ch_idx], hr[ch_idx], sr[ch_idx]
            diff = np.abs(sr_ch - hr_ch)

            self._render_cell(ch_idx, 0, lr_ch, palette, channel)
            self._render_cell(ch_idx, 1, hr_ch, palette, channel)
            self._render_cell(ch_idx, 2, sr_ch, palette, channel)
            self._render_cell(ch_idx, 3, diff, _DIFF_PALETTE, channel)

    def _render_cell(
        self,
        row: int,
        col: int,
        arr: np.ndarray,
        palette: str,
        channel: str,
    ) -> None:
        rgb, _ = self._renderer.render_legacy_palette_map(
            arr,
            render_mode="smooth",
            palette_name=palette,
            current_field=channel,
        )
        img = self._images[row][col]
        img.setLookupTable(None)
        img.setImage(rgb, autoLevels=False)
        nz, nx = arr.shape
        img.setRect(QtCore.QRectF(0, 0, float(nx), float(nz)))
