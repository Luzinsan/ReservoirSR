from __future__ import annotations

from PySide6 import QtWidgets

from reservoir_sr.features.simulation.presentation.panels.dataset_generation_panel import (
    DatasetGenerationPanel,
)
from reservoir_sr.features.simulation.presentation.panels.dataset_view_panel import DatasetViewPanel
from reservoir_sr.features.simulation.presentation.panels.runtime_panel import RuntimePanel


class DataSourcesPanel(QtWidgets.QGroupBox):

    def __init__(self) -> None:
        super().__init__("Data source")
        layout = QtWidgets.QVBoxLayout(self)

        self.mode_tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.mode_tabs)

        self.runtime_widget = RuntimePanel()
        self.mode_tabs.addTab(self.runtime_widget, "Runtime")

        self.dataset_generation_widget = DatasetGenerationPanel()
        self.mode_tabs.addTab(self.dataset_generation_widget, "Simulation generation")

        self.dataset_view_widget = DatasetViewPanel()
        self.mode_tabs.addTab(self.dataset_view_widget, "Simulation run view")
