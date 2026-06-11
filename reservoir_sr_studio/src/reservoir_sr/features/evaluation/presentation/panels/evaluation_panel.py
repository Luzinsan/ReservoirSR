from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtWidgets

from reservoir_sr.features.evaluation.presentation.panels.field_comparison_grid import (
    FieldComparisonGrid,
)


class EvaluationPanel(QtWidgets.QWidget):

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QtWidgets.QHBoxLayout(self)

        # ── Left column: controls ────────────────────────────
        left = QtWidgets.QWidget()
        left.setMinimumWidth(360)
        left.setMaximumWidth(440)
        left_layout = QtWidgets.QVBoxLayout(left)

        controls = QtWidgets.QGroupBox("Evaluation controls")
        form = QtWidgets.QFormLayout(controls)

        self.model_combo = QtWidgets.QComboBox()
        self.model_combo.setMinimumWidth(260)
        form.addRow("Model", self.model_combo)

        self.split_combo = QtWidgets.QComboBox()
        for s in ("train", "val", "test"):
            self.split_combo.addItem(s, s)
        self.split_combo.setCurrentIndex(2)
        form.addRow("Split", self.split_combo)

        self.archive_combo = QtWidgets.QComboBox()
        self.archive_combo.setMinimumWidth(260)
        form.addRow("Archive", self.archive_combo)

        self.step_label = QtWidgets.QLabel("Step: 0/0")
        self.step_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.step_slider.setRange(0, 0)
        self.step_slider.setEnabled(False)
        form.addRow("Current step", self.step_label)
        form.addRow("Timeline", self.step_slider)

        left_layout.addWidget(controls)

        self.prefetch_button = QtWidgets.QPushButton("Prefetch all SR for current archive")
        self.prefetch_button.setEnabled(False)
        left_layout.addWidget(self.prefetch_button)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)

        self.status_label = QtWidgets.QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #666;")
        left_layout.addWidget(self.status_label)
        left_layout.addStretch(1)

        root.addWidget(left, 0)

        # ── Right column: 3×4 grid ───────────────────────────
        self.grid = FieldComparisonGrid()
        root.addWidget(self.grid, 1)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def set_models(self, paths: list[Path]) -> None:
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        for p in paths:
            self.model_combo.addItem(p.name, str(p))
        self.model_combo.blockSignals(False)

    def set_archives(self, paths: list[Path]) -> None:
        self.archive_combo.blockSignals(True)
        self.archive_combo.clear()
        self.archive_combo.addItem("— select archive —", -1)
        for i, p in enumerate(paths):
            self.archive_combo.addItem(p.name, i)
        self.archive_combo.setCurrentIndex(0)
        self.archive_combo.blockSignals(False)

    def update_step(self, current: int, total: int, slider_value: int) -> None:
        self.step_label.setText(f"Step: {current}/{total}")
        self.step_slider.blockSignals(True)
        self.step_slider.setRange(0, max(total - 1, 0))
        self.step_slider.setValue(slider_value)
        self.step_slider.setEnabled(total > 1)
        self.step_slider.blockSignals(False)

    def set_progress(self, current: int, total: int, visible: bool) -> None:
        self.progress_bar.setVisible(visible)
        if visible:
            self.progress_bar.setRange(0, max(total, 1))
            self.progress_bar.setValue(current)
