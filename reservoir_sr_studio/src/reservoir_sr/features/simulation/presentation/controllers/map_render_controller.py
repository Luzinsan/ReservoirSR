from __future__ import annotations

import numpy as np
from PySide6 import QtCore

from reservoir_sr.common.qt_binding import autobind
from reservoir_sr.common.logging import EventLogger
from reservoir_sr.app.settings_models import DataModuleSettings
from reservoir_sr.features.simulation.presentation.panels.maps_panel import MapsPanel
from reservoir_sr.features.simulation.presentation.panels.metrics_panel import MetricsPanel
from reservoir_sr.features.simulation.presentation.field_plot_renderer import FieldPlotRenderer
from reservoir_sr.domain.simulation.value_objects import FieldSnapshot
from reservoir_sr.features.simulation.presentation.view_models import RenderViewState

RENDER_VIEW_BINDINGS = [
    ("render_mode", "render_mode_combo", "data"),
]

_RENDERABLE_SETTINGS = frozenset({
    "palette_name",
    "show_legend",
    "isoline_layer_mode",
    "isoline_width",
    "isoline_level_stride",
})


class MapRenderController:
    """Рендеринг карт полей (P/ST/SB), изолиний, оверлеев и метрик.

    Единственный вход данных — ``refresh(snapshot)``.
    При смене визуальных настроек (поле, палитра, изолинии) перерисовка
    происходит из кешированного ``_snapshot`` без обращения к источнику.
    Метрики передаются по ссылке в ``snapshot.metrics``.
    """

    def __init__(
        self,
        settings: DataModuleSettings,
        maps_widget: MapsPanel,
        metrics_widget: MetricsPanel,
        logger: EventLogger,
    ) -> None:
        self.state = RenderViewState(render_mode="smooth")
        self.display_settings = settings
        self.plot_controller = FieldPlotRenderer()
        self.maps_widget = maps_widget
        self.metrics_widget = metrics_widget
        self.logger = logger

        self._snapshot: FieldSnapshot | None = None
        self.layer_lines: list[object] = []
        self.layer_labels: list[object] = []
        self.isoline_items: list[object] = []

        self._bind_model()
        self._connect_signals()

    def _bind_model(self) -> None:
        autobind(self.state, self.maps_widget, RENDER_VIEW_BINDINGS)

    def _connect_signals(self) -> None:
        self.state.subscribe(self._on_state_changed)
        self.display_settings.subscribe(self._on_display_settings_changed)
        self.maps_widget.legend_label.setVisible(self.display_settings.show_legend)
        for label, button in self.maps_widget.field_buttons.items():
            field = self.maps_widget.field_button_map[label]
            button.clicked.connect(lambda checked=False, f=field: self._on_select_field(f))
        self._sync_field_buttons()

    # ------------------------------------------------------------------
    # Public API — единственный вход данных
    # ------------------------------------------------------------------

    def refresh(self, snapshot: FieldSnapshot) -> None:
        """Принимает снимок полей от режима-контроллера, кеширует и отрисовывает."""
        self._snapshot = snapshot
        arr = next(iter(snapshot.fields.values()), None)
        if arr is not None:
            nz, nx = arr.shape
            self.state.scene_dims = (float(nx), float(nz))
        self._flush_metrics_curves()
        self._render()

    def clear(self) -> None:
        """Полная очистка: кеш, карта, метрики, оверлеи."""
        self._snapshot = None
        self._clear_map()
        self._flush_metrics_curves()

    # ------------------------------------------------------------------
    # Внутренняя отрисовка из кеша
    # ------------------------------------------------------------------

    def _render(self) -> None:
        """Отрисовывает текущий канал из кешированного snapshot."""
        if self._snapshot is None:
            return
        arr = self._snapshot.fields.get(self.state.current_field)
        if arr is None:
            return
        dims = self.state.scene_dims
        rgb, _ = self.plot_controller.render_legacy_palette_map(
            arr,
            render_mode=self.state.render_mode,
            palette_name=self.display_settings.palette_name,
            current_field=self.state.current_field,
        )
        if self.display_settings.isoline_layer_mode == "only":
            rgb = np.full_like(rgb, 255)
        self.maps_widget.image.setLookupTable(None)
        self.maps_widget.image.setImage(rgb, autoLevels=False)
        self.maps_widget.image.setRect(QtCore.QRectF(0, 0, dims[0], dims[1]))
        self.isoline_items = self.plot_controller.update_isolines(
            self.maps_widget.plot,
            self.isoline_items,
            arr=arr,
            mode=self.display_settings.isoline_layer_mode,
            stride=self.display_settings.isoline_level_stride,
            width=self.display_settings.isoline_width,
            palette_name=self.display_settings.palette_name,
            current_field=self.state.current_field,
            scene_dims=dims,
        )
        self.maps_widget.title_label.setText(self.plot_controller.field_title(self.state.current_field))
        self._update_legend()

    # ------------------------------------------------------------------
    # Metrics helpers
    # ------------------------------------------------------------------

    def _flush_metrics_curves(self) -> None:
        """Проталкивает метрики из snapshot в кривые виджета."""
        m = self._snapshot.metrics if self._snapshot else None
        if m is not None:
            self.metrics_widget.curve_ai.setData(m.time, m.ai)
            self.metrics_widget.curve_ait.setData(m.time, m.ait)
            self.metrics_widget.curve_aib.setData(m.time, m.aib)
        else:
            self.metrics_widget.curve_ai.setData([], [])
            self.metrics_widget.curve_ait.setData([], [])
            self.metrics_widget.curve_aib.setData([], [])

    def _clear_map(self) -> None:
        self.maps_widget.image.setImage(np.zeros((1, 1, 3), dtype=np.uint8), autoLevels=False)

    # ------------------------------------------------------------------
    # Scene layout (viewport + layer overlays)
    # ------------------------------------------------------------------

    def _update_scene_layout(self) -> None:
        """Обновляет viewport камеры и оверлеи слоёв из текущего state/snapshot."""
        boundaries = self._snapshot.layer_boundaries if self._snapshot else None
        self.layer_lines, self.layer_labels = self.plot_controller.update_scene_layout(
            self.maps_widget.plot,
            scene_dims=self.state.scene_dims,
            layer_boundaries=boundaries,
            layer_lines=self.layer_lines,
            layer_labels=self.layer_labels,
        )

    # ------------------------------------------------------------------
    # State change handlers
    # ------------------------------------------------------------------

    def _sync_field_buttons(self) -> None:
        for label, button in self.maps_widget.field_buttons.items():
            button.setChecked(self.maps_widget.field_button_map[label] == self.state.current_field)

    def _on_select_field(self, field_name: str) -> None:
        self.logger.action("Map field selected", field=field_name)
        self.state.current_field = field_name

    def _on_state_changed(self, name: str, value: object) -> None:
        if name == "current_field":
            self._sync_field_buttons()
        if name == "scene_dims":
            self._update_scene_layout()
        if name in {"current_field", "render_mode"}:
            self._render()

    def _on_display_settings_changed(self, name: str, value: object) -> None:
        if name == "show_legend":
            self.maps_widget.legend_label.setVisible(bool(value))
        if name in _RENDERABLE_SETTINGS:
            self._render()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_legend(self) -> None:
        if not self.display_settings.show_legend:
            return
        self.plot_controller.update_legend(self.maps_widget.legend_label, palette_name=self.display_settings.palette_name)
