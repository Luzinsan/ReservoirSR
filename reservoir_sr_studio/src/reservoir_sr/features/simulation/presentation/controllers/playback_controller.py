from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from reservoir_sr.common.logging import EventLogger
from reservoir_sr.common.qt_binding import autobind
from reservoir_sr.features.simulation.presentation.controllers.mode_protocol import DataModeController
from reservoir_sr.features.simulation.presentation.panels.playback_panel import PlaybackPanel
from reservoir_sr.features.simulation.presentation.view_models import (
    DataTabViewModel,
    PlaybackState,
    TabMode,
)

PLAYBACK_BINDINGS = [
    ("step_batch", "batch_spin", "value"),
    ("interval_ms", "interval_spin", "value"),
]


class PlaybackController:
    """Оркестратор воспроизведения: таймер, кнопки Start/Pause/Step, блокировка табов."""

    def __init__(
        self,
        playback_state: PlaybackState,
        tab_vm: DataTabViewModel,
        widget: PlaybackPanel,
        mode_tabs: QtWidgets.QTabWidget,
        mode_controllers: dict[TabMode, DataModeController],
        logger: EventLogger,
    ) -> None:
        self.playback_state = playback_state
        self.tab_vm = tab_vm
        self.widget = widget
        self.mode_tabs = mode_tabs
        self.mode_controllers = mode_controllers
        self.logger = logger

        self._timer = QtCore.QTimer()
        self._timer.setSingleShot(False)

        self._bind_model()
        self._bind_subscriptions()
        self._connect_signals()

    def _bind_model(self) -> None:
        autobind(self.playback_state, self.widget, PLAYBACK_BINDINGS)

    def _bind_subscriptions(self) -> None:
        self.playback_state.subscribe(self.on_playback_changed)
        self.tab_vm.subscribe(self._on_tab_changed)

    def _connect_signals(self) -> None:
        self.widget.start_button.clicked.connect(self._on_start)
        self.widget.pause_button.clicked.connect(self._on_pause)
        self.widget.step_button.clicked.connect(self._on_step)
        self._timer.timeout.connect(self._on_tick)

    # ------------------------------------------------------------------
    # Обработчики кнопок
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        controller = self.active_controller
        try:
            controller.prepare()
        except Exception as exc:
            import traceback
            self.logger.error("Prepare failed, playback not started", detail=str(exc), tb=traceback.format_exc())
            return
        self.playback_state.is_playing = True

    def _on_pause(self) -> None:
        controller = self.active_controller
        try:
            controller.pause()
        except Exception as exc:
            import traceback
            self.logger.error("Pause failed", detail=str(exc), tb=traceback.format_exc())
        self.playback_state.is_playing = False

    def _on_step(self) -> None:
        if self.playback_state.is_playing:
            return
        controller = self.active_controller
        try:
            controller.prepare()
            controller.step(self.playback_state.step_batch)
        except Exception as exc:
            import traceback
            self.logger.error("Single step failed", detail=str(exc), tb=traceback.format_exc())

    def _on_cancel(self) -> None:
        controller = self.active_controller
        try:
            controller.cancel()
        except Exception as exc:
            import traceback
            self.logger.error("Cancel failed", detail=str(exc), tb=traceback.format_exc())

    # ------------------------------------------------------------------
    # Таймер
    # ------------------------------------------------------------------

    def _on_tick(self) -> None:
        controller = self.active_controller
        if controller is None:
            self.playback_state.is_playing = False
            return
        try:
            reached_end = controller.step(self.playback_state.step_batch)
            if reached_end:
                self.playback_state.is_playing = False
        except Exception as exc:
            import traceback
            self.logger.error("Playback tick failed", detail=str(exc), tb=traceback.format_exc())
            self.playback_state.is_playing = False

    # ------------------------------------------------------------------
    # Реакция на модель
    # ------------------------------------------------------------------

    def _on_tab_changed(self, name: str, _value: object) -> None:
        if name != "active_tab":
            return
        self._apply_step_button()

    def _apply_step_button(self) -> None:
        btn = self.widget.step_button
        btn.clicked.disconnect()

        if self.tab_vm.active_tab == TabMode.GENERATION:
            btn.setText("Cancel")
            btn.clicked.connect(self._on_cancel)
        else:
            btn.setText("Step")
            btn.clicked.connect(self._on_step)

    def on_playback_changed(self, name: str, value: object) -> None:
        if name == "is_playing":
            playing = bool(value)
            self.widget.start_button.setEnabled(not playing)
            self.widget.pause_button.setEnabled(playing)
            if playing:
                self._timer.start(self.playback_state.interval_ms)
                self.mode_tabs.tabBar().setEnabled(False)
            else:
                self._timer.stop()
                self.mode_tabs.tabBar().setEnabled(True)
        elif name == "interval_ms":
            if self._timer.isActive():
                self._timer.setInterval(int(value))
        elif name == "playback_ready":
            ready = bool(value)
            self.widget.start_button.setEnabled(ready)
            self.widget.pause_button.setEnabled(ready)
            self.widget.step_button.setEnabled(ready)

    @property
    def active_controller(self) -> DataModeController | None:
        return self.mode_controllers.get(self.tab_vm.active_tab)
