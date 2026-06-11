from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6 import QtCore

from reservoir_sr.app.app_context import AppContext
from reservoir_sr.common.qt_binding import autobind
from reservoir_sr.common.logging import EventLogger
from reservoir_sr.domain.simulation.value_objects import FieldSnapshot
from reservoir_sr.domain.training.normalization_stats import NormalizationStats
from reservoir_sr.features.inference.application.sr_inference_engine import SrInferenceEngine
from reservoir_sr.features.simulation.presentation.field_plot_renderer import FieldPlotRenderer
from reservoir_sr.features.simulation.presentation.panels.maps_panel import MapsPanel
from reservoir_sr.features.simulation.presentation.panels.metrics_panel import MetricsPanel
from reservoir_sr.features.simulation.presentation.view_models import RenderViewState
from reservoir_sr.ml.preprocessing.normalizer import Normalizer

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

_CHANNEL_ORDER = ("P", "ST", "SB")


class MapRenderController:
    """Рендеринг карт полей: smooth/simple интерполяция или SR-апскейл нейросетью."""

    def __init__(
        self,
        context: AppContext,
        maps_widget: MapsPanel,
        metrics_widget: MetricsPanel,
        logger: EventLogger,
    ) -> None:
        self.state = RenderViewState(render_mode="smooth")
        self.context = context
        self.display_settings = context.data
        self.inference_settings = context.inference
        self.plot_controller = FieldPlotRenderer()
        self.maps_widget = maps_widget
        self.metrics_widget = metrics_widget
        self.logger = logger

        self._snapshot: FieldSnapshot | None = None
        self.layer_lines: list[object] = []
        self.layer_labels: list[object] = []
        self.isoline_items: list[object] = []

        self.engine = SrInferenceEngine()
        self._sr_cache: dict[str, np.ndarray] | None = None
        self._normalizer: Normalizer | None = None

        self._bind_model()
        self._connect_signals()
        self._refresh_sr_models()

    # ------------------------------------------------------------------
    # Wiring
    # ------------------------------------------------------------------

    def _bind_model(self) -> None:
        autobind(self.state, self.maps_widget, RENDER_VIEW_BINDINGS)

    def _connect_signals(self) -> None:
        self.state.subscribe(self._on_state_changed)
        self.display_settings.subscribe(self._on_display_settings_changed)
        self.inference_settings.subscribe(self._on_inference_settings_changed)
        self.maps_widget.legend_label.setVisible(self.display_settings.show_legend)
        self.maps_widget.sr_model_combo.currentIndexChanged.connect(self._on_sr_model_changed)
        for label, button in self.maps_widget.field_buttons.items():
            field = self.maps_widget.field_button_map[label]
            button.clicked.connect(lambda checked=False, f=field: self._on_select_field(f))
        self._sync_field_buttons()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self, snapshot: FieldSnapshot) -> None:
        self._snapshot = snapshot
        self._sr_cache = None
        arr = next(iter(snapshot.fields.values()), None)
        if arr is not None:
            nz, nx = arr.shape
            self.state.scene_dims = (float(nx), float(nz))
        self._flush_metrics_curves()
        self._render()

    def clear(self) -> None:
        self._snapshot = None
        self._sr_cache = None
        self._clear_map()
        self._flush_metrics_curves()

    # ------------------------------------------------------------------
    # SR model discovery & loading
    # ------------------------------------------------------------------

    def _refresh_sr_models(self) -> None:
        models = self.inference_settings.available_models()
        combo = self.maps_widget.sr_model_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("— select model —", "")
        for path in models:
            combo.addItem(path.name, str(path))
        combo.blockSignals(False)
        combo.setEnabled(self.state.render_mode == "sr" and bool(models))

    def _on_sr_model_changed(self, index: int) -> None:
        data = self.maps_widget.sr_model_combo.itemData(index)
        if not data:
            self.engine.unload()
            self.state.sr_model_path = None
            return
        path = Path(data)
        if self.engine.model_path == path:
            return
        normalizer = self._ensure_normalizer()
        if normalizer is None:
            return
        try:
            self.engine.load(path, normalizer)
        except Exception as exc:
            self.logger.error("Failed to load SR model", path=str(path), detail=str(exc))
            return
        self.state.sr_model_path = path
        self._sr_cache = None
        if self.state.render_mode == "sr":
            self._render()

    def _ensure_normalizer(self) -> Normalizer | None:
        if self._normalizer is not None:
            return self._normalizer
        stats_path_str = self.inference_settings.default_stats_path.strip()
        if not stats_path_str:
            self.logger.warning("Stats file path not configured (Settings → Inference)")
            return None
        stats_path = Path(stats_path_str)
        if not stats_path.is_file():
            self.logger.warning("Stats file not found", path=str(stats_path))
            return None
        try:
            stats = NormalizationStats.from_json(stats_path)
        except Exception as exc:
            self.logger.error("Failed to read stats", path=str(stats_path), detail=str(exc))
            return None
        self._normalizer = Normalizer(stats, config={})
        return self._normalizer

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def _render(self) -> None:
        if self._snapshot is None:
            return
        arr = self._resolve_field_array()
        if arr is None:
            return

        dims = self.state.scene_dims
        rgb, _ = self.plot_controller.render_legacy_palette_map(
            arr,
            render_mode=self.state.render_mode if self.state.render_mode != "sr" else "smooth",
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
        self.maps_widget.title_label.setText(
            self.plot_controller.field_title(self.state.current_field)
        )
        self._update_legend()

    def _resolve_field_array(self) -> np.ndarray | None:
        """Возвращает массив текущего канала с учётом режима (raw / SR-upscaled)."""
        if self._snapshot is None:
            return None

        if self.state.render_mode == "sr" and self.engine.is_ready:
            sr_fields = self._compute_sr_fields()
            if sr_fields is not None:
                return sr_fields.get(self.state.current_field)

        return self._snapshot.fields.get(self.state.current_field)

    def _compute_sr_fields(self) -> dict[str, np.ndarray] | None:
        """Прогоняет полный snapshot через SR-движок один раз и кэширует результат."""
        if self._sr_cache is not None:
            return self._sr_cache
        if self._snapshot is None or not self.engine.is_ready:
            return None

        try:
            stacked = np.stack(
                [self._snapshot.fields[name] for name in _CHANNEL_ORDER]
            ).astype(np.float32)
        except KeyError as exc:
            self.logger.warning("SR render skipped: missing channel", missing=str(exc))
            return None

        sr = self.engine.upscale(stacked)
        self._sr_cache = {name: sr[i] for i, name in enumerate(_CHANNEL_ORDER)}

        nz, nx = sr.shape[1], sr.shape[2]
        self.state.scene_dims = (float(nx), float(nz))
        return self._sr_cache

    # ------------------------------------------------------------------
    # Metrics helpers
    # ------------------------------------------------------------------

    def _flush_metrics_curves(self) -> None:
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
        if name == "render_mode":
            has_models = self.maps_widget.sr_model_combo.count() > 1  # >1 because of placeholder
            self.maps_widget.sr_model_combo.setEnabled(value == "sr" and has_models)
            self._sr_cache = None
        if name in {"current_field", "render_mode"}:
            self._render()

    def _on_display_settings_changed(self, name: str, value: object) -> None:
        if name == "show_legend":
            self.maps_widget.legend_label.setVisible(bool(value))
        if name in _RENDERABLE_SETTINGS:
            self._render()

    def _on_inference_settings_changed(self, name: str, _value: object) -> None:
        if name in ("default_model_dir", "extra_model_paths"):
            self._refresh_sr_models()
        elif name == "default_stats_path":
            self._normalizer = None
            self.engine.unload()
            self.state.sr_model_path = None
            self._refresh_sr_models()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_legend(self) -> None:
        if not self.display_settings.show_legend:
            return
        self.plot_controller.update_legend(
            self.maps_widget.legend_label, palette_name=self.display_settings.palette_name
        )
