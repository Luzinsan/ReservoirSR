from __future__ import annotations

from PySide6 import QtWidgets


class RuntimePanel(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        runtime_form = QtWidgets.QFormLayout(self)

        self.nx_spin = QtWidgets.QSpinBox()
        self.nx_spin.setRange(2, 512)
        self.nx_spin.setValue(100)
        self.nz_spin = QtWidgets.QSpinBox()
        self.nz_spin.setRange(1, 100_000)
        self.nz_spin.setReadOnly(True)
        self.nz_spin.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.nz_spin.setValue(1)
        self.q_zab_spin = QtWidgets.QDoubleSpinBox()
        self.q_zab_spin.setRange(0.0, 1e6)
        self.q_zab_spin.setDecimals(6)
        self.q_zab_spin.setValue(50.0)
        self.obv_p_spin = QtWidgets.QDoubleSpinBox()
        self.obv_p_spin.setRange(0.0, 1e6)
        self.obv_p_spin.setDecimals(6)
        self.obv_p_spin.setValue(180.0)
        self.r_skv_spin = QtWidgets.QDoubleSpinBox()
        self.r_skv_spin.setRange(0.0, 1e6)
        self.r_skv_spin.setDecimals(6)
        self.r_skv_spin.setValue(0.1)
        self.mu_pazp_spin = QtWidgets.QDoubleSpinBox()
        self.mu_pazp_spin.setRange(0.0, 1e6)
        self.mu_pazp_spin.setDecimals(6)
        self.mu_pazp_spin.setValue(8.0)

        runtime_form.addRow("NX", self.nx_spin)
        runtime_form.addRow("NZ", self.nz_spin)
        runtime_form.addRow("Q_zab", self.q_zab_spin)
        runtime_form.addRow("Obv_p", self.obv_p_spin)
        runtime_form.addRow("R_skv", self.r_skv_spin)
        runtime_form.addRow("Mu_pazp", self.mu_pazp_spin)
