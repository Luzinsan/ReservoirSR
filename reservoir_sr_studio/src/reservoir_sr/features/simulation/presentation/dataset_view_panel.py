from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtWidgets


class DatasetViewPanel(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QFormLayout(self)

        self.archive_path_edit = QtWidgets.QLineEdit("")
        self.browse_button = QtWidgets.QPushButton("...")
        path_layout = QtWidgets.QHBoxLayout()
        path_layout.addWidget(self.archive_path_edit)
        path_layout.addWidget(self.browse_button)
        path_widget = QtWidgets.QWidget()
        path_widget.setLayout(path_layout)

        self.load_button = QtWidgets.QPushButton("Load dataset")
        self.resolution_combo = QtWidgets.QComboBox()
        self.resolution_combo.addItem("LR", "lr")
        self.resolution_combo.addItem("HR", "hr")
        self.loaded_label = QtWidgets.QLabel("Dataset not loaded")
        self.info_label = QtWidgets.QLabel("Нет загруженного архива")
        self.info_label.setWordWrap(True)
        self.step_label = QtWidgets.QLabel("Step: 0/0")
        self.step_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.step_slider.setRange(0, 0)
        self.step_slider.setEnabled(False)

        layout.addRow("File", path_widget)
        layout.addRow("", self.load_button)
        layout.addRow("Resolution", self.resolution_combo)
        layout.addRow("Archive", self.loaded_label)
        layout.addRow("Info", self.info_label)
        layout.addRow("Current step", self.step_label)
        layout.addRow("Timeline", self.step_slider)
