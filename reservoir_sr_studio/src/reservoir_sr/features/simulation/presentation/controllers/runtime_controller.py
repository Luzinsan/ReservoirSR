from __future__ import annotations

from dataclasses import asdict
from typing import Any

import numpy as np

from reservoir_sr.app.app_context import AppContext
from reservoir_sr.common.logging import EventLogger
from reservoir_sr.common.qt_binding import autobind
from reservoir_sr.domain.simulation.config_models import (
    SimulationConfig,
    simulation_config_from_mapping,
)
from reservoir_sr.domain.simulation.models import SimulationStepResult
from reservoir_sr.features.simulation.application.runtime_service import RuntimeService
from reservoir_sr.features.simulation.presentation.controllers.map_render_controller import MapRenderController
from reservoir_sr.features.simulation.presentation.controllers.mode_protocol import DataModeController
from reservoir_sr.features.simulation.presentation.view_models import (
    FieldSnapshot,
    MetricsSnapshot,
    PlaybackState,
    RuntimeSessionState,
    RuntimeTrackingState,
)

RUNTIME_SESSION_BINDINGS = [
    ("nx", "nx_spin", "value"),
    ("nz", "nz_spin", "value"),
    ("q_zab", "q_zab_spin", "value"),
    ("obv_p", "obv_p_spin", "value"),
    ("r_skv", "r_skv_spin", "value"),
    ("mu_pazp", "mu_pazp_spin", "value"),
]


class RuntimeController(DataModeController):
    """Управление runtime-симуляцией: инициализация, шаги, получение полей."""

    _INIT_FIELDS = frozenset({"nx", "q_zab", "obv_p", "r_skv", "mu_pazp"})

    def __init__(
        self,
        service: RuntimeService,
        widget: object,
        logger: EventLogger,
        render_ctrl: MapRenderController,
        context: AppContext,
        playback_state: PlaybackState,
    ) -> None:
        # Зависимости
        self.service = service
        self.logger = logger
        self.render_ctrl = render_ctrl
        self.context = context
        self._widget = widget

        # Модели состояния
        self.playback_state = playback_state
        self.state = RuntimeSessionState()
        self.tracking = RuntimeTrackingState()
        self.source_config = SimulationConfig()

        # Внутреннее состояние
        self._metrics = MetricsSnapshot()
        self._last_snapshot: FieldSnapshot | None = None
        self.needs_init: bool = True

        # Binding & subscriptions
        self._bind_model()
        self._bind_subscriptions()

    def _bind_model(self) -> None:
        autobind(self.state, self._widget, RUNTIME_SESSION_BINDINGS)

    def _bind_subscriptions(self) -> None:
        self.state.subscribe(self._on_session_state_changed)

    def _on_session_state_changed(self, name: str, value: object) -> None:
        if name in self._INIT_FIELDS:
            self.needs_init = True

    def reset(self) -> None:
        """Сбрасывает source_config и state к дефолтам."""
        self.source_config = SimulationConfig()
        defaults = RuntimeSessionState()
        for name in type(self.state).__dataclass_fields__:
            setattr(self.state, name, getattr(defaults, name))
        self.needs_init = True
        self._metrics.clear()
        self._last_snapshot = None
        self.logger.action("Runtime reset to defaults")
        self.clear_tracking()

    # ------------------------------------------------------------------
    # Config persistence
    # ------------------------------------------------------------------

    def save_config(self) -> dict[str, Any]:
        """Сериализует runtime-конфигурацию (source_config + overrides)."""
        return asdict(self.build_config())

    def load_config(self, data: dict[str, Any]) -> None:
        """Восстанавливает source_config из JSON и синхронизирует UI-поля."""
        config_fields = set(SimulationConfig.__dataclass_fields__)
        config_data = {k: v for k, v in data.items() if k in config_fields}
        self.source_config = simulation_config_from_mapping(config_data)
        for field in self._INIT_FIELDS:
            if field in config_data:
                setattr(self.state, field, config_data[field])
        self.needs_init = True
        self.logger.debug("Runtime config loaded", config=self.source_config)

    def build_config(self) -> SimulationConfig:
        cfg = self.state.build_config(self.source_config)
        self.logger.debug("Runtime configuration prepared", config=cfg)
        return cfg

    # ------------------------------------------------------------------
    # Simulation lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        assert self.service is not None
        cfg = self.build_config()
        self.logger.info("Initialize runtime simulation")
        response = self.service.initialize("", cfg)
        if not response.ok:
            self.logger.error("Runtime initialization failed", detail=response.message)
            raise RuntimeError(response.message)
        self.state.simulation_id = response.simulation_id
        self.state.nx = response.nx
        self.state.nz = response.nz
        self.needs_init = False
        self.logger.info(
            "Runtime initialized",
            simulation_id=response.simulation_id,
            nx=response.nx,
            nz=response.nz,
        )

    def prepare(self) -> None:
        """Подготавливает runtime-сессию перед началом воспроизведения."""
        if self.needs_init:
            self.initialize()

    def advance(self, step_count: int) -> SimulationStepResult:
        """Запрашивает у сервера продвижение симуляции на указанное число шагов."""
        assert self.service is not None
        step = self.service.step(self.state.simulation_id, step_count=step_count)
        if not step.ok:
            self.logger.error("Runtime step failed", detail=step.message)
            raise RuntimeError(step.message)
        return step

    def advance_step(self, step_count: int) -> tuple[SimulationStepResult, float, float]:
        """Выполняет шаг симуляции и возвращает (step, dq, dpz)."""
        step = self.advance(step_count)
        dq = 0.0 if self.tracking.prev_q is None else float(step.q_fld - self.tracking.prev_q)
        dpz = 0.0 if self.tracking.prev_pz is None else float(step.p_zab - self.tracking.prev_pz)
        self.tracking.prev_q = float(step.q_fld)
        self.tracking.prev_pz = float(step.p_zab)
        return step, dq, dpz

    def clear_tracking(self) -> None:
        """Очищает историю значений для расчета приращений между шагами."""
        self.tracking.prev_q = None
        self.tracking.prev_pz = None
        self.logger.debug("Runtime tracking cleared")

    # ------------------------------------------------------------------
    # Snapshot helpers
    # ------------------------------------------------------------------

    def layer_boundaries(self) -> np.ndarray:
        """Кумулятивные границы слоёв (по nzm) для оверлея на карте."""
        nzm = np.array([layer.nzm for layer in self.source_config.layers], dtype=np.float64)
        return np.cumsum(nzm[:-1])

    def _build_snapshot(self) -> FieldSnapshot:
        """Запрашивает все 3 канала у сервера и формирует FieldSnapshot с метриками (ссылка)."""
        sim_fields = self.service.get_fields(self.state.simulation_id)
        return FieldSnapshot(
            fields={fg.name: fg.values for fg in sim_fields.data.values()},
            scene_dims=(float(self.state.nx), float(self.state.nz)),
            metrics=self._metrics,
            layer_boundaries=self.layer_boundaries(),
        )

    # ------------------------------------------------------------------
    # Playback protocol (DataModeController)
    # ------------------------------------------------------------------

    def step(self, step_count: int) -> bool:
        """Выполняет шаг симуляции, обновляет UI и возвращает False (runtime бесконечен)."""
        result, dq, dpz = self.advance_step(step_count=step_count)
        self._metrics.append(result.time, result.ai, result.ait, result.aib)

        if self.context.data.live_render:
            snapshot = self._build_snapshot()
            self._last_snapshot = snapshot
            self.render_ctrl.refresh(snapshot)
        self.context.nav.status_text = (
            f"t={result.time:.3f}  Q={result.q_fld:.6f} (dQ={dq:+.3e})  "
            f"Pz={result.p_zab:.6f} (dPz={dpz:+.3e})  "
            f"H2O={result.ai * 100.0:.3f}%"
        )
        return False

    def enter(self) -> None:
        self.playback_state.playback_ready = True
        if self._last_snapshot is not None:
            self.render_ctrl.refresh(self._last_snapshot)

    def exit(self) -> None:
        self.render_ctrl.clear()
