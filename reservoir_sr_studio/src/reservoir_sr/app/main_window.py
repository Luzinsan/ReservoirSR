from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from reservoir_sr.app.app_context import AppContext, AppModuleTab
from reservoir_sr.app.module_protocol import ModuleProtocol
from reservoir_sr.app.settings_dialog import SettingsDialog
from reservoir_sr.common.logging import EventLogger, LogPanel
from reservoir_sr.features.evaluation.presentation.evaluation_module import EvaluationModule
from reservoir_sr.features.simulation.presentation.controllers.data_tab_controller import DataTabController
from reservoir_sr.features.simulation.presentation.panels.data_tab_panel import DataTabPanel


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, context: AppContext, window_cfg: DictConfig) -> None:
        super().__init__()
        self.setWindowTitle(window_cfg.title)
        self.context = context
        self.resize(window_cfg.width, window_cfg.height)

        self._modules: list[ModuleProtocol] = []

        self._build_toolbar()
        self._build_log_panel()
        self.logger = EventLogger("MainWindow", self.context.general, self.context.log_bus)
        self._build_modules()
        self._build_status_bar()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_toolbar(self) -> None:
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)

        self.act_open_project = QtGui.QAction("Open Project", self)
        self.act_save_project = QtGui.QAction("Save Project", self)
        self.act_settings = QtGui.QAction("Settings", self)
        self.act_export = QtGui.QAction("Export", self)
        self.act_reset = QtGui.QAction("Reset", self)
        self.act_toggle_log = QtGui.QAction("Log", self)
        self.act_toggle_log.setCheckable(True)

        toolbar.addAction(self.act_open_project)
        toolbar.addAction(self.act_save_project)
        toolbar.addSeparator()
        toolbar.addAction(self.act_settings)
        toolbar.addSeparator()
        toolbar.addAction(self.act_export)
        toolbar.addAction(self.act_reset)
        toolbar.addSeparator()
        toolbar.addAction(self.act_toggle_log)

    def _build_modules(self) -> None:
        self.module_tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.module_tabs)

        self.data_tab_panel = DataTabPanel()
        self.data_tab_controller = DataTabController(context=self.context, panel=self.data_tab_panel)
        self._add_module(self.data_tab_controller, "Data")

        self._add_module(EvaluationModule(context=self.context), "Evaluation")

    def _add_module(self, module: ModuleProtocol, label: str) -> None:
        self._modules.append(module)
        self.module_tabs.addTab(module.widget, label)

    def _build_log_panel(self) -> None:
        self.log_dock = QtWidgets.QDockWidget("Log", self)
        self.log_dock.setAllowedAreas(
            QtCore.Qt.DockWidgetArea.BottomDockWidgetArea
            | QtCore.Qt.DockWidgetArea.TopDockWidgetArea
        )
        self.log_output = LogPanel()
        self.log_dock.setWidget(self.log_output)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.log_dock)
        self.log_dock.hide()

    def _build_status_bar(self) -> None:
        self.status_label = QtWidgets.QLabel("Ready")
        self.server_indicator = QtWidgets.QLabel(f"Server: {self.context.general.endpoint}")
        self.statusBar().addWidget(self.status_label, 1)
        self.statusBar().addPermanentWidget(self.server_indicator)

    def _connect_signals(self) -> None:
        self.context.nav.subscribe(self._on_nav_state_changed)
        self.context.general.subscribe(self._on_general_settings_changed)
        self.context.log_bus.message_logged.connect(self._append_log)
        self.act_open_project.triggered.connect(self._on_open_project)
        self.act_save_project.triggered.connect(self._on_save_project)
        self.act_settings.triggered.connect(self._on_settings)
        self.act_export.triggered.connect(self._on_export)
        self.act_reset.triggered.connect(self._on_reset)
        self.act_toggle_log.toggled.connect(self._on_toggle_log)
        self.module_tabs.currentChanged.connect(self._on_module_tab_changed)

    # ------------------------------------------------------------------
    # Toolbar handlers
    # ------------------------------------------------------------------

    def _on_open_project(self) -> None:
        """TODO: диалог выбора файла проекта, вызов apply_project на всех модулях."""
        self.logger.action("Open project requested")
        self.logger.warning("Open Project not implemented")

    def _on_save_project(self) -> None:
        """TODO: сбор collect_project со всех модулей, запись в JSON."""
        self.logger.action("Save project requested")
        self.logger.warning("Save Project not implemented")

    def _on_settings(self) -> None:
        self.logger.action("Settings dialog opened")
        dialog = SettingsDialog(self.context, self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.logger.info("Settings updated")
            self.statusBar().showMessage("Settings updated", 3000)
        else:
            self.logger.action("Settings dialog cancelled")

    def _on_general_settings_changed(self, name: str, value: object) -> None:
        if name == "endpoint":
            self.server_indicator.setText(f"Server: {value}")
            self.logger.info("General setting changed", name=name, value=value)

    def _on_nav_state_changed(self, name: str, value: object) -> None:
        if name == "status_text":
            self.status_label.setText(str(value))

    def _on_export(self) -> None:
        self.logger.action("Toolbar export triggered")
        self._current_module().export_data()

    def _on_reset(self) -> None:
        self.logger.action("Toolbar reset triggered")
        self._current_module().reset_module()

    def _on_toggle_log(self, visible: bool) -> None:
        self.log_dock.setVisible(visible)
        self.logger.action("Log panel toggled", visible=visible)

    def _on_module_tab_changed(self, index: int) -> None:
        self.context.nav.current_module = AppModuleTab(index)
        self.logger.info("Module tab changed", index=index)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _current_module(self) -> ModuleProtocol:
        index = self.module_tabs.currentIndex()
        return self._modules[index]

    def _append_log(self, html: str) -> None:
        self.log_output.append_html(html)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        for module in self._modules:
            module.close_resources()
        super().closeEvent(event)


