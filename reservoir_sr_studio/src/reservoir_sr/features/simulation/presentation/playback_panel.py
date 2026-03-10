from __future__ import annotations

from PySide6 import QtWidgets


class PlaybackPanel(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.start_button = QtWidgets.QPushButton("Start")
        self.pause_button = QtWidgets.QPushButton("Pause")
        self.step_button = QtWidgets.QPushButton("Step")
        self.reset_button = QtWidgets.QPushButton("Reset")
        self.apply_runtime_button = QtWidgets.QPushButton("Apply Runtime")

        for button in (
            self.start_button,
            self.pause_button,
            self.step_button,
            self.reset_button,
            self.apply_runtime_button,
        ):
            layout.addWidget(button)
