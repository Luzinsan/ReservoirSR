from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

from reservoir_sr.features.evaluation.presentation.panels.colormap_factory import (
    CHANNEL_LUTS,
    DIFF_LUT,
)

_CHANNEL_NAMES = ("P", "ST", "SB")
_COLUMN_TITLES = ("LR", "HR (GT)", "SR (pred)", "|SR − HR|")
_EMPTY = np.zeros((1, 1), dtype=np.float32)


class FieldComparisonGrid(QtWidgets.QWidget):
    """3×4 grid of pyqtgraph ImageItems with pre-baked LUTs.

    На каждом кадре только setImage(arr, levels) — без перекрашивания scene.
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        # _images[row][col] — ImageItem на ячейку
        self._images: list[list[pg.ImageItem]] = []

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        # Column headers
        for col, title in enumerate(_COLUMN_TITLES):
            header = QtWidgets.QLabel(title)
            header.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            header.setStyleSheet("font-weight: 600;")
            layout.addWidget(header, 0, col + 1)

        for row, channel in enumerate(_CHANNEL_NAMES):
            row_label = QtWidgets.QLabel(channel)
            row_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            row_label.setStyleSheet("font-weight: 600;")
            layout.addWidget(row_label, row + 1, 0)

            channel_lut = CHANNEL_LUTS[channel]
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
                # Заранее ставим нужный LUT — он больше не меняется.
                lut = DIFF_LUT if col == 3 else channel_lut
                image.setLookupTable(lut)
                # Заглушка с заведомо корректными levels — pyqtgraph не упадёт.
                image.setImage(_EMPTY, autoLevels=False, levels=(0.0, 1.0))
                plot.addItem(image)

                gw.setMinimumHeight(150)
                layout.addWidget(gw, row + 1, col + 1)
                row_images.append(image)

            self._images.append(row_images)

        for col in range(1, 5):
            layout.setColumnStretch(col, 1)
        for row in range(1, 4):
            layout.setRowStretch(row, 1)

    def show_empty(self) -> None:
        for row_imgs in self._images:
            for img in row_imgs:
                img.setImage(_EMPTY, autoLevels=False, levels=(0.0, 1.0))

    def update_frame_fast(
        self,
        lr: np.ndarray,
        hr: np.ndarray,
        sr: np.ndarray,
        diff: np.ndarray,
        field_levels: list[tuple[float, float]],
        diff_levels: list[tuple[float, float]],
    ) -> None:
        for ch_idx in range(len(_CHANNEL_NAMES)):
            fl = field_levels[ch_idx]
            dl = diff_levels[ch_idx]
            row_imgs = self._images[ch_idx]
            row_imgs[0].setImage(lr[ch_idx], autoLevels=False, levels=fl)
            row_imgs[1].setImage(hr[ch_idx], autoLevels=False, levels=fl)
            row_imgs[2].setImage(sr[ch_idx], autoLevels=False, levels=fl)
            row_imgs[3].setImage(diff[ch_idx], autoLevels=False, levels=dl)
