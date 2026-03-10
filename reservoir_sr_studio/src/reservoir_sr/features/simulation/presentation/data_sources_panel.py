from __future__ import annotations

from PySide6 import QtWidgets

from reservoir_sr.features.simulation.presentation.dataset_generation_panel import DatasetGenerationPanel
from reservoir_sr.features.simulation.presentation.dataset_view_panel import DatasetViewPanel
from reservoir_sr.features.simulation.presentation.runtime_panel import RuntimePanel


class DataSourcesPanel(QtWidgets.QGroupBox):
    def __init__(self) -> None:
        super().__init__("Источник данных")
        layout = QtWidgets.QVBoxLayout(self)

        self.mode_tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.mode_tabs)

        self.runtime_panel = RuntimePanel()
        self.mode_tabs.addTab(self.runtime_panel, "Runtime")

        self.dataset_generation_panel = DatasetGenerationPanel()
        self.mode_tabs.addTab(self.dataset_generation_panel, "Dataset generation")

        self.dataset_view_panel = DatasetViewPanel()
        self.mode_tabs.addTab(self.dataset_view_panel, "Dataset view")
