from __future__ import annotations

from pathlib import Path

from PySide6 import QtWidgets


class DatasetGenerationPanel(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QFormLayout(self)

        self.output_dir_edit = QtWidgets.QLineEdit(str(Path.cwd() / "dataset_out"))
        self.browse_button = QtWidgets.QPushButton("...")
        out_layout = QtWidgets.QHBoxLayout()
        out_layout.addWidget(self.output_dir_edit)
        out_layout.addWidget(self.browse_button)
        out_widget = QtWidgets.QWidget()
        out_widget.setLayout(out_layout)
        self.job_id_edit = QtWidgets.QLineEdit("")
        self.steps_spin = QtWidgets.QSpinBox()
        self.steps_spin.setRange(1, 1_000_000)
        self.steps_spin.setValue(500)
        self.start_button = QtWidgets.QPushButton("Start dataset job")
        self.cancel_button = QtWidgets.QPushButton("Cancel dataset job")
        self.progress_bar = QtWidgets.QProgressBar()
        self.status_label = QtWidgets.QLabel("idle")

        layout.addRow("Output dir", out_widget)
        layout.addRow("Job ID", self.job_id_edit)
        layout.addRow("Steps", self.steps_spin)
        layout.addRow(self.start_button)
        layout.addRow(self.cancel_button)
        layout.addRow("Progress", self.progress_bar)
        layout.addRow("Status", self.status_label)
