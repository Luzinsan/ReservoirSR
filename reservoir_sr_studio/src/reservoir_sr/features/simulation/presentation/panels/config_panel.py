from __future__ import annotations

from PySide6 import QtWidgets


class ConfigPanel(QtWidgets.QGroupBox):
    def __init__(self) -> None:
        super().__init__("Configuration file")
        layout = QtWidgets.QVBoxLayout(self)

        path_layout = QtWidgets.QHBoxLayout()
        self.path_edit = QtWidgets.QLineEdit()
        self.path_edit.setPlaceholderText("Path to simulation JSON config")
        browse_button = QtWidgets.QPushButton("...")
        browse_button.clicked.connect(self._on_browse)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(browse_button)

        buttons_layout = QtWidgets.QHBoxLayout()
        self.load_button = QtWidgets.QPushButton("Load")
        self.save_button = QtWidgets.QPushButton("Save")
        buttons_layout.addWidget(self.load_button)
        buttons_layout.addWidget(self.save_button)

        layout.addLayout(path_layout)
        layout.addLayout(buttons_layout)

    def _on_browse(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select config", self.path_edit.text(), "JSON (*.json)",
        )
        if file_path:
            self.path_edit.setText(file_path)
