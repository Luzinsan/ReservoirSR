from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6 import QtWidgets

from reservoir_sr.app.app_context import AppContext, AppModuleTab
from reservoir_sr.common.logging import EventLogger
from reservoir_sr.common.qt_binding import autobind
from reservoir_sr.features.simulation.presentation.controllers.dataset_view_controller import DatasetViewController
from reservoir_sr.features.simulation.presentation.controllers.generation_controller import GenerationController
from reservoir_sr.features.simulation.presentation.controllers.map_render_controller import MapRenderController
from reservoir_sr.features.simulation.presentation.controllers.playback_controller import PlaybackController
from reservoir_sr.features.simulation.presentation.controllers.runtime_controller import RuntimeController
from reservoir_sr.features.simulation.presentation.panels.data_tab_panel import DataTabPanel
from reservoir_sr.features.simulation.presentation.view_models import DataTabViewModel, PlaybackState, TabMode
from reservoir_sr.infrastructure.grpc.simulation_client import GrpcSimulationClient


class DataTabController:

    def __init__(self, context: AppContext, panel: DataTabPanel) -> None:
        self.context = context
        self.panel = panel
        self.logger = EventLogger("DataTabController", self.context.general, self.context.log_bus)

        self.tab_vm = DataTabViewModel()
        self.playback_state = PlaybackState()

        self.client = GrpcSimulationClient(self.context.general.endpoint)

        self.render_ctrl = MapRenderController(
            context=self.context,
            maps_widget=self.panel.maps_widget,
            metrics_widget=self.panel.metrics_widget,
            logger=self.logger.child("MapRenderController"),
        )

        self.runtime_ctrl = RuntimeController(
            context=self.context,
            client=self.client,
            widget=self.panel.data_sources_panel.runtime_widget,
            logger=self.logger.child("RuntimeController"),
            render_ctrl=self.render_ctrl,
            playback_state=self.playback_state,
        )

        self.generation_ctrl = GenerationController(
            client=self.client,
            context=self.context,
            widget=self.panel.data_sources_panel.dataset_generation_widget,
            logger=self.logger.child("GenerationController"),
            playback_state=self.playback_state,
        )

        self.dataset_view_ctrl = DatasetViewController(
            context=self.context,
            panel=self.panel.data_sources_panel.dataset_view_widget,
            logger=self.logger.child("DatasetViewController"),
            playback_state=self.playback_state,
            render_ctrl=self.render_ctrl,
        )

        self._mode_controllers = {
            TabMode.RUNTIME: self.runtime_ctrl,
            TabMode.GENERATION: self.generation_ctrl,
            TabMode.DATASET: self.dataset_view_ctrl,
        }

        self.playback_ctrl = PlaybackController(
            playback_state=self.playback_state,
            tab_vm=self.tab_vm,
            widget=self.panel.playback_panel,
            mode_tabs=self.panel.data_sources_panel.mode_tabs,
            mode_controllers=self._mode_controllers,
            logger=self.logger.child("PlaybackController"),
        )

        self._is_module_active: bool = False
        self._bind_models()
        self._bind_subscriptions()
        self.on_nav_changed("current_module", self.context.nav.current_module)
        self._on_tab_changed("active_tab", self.tab_vm.active_tab)

    @property
    def widget(self) -> DataTabPanel:
        return self.panel

    def _bind_models(self) -> None:
        DATA_TAB_BINDINGS = [
            ("active_tab", "mode_tabs", "index"),
        ]
        DATA_SETTINGS_BINDINGS = [
            ("simulation_config_path", "config_panel.path_edit", "text"),
        ]
        autobind(self.tab_vm, self.panel.data_sources_panel, DATA_TAB_BINDINGS)
        autobind(self.context.data, self.panel, DATA_SETTINGS_BINDINGS)

    def _bind_subscriptions(self) -> None:
        self.context.nav.subscribe(self.on_nav_changed)
        self.tab_vm.subscribe(self._on_tab_changed)
        self.panel.config_panel.load_button.clicked.connect(self._on_load_config)
        self.panel.config_panel.save_button.clicked.connect(self._on_save_config)

    def _on_tab_changed(self, name: str, value: object) -> None:
        if name != "active_tab":
            return
        for mode, ctrl in self._mode_controllers.items():
            if mode == value:
                ctrl.enter()
            else:
                ctrl.exit()

    def on_nav_changed(self, name: str, value: object) -> None:
        if name == "current_module":
            if value == AppModuleTab.DATA:
                self.enter()
            else:
                self.exit()

    def enter(self) -> None:
        self._is_module_active = True
        self.context.nav.status_text = "Data module active"

    def exit(self) -> None:
        self._is_module_active = False

    # ------------------------------------------------------------------
    # Config persistence
    # ------------------------------------------------------------------

    def _on_load_config(self) -> None:
        path = Path(self.panel.config_panel.path_edit.text().strip())
        if not path.is_file():
            self.logger.error("Config file not found", path=str(path))
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        if self.tab_vm.active_tab == TabMode.RUNTIME:
            self.runtime_ctrl.load_config(data.get("runtime", {}))
        elif self.tab_vm.active_tab == TabMode.GENERATION:
            self.generation_ctrl.load_config(data.get("dataset", {}))
        self.logger.info("Config loaded", path=str(path), tab=self.tab_vm.active_tab.name)

    def _on_save_config(self) -> None:
        path = Path(self.panel.config_panel.path_edit.text().strip())
        data: dict[str, Any] = {}
        if self.tab_vm.active_tab == TabMode.RUNTIME:
            data["runtime"] = self.runtime_ctrl.save_config()
        elif self.tab_vm.active_tab == TabMode.GENERATION:
            data["dataset"] = self.generation_ctrl.save_config()
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        self.logger.info("Config saved", path=str(path), tab=self.tab_vm.active_tab.name)

    # ------------------------------------------------------------------
    # ModuleProtocol
    # ------------------------------------------------------------------

    def export_data(self) -> None:
        return

    def reset_module(self) -> None:
        self.playback_state.is_playing = False

    def close_resources(self) -> None:
        self.render_ctrl.engine.unload()
        self.client.close()

    def apply_project(self, project: dict[str, Any]) -> None:
        _ = project

    def collect_project(self) -> dict[str, Any]:
        return {}
