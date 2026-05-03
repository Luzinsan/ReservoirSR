from __future__ import annotations

import pyqtgraph as pg
from PySide6 import QtWidgets


class MapsPanel(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QtWidgets.QVBoxLayout(self)

        top_row = QtWidgets.QHBoxLayout()
        self.title_label = QtWidgets.QLabel("Распределение насыщенности ST")
        top_row.addWidget(self.title_label, stretch=1)
        top_row.addWidget(QtWidgets.QLabel("Режим карты:"))
        self.render_mode_combo = QtWidgets.QComboBox()
        self.render_mode_combo.addItem("Упрощенная", "simple")
        self.render_mode_combo.addItem("Сглаженная", "smooth")
        top_row.addWidget(self.render_mode_combo)
        layout.addLayout(top_row)

        body = QtWidgets.QHBoxLayout()
        layout.addLayout(body, stretch=1)

        field_widget = QtWidgets.QWidget()
        field_widget.setMaximumWidth(86)
        field_layout = QtWidgets.QGridLayout(field_widget)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setHorizontalSpacing(4)
        field_layout.setVerticalSpacing(4)

        self.field_button_map: dict[str, str] = {}
        self.field_buttons: dict[str, QtWidgets.QPushButton] = {}
        legacy_buttons = [
            ("Kx", "P"),
            ("Kz", "P"),
            ("Sb", "SB"),
            ("St", "ST"),
            ("P", "P"),
            ("Pv", "P"),
            ("Sv", "ST"),
            ("Sg", "SB"),
            ("V", "ST"),
            ("U", "SB"),
        ]
        for index, (label, field) in enumerate(legacy_buttons):
            button = QtWidgets.QPushButton(label)
            button.setCheckable(True)
            button.setFixedSize(34, 26)
            row, col = divmod(index, 2)
            field_layout.addWidget(button, row, col)
            self.field_button_map[label] = field
            self.field_buttons[label] = button
        body.addWidget(field_widget, stretch=0)

        self.plot = pg.PlotWidget()
        self.plot.setBackground("w")
        self.plot.showGrid(x=True, y=True, alpha=0.35)
        self.plot.setMenuEnabled(False)
        self.plot.getPlotItem().hideButtons()
        self.plot.getPlotItem().setMouseEnabled(x=False, y=False)
        self.plot.getViewBox().invertY(True)
        self.plot.getViewBox().setAspectLocked(False)
        self.plot.setLabel("bottom", "r")
        self.plot.setLabel("left", "z")
        self.plot.setMinimumHeight(420)
        self.plot.setMinimumWidth(900)
        self.image = pg.ImageItem(axisOrder="row-major")
        self.image.setAutoDownsample(True)
        self.plot.addItem(self.image)
        body.addWidget(self.plot, stretch=1)

        self.legend_label = QtWidgets.QLabel()
        self.legend_label.setMinimumHeight(24)
        self.legend_label.setMaximumHeight(30)
        layout.addWidget(self.legend_label)

        self._init_scaling()

    def _init_scaling(self) -> None:
        self.plot.getViewBox().setDefaultPadding(0.0)
