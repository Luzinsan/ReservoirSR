from __future__ import annotations

import sys
import uuid
from dataclasses import asdict

from PySide6 import QtCore, QtGui, QtWidgets

from reservoir_sr.app.modules.data_module_methods import DataModuleMethods
from reservoir_sr.domain.simulation.config_models import SimulationConfig
from reservoir_sr.features.inference.presentation.inference_panel import InferencePanel
from reservoir_sr.features.simulation.application.config_persistence_service import ConfigPersistenceService
from reservoir_sr.features.simulation.application.dataset_generation_service import DatasetGenerationService
from reservoir_sr.features.simulation.application.dataset_view_service import DatasetViewService
from reservoir_sr.features.simulation.application.runtime_service import RuntimeService
from reservoir_sr.features.simulation.presentation.config_panel import ConfigPanel
from reservoir_sr.features.simulation.presentation.data_sources_panel import DataSourcesPanel
from reservoir_sr.features.simulation.presentation.maps_panel import MapsPanel
from reservoir_sr.features.simulation.presentation.metrics_panel import MetricsPanel
from reservoir_sr.features.simulation.presentation.playback_panel import PlaybackPanel
from reservoir_sr.features.simulation.presentation.plot_controller import PlotController
from reservoir_sr.features.simulation.presentation.state import (
    DatasetJobViewState,
    DatasetViewState,
    MetricsState,
    RenderViewState,
    RuntimeTrackingState,
    RuntimeViewState,
    ViewMode,
)
from reservoir_sr.features.training.presentation.training_panel import TrainingPanel
from reservoir_sr.infrastructure.grpc.simulation_client import GrpcSimulationClient


class MainWindow(DataModuleMethods, QtWidgets.QMainWindow):
    def __init__(self, endpoint: str = "localhost:5000") -> None:
        super().__init__()
        self.runtime_state = RuntimeViewState(endpoint=endpoint, simulation_id=f"sim_{uuid.uuid4().hex[:8]}")
        self.dataset_job_state = DatasetJobViewState()
        self.dataset_view_state = DatasetViewState()
        self.render_state = RenderViewState()
        self.metrics_state = MetricsState()
        self.tracking_state = RuntimeTrackingState()
        self.view_mode = ViewMode.RUNTIME
        self.defaults = SimulationConfig()
        self.config_keys = set(asdict(self.defaults).keys())
        self.runtime_state.payload = asdict(self.defaults)

        self.client = GrpcSimulationClient(endpoint)
        self.runtime_service = RuntimeService(self.client)
        self.generation_service = DatasetGenerationService(endpoint)
        self.view_service = DatasetViewService()
        self.config_service = ConfigPersistenceService()
        self.plot_controller = PlotController()

        self.runtime_timer = QtCore.QTimer(self)
        self.runtime_timer.timeout.connect(self.on_timer_tick)
        self.dataset_timer = QtCore.QTimer(self)
        self.dataset_timer.timeout.connect(self._poll_dataset_status)

        self.layer_lines: list[object] = []
        self.layer_labels: list[object] = []
        self.isoline_items: list[object] = []
        self.vector_items: list[object] = []

        self._build_ui(endpoint)
        self._init_simulation()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.runtime_timer.stop()
        self.dataset_timer.stop()
        self.client.close()
        super().closeEvent(event)

    def _build_ui(self, endpoint: str) -> None:
        self.setWindowTitle("Фильтрация в трещиновато-пористом пласте (Python)")
        self.resize(1500, 950)

        toolbar = self.addToolBar("Main")
        self.act_start = QtGui.QAction("Тест", self)
        self.act_metrics = QtGui.QAction("Характеристики", self)
        self.act_settings = QtGui.QAction("Настройки", self)
        self.act_start.triggered.connect(self.on_start)
        toolbar.addAction(self.act_start)
        toolbar.addAction(self.act_metrics)
        toolbar.addAction(self.act_settings)

        self.module_tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.module_tabs)
        data_module = QtWidgets.QWidget()
        self.module_tabs.addTab(data_module, "Data")
        self.training_panel = TrainingPanel()
        self.module_tabs.addTab(self.training_panel, "Training")
        self.inference_panel = InferencePanel()
        self.module_tabs.addTab(self.inference_panel, "Inference")

        root_layout = QtWidgets.QHBoxLayout(data_module)
        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)
        left.setMinimumWidth(320)
        left.setMaximumWidth(420)
        root_layout.addWidget(left, stretch=0)

        self.config_panel = ConfigPanel()
        left_layout.addWidget(self.config_panel)

        self.data_sources_panel = DataSourcesPanel()
        self.runtime_panel = self.data_sources_panel.runtime_panel
        self.dataset_generation_panel = self.data_sources_panel.dataset_generation_panel
        self.dataset_view_panel = self.data_sources_panel.dataset_view_panel
        self.runtime_panel.endpoint_edit.setText(endpoint)
        self.runtime_panel.simulation_id_edit.setText(self.runtime_state.simulation_id)
        self.runtime_panel.nx_spin.setValue(self.defaults.nx)
        self.runtime_panel.n_dr_spin.setValue(self.defaults.n_dr)
        self.runtime_panel.epsp_spin.setValue(self.defaults.epsp)
        self.runtime_panel.tu_spin.setValue(self.defaults.tu_seconds)
        self.runtime_panel.tk_spin.setValue(self.defaults.tk_days)
        left_layout.addWidget(self.data_sources_panel)

        self.playback_panel = PlaybackPanel()
        left_layout.addWidget(self.playback_panel)
        left_layout.addStretch(1)

        self.tabs = QtWidgets.QTabWidget()
        root_layout.addWidget(self.tabs, stretch=1)
        self.maps_panel = MapsPanel()
        self.metrics_panel = MetricsPanel()
        self.tabs.addTab(self.maps_panel, "Карты")
        self.tabs.addTab(self.metrics_panel, "Характеристики")

        self.status_runtime = QtWidgets.QLabel("t=0.0  Q=0.0  Pz=0.0  H2O=0.0%")
        self.statusBar().addWidget(self.status_runtime, 1)

        self.act_metrics.triggered.connect(lambda: self.tabs.setCurrentIndex(1))
        self.act_settings.triggered.connect(lambda: self.tabs.setCurrentIndex(0))
        self.module_tabs.currentChanged.connect(self._on_module_tab_changed)
        self.playback_panel.start_button.clicked.connect(self.on_start)
        self.playback_panel.pause_button.clicked.connect(self.on_pause)
        self.playback_panel.step_button.clicked.connect(self.on_step)
        self.playback_panel.reset_button.clicked.connect(self.on_reset)
        self.playback_panel.apply_runtime_button.clicked.connect(self._init_simulation)
        self.config_panel.browse_button.clicked.connect(self.on_browse_cfg)
        self.config_panel.load_button.clicked.connect(self.on_load_cfg)
        self.config_panel.save_button.clicked.connect(self.on_save_cfg)
        self.dataset_generation_panel.browse_button.clicked.connect(self.on_browse_dataset_out)
        self.dataset_view_panel.browse_button.clicked.connect(self.on_browse_dataset_file)
        self.dataset_view_panel.load_button.clicked.connect(self.on_load_dataset_file)
        self.dataset_generation_panel.start_button.clicked.connect(self.on_dataset_start)
        self.dataset_generation_panel.cancel_button.clicked.connect(self.on_dataset_cancel)
        self.data_sources_panel.mode_tabs.currentChanged.connect(self.on_mode_tab_changed)
        self.dataset_view_panel.resolution_combo.currentIndexChanged.connect(self.on_dataset_resolution_changed)
        self.dataset_view_panel.step_slider.valueChanged.connect(self.on_dataset_slider_changed)
        self.maps_panel.render_mode_combo.currentIndexChanged.connect(self.on_render_mode_changed)
        self.maps_panel.isoline_combo.currentIndexChanged.connect(self.on_isoline_layer_changed)
        self.maps_panel.palette_combo.currentIndexChanged.connect(self.on_palette_changed)
        self.maps_panel.show_legend_checkbox.toggled.connect(self.on_toggle_legend)
        self.maps_panel.live_render_checkbox.toggled.connect(self.on_toggle_live_render)
        self.maps_panel.zoom_checkbox.toggled.connect(self.on_toggle_zoom)
        self.maps_panel.zoom_reset_button.clicked.connect(self.on_zoom_reset)
        self.maps_panel.isoline_width_spin.valueChanged.connect(self.on_isoline_width_changed)
        self.maps_panel.isoline_stride_spin.valueChanged.connect(self.on_isoline_stride_changed)
        self.maps_panel.vector_color_button.clicked.connect(self.on_pick_vector_color)

        for label, button in self.maps_panel.field_buttons.items():
            field = self.maps_panel.field_button_map[label]
            button.clicked.connect(lambda checked=False, f=field: self.on_select_field(f))

        self._sync_field_buttons()
        self._update_mode_controls()

    def _is_data_module_active(self) -> bool:
        return self.module_tabs.currentIndex() == 0

    def _on_module_tab_changed(self, _: int) -> None:
        if not self._is_data_module_active() and self.runtime_timer.isActive():
            self.on_pause()
        self._update_mode_controls()


def main() -> None:
    endpoint = "localhost:5000"
    if len(sys.argv) > 1:
        endpoint = sys.argv[1]
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(endpoint=endpoint)
    window.show()
    sys.exit(app.exec())
