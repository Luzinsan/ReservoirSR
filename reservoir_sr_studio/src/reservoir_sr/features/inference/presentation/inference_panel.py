from __future__ import annotations

from PySide6 import QtWidgets


class InferencePanel(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QtWidgets.QVBoxLayout(self)
        title = QtWidgets.QLabel("Inference Module")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        description = QtWidgets.QLabel(
            "This module is reserved for inference and result analysis pipelines.\n"
            "Use this top-level tab to run super-resolution models and inspect outputs."
        )
        description.setWordWrap(True)

        placeholder = QtWidgets.QGroupBox("Inference Workspace")
        placeholder_layout = QtWidgets.QVBoxLayout(placeholder)
        placeholder_layout.addWidget(
            QtWidgets.QLabel("Architecture-first placeholder. Add model serving and batch inference controls here.")
        )

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(placeholder)
        layout.addStretch(1)
