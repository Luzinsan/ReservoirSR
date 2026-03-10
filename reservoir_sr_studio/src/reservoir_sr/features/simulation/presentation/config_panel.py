from __future__ import annotations

from pathlib import Path

from PySide6 import QtWidgets


class ConfigPanel(QtWidgets.QGroupBox):
    def __init__(self) -> None:
        super().__init__("Конфигурационный файл")
        layout = QtWidgets.QVBoxLayout(self)

        path_layout = QtWidgets.QHBoxLayout()
        self.path_edit = QtWidgets.QLineEdit(str(Path.cwd() / "gui_config.json"))
        self.browse_button = QtWidgets.QPushButton("...")
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_button)

        buttons_layout = QtWidgets.QHBoxLayout()
        self.load_button = QtWidgets.QPushButton("Load")
        self.save_button = QtWidgets.QPushButton("Save")
        buttons_layout.addWidget(self.load_button)
        buttons_layout.addWidget(self.save_button)

        layout.addLayout(path_layout)
        layout.addLayout(buttons_layout)
