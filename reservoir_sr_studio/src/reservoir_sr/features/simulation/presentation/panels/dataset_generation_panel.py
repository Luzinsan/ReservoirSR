from __future__ import annotations

from pathlib import Path

from PySide6 import QtWidgets


class DatasetGenerationPanel(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        main_layout = QtWidgets.QVBoxLayout(self)

        form = QtWidgets.QFormLayout()
        main_layout.addLayout(form)

        # ------------------------------------------------------------------
        # Common fields
        # ------------------------------------------------------------------
        self.output_dir_edit = QtWidgets.QLineEdit(str(Path.cwd() / "dataset_out"))
        browse_button = QtWidgets.QPushButton("...")
        browse_button.clicked.connect(self._on_browse)
        out_layout = QtWidgets.QHBoxLayout()
        out_layout.addWidget(self.output_dir_edit)
        out_layout.addWidget(browse_button)
        out_widget = QtWidgets.QWidget()
        out_widget.setLayout(out_layout)
        form.addRow("Output dir", out_widget)

        self.job_id_edit = QtWidgets.QLineEdit("")
        form.addRow("Job ID", self.job_id_edit)

        self.steps_spin = QtWidgets.QSpinBox()
        self.steps_spin.setRange(1, 1_000_000)
        self.steps_spin.setValue(500)
        form.addRow("Steps", self.steps_spin)

        self.snapshot_stride_spin = QtWidgets.QSpinBox()
        self.snapshot_stride_spin.setRange(1, 1_000_000)
        self.snapshot_stride_spin.setValue(1)
        form.addRow("Snapshot stride", self.snapshot_stride_spin)

        self.lr_nx_spin = QtWidgets.QSpinBox()
        self.lr_nx_spin.setRange(2, 4096)
        self.lr_nx_spin.setValue(100)
        form.addRow("LR NX", self.lr_nx_spin)

        self.hr_nx_spin = QtWidgets.QSpinBox()
        self.hr_nx_spin.setRange(2, 8192)
        self.hr_nx_spin.setValue(400)
        form.addRow("HR NX", self.hr_nx_spin)

        self.fixed_tu_spin = QtWidgets.QDoubleSpinBox()
        self.fixed_tu_spin.setRange(1e-4, 1e6)
        self.fixed_tu_spin.setDecimals(6)
        self.fixed_tu_spin.setValue(86.4)
        form.addRow("TU (sec)", self.fixed_tu_spin)

        self.fixed_epsp_spin = QtWidgets.QDoubleSpinBox()
        self.fixed_epsp_spin.setRange(1e-12, 1.0)
        self.fixed_epsp_spin.setDecimals(10)
        self.fixed_epsp_spin.setValue(1e-6)
        form.addRow("EPSP", self.fixed_epsp_spin)

        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItem("Single simulation", "single")
        self.mode_combo.addItem("Simulation campaign", "campaign")
        form.addRow("Generation mode", self.mode_combo)

        # ------------------------------------------------------------------
        # Single vs Campaign (stacked UI)
        # ------------------------------------------------------------------
        self.mode_stack = QtWidgets.QStackedWidget()
        main_layout.addWidget(self.mode_stack)

        single_page = QtWidgets.QWidget()
        single_layout = QtWidgets.QVBoxLayout(single_page)
        single_layout.addWidget(QtWidgets.QLabel("Single: run one simulation job."))
        single_layout.addStretch(1)
        self.mode_stack.addWidget(single_page)

        campaign_page = QtWidgets.QWidget()
        campaign_layout = QtWidgets.QFormLayout(campaign_page)

        self.strategy_combo = QtWidgets.QComboBox()
        self.strategy_combo.addItem("Latin Hypercube Sampling (LHS)", "lhs")
        campaign_layout.addRow("Campaign strategy", self.strategy_combo)

        self.sample_count_spin = QtWidgets.QSpinBox()
        self.sample_count_spin.setRange(1, 50_000)
        self.sample_count_spin.setValue(32)
        campaign_layout.addRow("Simulations", self.sample_count_spin)

        self.seed_spin = QtWidgets.QSpinBox()
        self.seed_spin.setRange(0, 2_147_483_647)
        self.seed_spin.setValue(1234)
        campaign_layout.addRow("Seed", self.seed_spin)

        self.workers_spin = QtWidgets.QSpinBox()
        self.workers_spin.setRange(1, 64)
        self.workers_spin.setValue(4)
        campaign_layout.addRow("Workers", self.workers_spin)

        self.mode_stack.addWidget(campaign_page)
        self.mode_stack.setCurrentIndex(0)

        self.mode_combo.currentIndexChanged.connect(self._on_mode_combo_changed)

        # ------------------------------------------------------------------
        # Progress
        # ------------------------------------------------------------------
        self.progress_bar = QtWidgets.QProgressBar()
        main_layout.addWidget(self.progress_bar)

    def _on_mode_combo_changed(self) -> None:
        mode = self.mode_combo.currentData()
        self.mode_stack.setCurrentIndex(1 if mode == "campaign" else 0)

    def _on_browse(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select output directory", self.output_dir_edit.text(),
        )
        if folder:
            self.output_dir_edit.setText(folder)
