from __future__ import annotations

import pyqtgraph as pg
from PySide6 import QtWidgets


class MapsPanel(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QtWidgets.QVBoxLayout(self)

        top_row = QtWidgets.QHBoxLayout()
        self.title_label = QtWidgets.QLabel("ST saturation distribution")
        top_row.addWidget(self.title_label, stretch=1)
        top_row.addWidget(QtWidgets.QLabel("Render mode:"))
        self.render_mode_combo = QtWidgets.QComboBox()
        self.render_mode_combo.addItem("Simple", "simple")
        self.render_mode_combo.addItem("Smooth", "smooth")
        self.render_mode_combo.addItem("SR (neural)", "sr")
        top_row.addWidget(self.render_mode_combo)
        top_row.addWidget(QtWidgets.QLabel("SR model:"))
        self.sr_model_combo = QtWidgets.QComboBox()
        self.sr_model_combo.setMinimumWidth(220)
        self.sr_model_combo.setEnabled(False)
        top_row.addWidget(self.sr_model_combo)
        layout.addLayout(top_row)

        body = QtWidgets.QHBoxLayout()
        layout.addLayout(body, stretch=1)

        field_widget = QtWidgets.QWidget()
        field_widget.setMaximumWidth(60)
        field_layout = QtWidgets.QVBoxLayout(field_widget)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setSpacing(4)

        self.field_button_map: dict[str, str] = {}
        self.field_buttons: dict[str, QtWidgets.QPushButton] = {}
        field_definitions = [
            ("P", "P"),
            ("ST", "ST"),
            ("SB", "SB"),
        ]
        for label, field in field_definitions:
            button = QtWidgets.QPushButton(label)
            button.setCheckable(True)
            button.setFixedSize(48, 28)
            field_layout.addWidget(button)
            self.field_button_map[label] = field
            self.field_buttons[label] = button
        field_layout.addStretch(1)
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
