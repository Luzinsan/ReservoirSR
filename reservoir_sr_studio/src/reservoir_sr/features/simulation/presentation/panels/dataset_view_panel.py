from __future__ import annotations

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
        self.folder_path_edit = QtWidgets.QLineEdit("")
        self.browse_folder_button = QtWidgets.QPushButton("...")
        folder_layout = QtWidgets.QHBoxLayout()
        folder_layout.addWidget(self.folder_path_edit)
        folder_layout.addWidget(self.browse_folder_button)
        folder_widget = QtWidgets.QWidget()
        folder_widget.setLayout(folder_layout)

        self.load_button = QtWidgets.QPushButton("Load simulation archive")
        self.load_folder_button = QtWidgets.QPushButton("Load folder archives")
        self.folder_limit_spin = QtWidgets.QSpinBox()
        self.folder_limit_spin.setRange(1, 100_000)
        self.folder_limit_spin.setValue(100)
        self.resolution_combo = QtWidgets.QComboBox()
        self.resolution_combo.addItem("LR", "lr")
        self.resolution_combo.addItem("HR", "hr")
        self.loaded_label = QtWidgets.QLabel("Simulation archive not loaded")
        self.info_label = QtWidgets.QLabel("Нет загруженного архива")
        self.info_label.setWordWrap(True)
        self.step_label = QtWidgets.QLabel("Step: 0/0")
        self.step_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.step_slider.setRange(0, 0)
        self.step_slider.setEnabled(False)

        layout.addRow("File", path_widget)
        layout.addRow("", self.load_button)
        layout.addRow("Folder", folder_widget)
        layout.addRow("Max archives (N)", self.folder_limit_spin)
        layout.addRow("", self.load_folder_button)
        layout.addRow("Resolution", self.resolution_combo)
        layout.addRow("Simulation archive", self.loaded_label)
        layout.addRow("Info", self.info_label)
        layout.addRow("Current step", self.step_label)
        layout.addRow("Timeline", self.step_slider)
