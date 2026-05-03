from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from reservoir_sr.app.app_context import AppContext
from reservoir_sr.common.logging import EventLogger
from reservoir_sr.common.qt_binding import autobind
from reservoir_sr.domain.simulation.config_models import (
    SimulationConfig,
    simulation_config_from_mapping,
)
from reservoir_sr.features.simulation.application.campaign_models import (
    CampaignCaseStream,
    SimulationCampaignRequest,
)
from reservoir_sr.features.simulation.application.campaign_service import SimulationCampaignService
from reservoir_sr.features.simulation.application.generation_job_queue import GenerationJobQueue
from reservoir_sr.features.simulation.presentation.controllers.mode_protocol import DataModeController
from reservoir_sr.features.simulation.presentation.view_models import (
    CampaignSessionState,
    GenerationSessionState,
    PlaybackState,
)
from reservoir_sr.infrastructure.grpc.simulation_client import GrpcSimulationClient

GENERATION_BINDINGS = [
    ("output_dir", "output_dir_edit", "text"),
    ("job_id", "job_id_edit", "text"),
    ("steps", "steps_spin", "value"),
    ("snapshot_stride", "snapshot_stride_spin", "value"),
    ("lr_nx", "lr_nx_spin", "value"),
    ("hr_nx", "hr_nx_spin", "value"),
    ("fixed_tu_seconds", "fixed_tu_spin", "value"),
    ("fixed_epsp", "fixed_epsp_spin", "value"),
    ("progress", "progress_bar", "value"),
]

CAMPAIGN_BINDINGS = [
    ("strategy", "strategy_combo", "data"),
    ("sample_count", "sample_count_spin", "value"),
    ("seed", "seed_spin", "value"),
    ("workers", "workers_spin", "value"),
]

_GENERATION_POLLING_INTERVAL_MS = 1000


class GenerationController(DataModeController):
    """Запуск и мониторинг задач генерации датасетов (single / campaign)."""

    def __init__(
        self,
        client: GrpcSimulationClient,
        widget: object,
        context: AppContext,
        logger: EventLogger,
        playback_state: PlaybackState,
    ) -> None:
        self._panel = widget
        self.context = context
        self.logger = logger
        self.playback_state = playback_state

        # Модели состояния
        self.generation_state = GenerationSessionState()
        self.campaign_state = CampaignSessionState()
        self.source_config = SimulationConfig()

        # Внутреннее состояние
        self.needs_submit: bool = True
        self._saved_interval_ms: int | None = None

        # Application services
        self.campaign_service = SimulationCampaignService()
        self._queue = GenerationJobQueue(client, self.generation_state, logger)

        # Binding & subscriptions
        self._bind_model()
        self._bind_subscriptions()

    def _bind_model(self) -> None:
        autobind(self.generation_state, self._panel, GENERATION_BINDINGS)
        autobind(self.campaign_state, self._panel, CAMPAIGN_BINDINGS)

    def _bind_subscriptions(self) -> None:
        mark_dirty = lambda name, _v: setattr(self, "needs_submit", True) if name != "progress" else None
        self.generation_state.subscribe(mark_dirty)
        self.campaign_state.subscribe(mark_dirty)

    # ------------------------------------------------------------------
    # Config persistence
    # ------------------------------------------------------------------

    def save_config(self) -> dict[str, Any]:
        return asdict(self.build_config())

    def load_config(self, data: dict[str, Any]) -> None:
        config_fields = set(SimulationConfig.__dataclass_fields__)
        config_data = {k: v for k, v in data.items() if k in config_fields}
        self.source_config = simulation_config_from_mapping(config_data)
        self.needs_submit = True
        self.logger.debug("Generation config loaded", config=self.source_config)

    def build_config(self) -> SimulationConfig:
        cfg = self.source_config
        self.logger.debug("Generation configuration prepared", config=cfg)
        return cfg

    # ------------------------------------------------------------------
    # DataModeController
    # ------------------------------------------------------------------

    def prepare(self) -> None:
        if self._queue.is_active and not self.needs_submit:
            resumed = self._queue.resume()
            if resumed:
                self.logger.info("Generation resumed", job_ids=resumed)
            return

        if self._queue.is_active:
            self.cancel()

        config = self.build_config()
        mode = self._panel.mode_combo.currentData()
        self.logger.info("Start dataset generation", mode=mode)
        if mode == "campaign":
            self._start_campaign(config)
        else:
            self._start_single(config)
        self.needs_submit = False

    def step(self, step_count: int) -> bool:
        _ = step_count
        if not self._queue.is_active:
            return True
        self._queue.tick(worker_limit=self.campaign_state.workers)
        self.context.nav.status_text = self._queue.status_summary()
        return not self._queue.is_active

    def pause(self) -> None:
        job_ids = self._queue.pause()
        self.logger.info("Generation paused", job_ids=job_ids)

    def cancel(self) -> None:
        self._queue.cancel()
        self.logger.info("Generation cancelled")
        self.playback_state.is_playing = False
        self.context.nav.status_text = "Generation cancelled"

    def enter(self) -> None:
        self.playback_state.playback_ready = True
        self._saved_interval_ms = self.playback_state.interval_ms
        self.playback_state.interval_ms = _GENERATION_POLLING_INTERVAL_MS

    def exit(self) -> None:
        if self._saved_interval_ms is not None:
            self.playback_state.interval_ms = self._saved_interval_ms
            self._saved_interval_ms = None

    # ------------------------------------------------------------------
    # Single job
    # ------------------------------------------------------------------

    def _start_single(self, config: SimulationConfig) -> None:
        try:
            job_id = self._queue.submit_single(config)
        except RuntimeError as exc:
            self.context.nav.status_text = f"Submission failed: {exc}"
            self.logger.error("Single dataset job submission failed", detail=str(exc))
            raise
        self.logger.info("Single dataset job submitted", job_id=job_id, output_dir=self.generation_state.output_dir)

    # ------------------------------------------------------------------
    # Campaign
    # ------------------------------------------------------------------

    def _start_campaign(self, config: SimulationConfig) -> None:
        gs = self.generation_state
        Path(gs.output_dir).mkdir(parents=True, exist_ok=True)

        request = SimulationCampaignRequest.build(
            generation=gs,
            campaign=self.campaign_state,
            base_config=config,
            ranges=self.campaign_service.default_ranges(),
        )
        stream = CampaignCaseStream(request, self.campaign_service.generate_cases(request))
        submitted = self._queue.submit_campaign(stream, worker_limit=self.campaign_state.workers)
        self.context.nav.status_text = f"Campaign started: {submitted} jobs submitted"
        self.logger.info("Campaign dataset jobs submitted", submitted=submitted)
