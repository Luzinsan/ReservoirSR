from __future__ import annotations

from PySide6 import QtWidgets


class PlaybackPanel(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        settings_row = QtWidgets.QHBoxLayout()
        settings_row.addWidget(QtWidgets.QLabel("Step batch"))
        self.batch_spin = QtWidgets.QSpinBox()
        self.batch_spin.setRange(1, 5000)
        self.batch_spin.setValue(10)
        settings_row.addWidget(self.batch_spin)

        settings_row.addWidget(QtWidgets.QLabel("Interval (ms)"))
        self.interval_spin = QtWidgets.QSpinBox()
        self.interval_spin.setRange(10, 10000)
        self.interval_spin.setValue(100)
        self.interval_spin.setSingleStep(50)
        settings_row.addWidget(self.interval_spin)

        settings_row.addStretch(1)
        layout.addLayout(settings_row)

        buttons_row = QtWidgets.QHBoxLayout()

        self.start_button = QtWidgets.QPushButton("Start")
        self.pause_button = QtWidgets.QPushButton("Pause")
        self.step_button = QtWidgets.QPushButton("Step")

        for button in (
            self.start_button,
            self.pause_button,
            self.step_button,
        ):
            buttons_row.addWidget(button)
        layout.addLayout(buttons_row)
