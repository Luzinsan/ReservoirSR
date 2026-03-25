from PySide6 import QtWidgets

from reservoir_sr.features.simulation.presentation.panels.config_panel import ConfigPanel
from reservoir_sr.features.simulation.presentation.panels.data_sources_panel import DataSourcesPanel
from reservoir_sr.features.simulation.presentation.panels.maps_panel import MapsPanel
from reservoir_sr.features.simulation.presentation.panels.metrics_panel import MetricsPanel
from reservoir_sr.features.simulation.presentation.panels.playback_panel import PlaybackPanel


class DataTabPanel(QtWidgets.QWidget):
    """UI-каркас вкладки Data. Без бизнес-логики."""
    
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.config_panel = ConfigPanel()
        self.data_sources_panel = DataSourcesPanel()
        self.playback_panel = PlaybackPanel()
        self.maps_widget = MapsPanel()
        self.metrics_widget = MetricsPanel()

        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QtWidgets.QHBoxLayout(self)

        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)
        left.setMinimumWidth(320)
        left.setMaximumWidth(420)
        root_layout.addWidget(left, stretch=0)

        left_layout.addWidget(self.config_panel)
        left_layout.addWidget(self.data_sources_panel)

        left_layout.addWidget(self.playback_panel)
        left_layout.addStretch(1)

        self.tabs = QtWidgets.QTabWidget()
        root_layout.addWidget(self.tabs, stretch=1)
        self.tabs.addTab(self.maps_widget, "Карты")
        self.tabs.addTab(self.metrics_widget, "Характеристики")
