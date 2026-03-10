from __future__ import annotations

import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets


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

        opts_row = QtWidgets.QHBoxLayout()
        opts_row.addWidget(QtWidgets.QLabel("Палитра:"))
        self.palette_combo = QtWidgets.QComboBox()
        self.palette_combo.addItem("Географическая", "geographical")
        self.palette_combo.addItem("Вода и нефть", "water_oil")
        self.palette_combo.addItem("Грязь и вода", "mud_water")
        self.palette_combo.addItem("Океан", "ocean")
        self.palette_combo.addItem("Рассвет", "sunset")
        self.palette_combo.addItem("Закат", "dawn")
        self.palette_combo.addItem("Радуга", "rainbow")
        opts_row.addWidget(self.palette_combo)
        self.show_legend_checkbox = QtWidgets.QCheckBox("Легенда")
        self.show_legend_checkbox.setChecked(True)
        opts_row.addWidget(self.show_legend_checkbox)
        self.live_render_checkbox = QtWidgets.QCheckBox("Рендер в прямом эфире")
        self.live_render_checkbox.setChecked(True)
        opts_row.addWidget(self.live_render_checkbox)
        opts_row.addWidget(QtWidgets.QLabel("Изолинии:"))
        self.isoline_combo = QtWidgets.QComboBox()
        self.isoline_combo.addItem("Выкл", "off")
        self.isoline_combo.addItem("Поверх карты", "overlay")
        self.isoline_combo.addItem("Только изолинии", "only")
        opts_row.addWidget(self.isoline_combo)
        self.zoom_checkbox = QtWidgets.QCheckBox("Увеличение области")
        opts_row.addWidget(self.zoom_checkbox)
        self.zoom_reset_button = QtWidgets.QPushButton("Сброс зума")
        opts_row.addWidget(self.zoom_reset_button)
        opts_row.addWidget(QtWidgets.QLabel("Толщина изолиний"))
        self.isoline_width_spin = QtWidgets.QSpinBox()
        self.isoline_width_spin.setRange(1, 4)
        self.isoline_width_spin.setValue(2)
        opts_row.addWidget(self.isoline_width_spin)
        opts_row.addWidget(QtWidgets.QLabel("Частота изолиний"))
        self.isoline_stride_spin = QtWidgets.QSpinBox()
        self.isoline_stride_spin.setRange(1, 12)
        self.isoline_stride_spin.setValue(1)
        opts_row.addWidget(self.isoline_stride_spin)
        self.vector_color_button = QtWidgets.QPushButton("Цвет векторов")
        opts_row.addWidget(self.vector_color_button)
        opts_row.addStretch(1)
        layout.addLayout(opts_row)

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
