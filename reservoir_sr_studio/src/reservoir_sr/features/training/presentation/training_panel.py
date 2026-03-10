from __future__ import annotations

from PySide6 import QtWidgets


class TrainingPanel(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QtWidgets.QVBoxLayout(self)
        title = QtWidgets.QLabel("Training Module")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        description = QtWidgets.QLabel(
            "This module is reserved for model training workflows.\n"
            "Use this top-level tab to configure datasets, training runs, and monitoring."
        )
        description.setWordWrap(True)

        placeholder = QtWidgets.QGroupBox("Training Workspace")
        placeholder_layout = QtWidgets.QVBoxLayout(placeholder)
        placeholder_layout.addWidget(
            QtWidgets.QLabel("Architecture-first placeholder. Add trainers and experiment controls here.")
        )

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(placeholder)
        layout.addStretch(1)
