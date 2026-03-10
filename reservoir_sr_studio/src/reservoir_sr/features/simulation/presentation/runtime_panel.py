from __future__ import annotations

from PySide6 import QtWidgets

from reservoir_sr.features.simulation.presentation.dataset_view_panel import DatasetViewPanel


class RuntimePanel(QtWidgets.QGroupBox):
    def __init__(self) -> None:
        super().__init__("Источник данных")
        layout = QtWidgets.QVBoxLayout(self)

        self.mode_tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.mode_tabs)

        runtime_tab = QtWidgets.QWidget()
        runtime_form = QtWidgets.QFormLayout(runtime_tab)

        self.endpoint_edit = QtWidgets.QLineEdit("localhost:5000")
        self.simulation_id_edit = QtWidgets.QLineEdit("sim_main")
        self.nx_spin = QtWidgets.QSpinBox()
        self.nx_spin.setRange(2, 512)
        self.nx_spin.setValue(100)
        self.n_dr_spin = QtWidgets.QSpinBox()
        self.n_dr_spin.setRange(1, 5000)
        self.n_dr_spin.setValue(10)
        self.epsp_spin = QtWidgets.QDoubleSpinBox()
        self.epsp_spin.setRange(1e-10, 1.0)
        self.epsp_spin.setDecimals(8)
        self.epsp_spin.setValue(1e-6)
        self.tu_spin = QtWidgets.QDoubleSpinBox()
        self.tu_spin.setRange(0.001, 1e6)
        self.tu_spin.setDecimals(6)
        self.tu_spin.setValue(86.4)
        self.tk_spin = QtWidgets.QDoubleSpinBox()
        self.tk_spin.setRange(1e-6, 1e6)
        self.tk_spin.setDecimals(6)
        self.tk_spin.setValue(1000.3)
        self.batch_spin = QtWidgets.QSpinBox()
        self.batch_spin.setRange(1, 5000)
        self.batch_spin.setValue(10)
        self.timer_spin = QtWidgets.QSpinBox()
        self.timer_spin.setRange(10, 2000)
        self.timer_spin.setValue(50)

        runtime_form.addRow("endpoint", self.endpoint_edit)
        runtime_form.addRow("simulation_id", self.simulation_id_edit)
        runtime_form.addRow("NX", self.nx_spin)
        runtime_form.addRow("N_Dr", self.n_dr_spin)
        runtime_form.addRow("EPSP", self.epsp_spin)
        runtime_form.addRow("TU (sec)", self.tu_spin)
        runtime_form.addRow("TK (days)", self.tk_spin)
        runtime_form.addRow("step_batch", self.batch_spin)
        runtime_form.addRow("timer (ms)", self.timer_spin)

        self.mode_tabs.addTab(runtime_tab, "Runtime")

        self.dataset_panel = DatasetViewPanel()
        self.mode_tabs.addTab(self.dataset_panel, "Dataset")
