from __future__ import annotations

import uuid
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from reservoir_sr.app.app_context import AppContext
from reservoir_sr.common.logging import EventLogger
from reservoir_sr.common.qt_binding import autobind
from reservoir_sr.domain.simulation.config_models import (
    SimulationConfig,
    simulation_config_from_mapping,
)
from reservoir_sr.domain.simulation.models import DatasetJobState
from reservoir_sr.features.simulation.application.campaign_models import (
    SimulationCampaignCase,
    SimulationCampaignRequest,
)
from reservoir_sr.features.simulation.application.campaign_service import (
    SimulationCampaignService,
    default_sr_parameter_ranges,
)
from reservoir_sr.features.simulation.presentation.controllers.mode_protocol import DataModeController
from reservoir_sr.features.simulation.presentation.view_models import (
    CampaignSessionState,
    DatasetJobViewState,
    GenerationSessionState,
    PlaybackState,
)
from reservoir_sr.infrastructure.grpc.simulation_client import GrpcSimulationClient

GENERATION_BINDINGS = [
    ("output_dir", "output_dir_edit", "text"),
    ("job_id", "job_id_edit", "text"),
    ("steps", "steps_spin", "value"),
    ("snapshot_stride", "snapshot_stride_spin", "value"),
]

CAMPAIGN_BINDINGS = [
    ("strategy", "strategy_combo", "data"),
    ("sample_count", "sample_count_spin", "value"),
    ("seed", "seed_spin", "value"),
    ("workers", "workers_spin", "value"),
    ("lr_nx", "lr_nx_spin", "value"),
    ("hr_nx", "hr_nx_spin", "value"),
    ("fixed_tu_seconds", "fixed_tu_spin", "value"),
    ("fixed_epsp", "fixed_epsp_spin", "value"),
]

JOB_STATE_BINDINGS = [
    ("progress", "progress_bar", "value"),
]

_GENERATION_POLLING_INTERVAL_MS = 1000
_COMPLETED_STATES = frozenset({"completed", "failed", "cancelled", "not_found"})


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
        # Зависимости
        self.client = client
        self._panel = widget
        self.context = context
        self.logger = logger
        self.playback_state = playback_state

        # Модели состояния
        self.generation_state = GenerationSessionState()
        self.campaign_state = CampaignSessionState()
        self.job_state = DatasetJobViewState()
        self.source_config = SimulationConfig()

        # Внутреннее состояние
        self.needs_submit: bool = True
        self._saved_interval_ms: int | None = None

        # Внутреннее состояние (campaign)
        self.campaign_service = SimulationCampaignService()
        self._campaign_pending_cases: list[SimulationCampaignCase] = []
        self._campaign_worker_limit: int = 1
        self._campaign_output_dir: str = ""
        self._campaign_steps: int = 0

        # Binding & subscriptions
        self._bind_model()
        self._bind_subscriptions()

    def _bind_model(self) -> None:
        autobind(self.generation_state, self._panel, GENERATION_BINDINGS)
        autobind(self.campaign_state, self._panel, CAMPAIGN_BINDINGS)
        autobind(self.job_state, self._panel, JOB_STATE_BINDINGS)

    def _bind_subscriptions(self) -> None:
        mark_dirty = lambda _n, _v: setattr(self, "needs_submit", True)
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
        if self.job_state.active_job_ids and not self.needs_submit:
            first_id = self.job_state.active_job_ids[0]
            status = self.client.get_job_status(first_id)
            if status.state == DatasetJobState.PAUSED:
                self.client.resume_job(first_id)
                self.logger.info("Generation resumed", job_id=first_id)
                return
            if status.state == DatasetJobState.RUNNING:
                return

        if self.job_state.active_job_ids:
            self.cancel()

        config = self.build_config()
        mode = self._panel.mode_combo.currentData()
        self.logger.info("Start dataset generation", mode=mode)
        if mode == "campaign":
            self._start_campaign(config)
        else:
            self._start_single(config)
        self.job_state.progress = 0
        self.needs_submit = False

    def step(self, step_count: int) -> bool:
        _ = step_count
        if not self.job_state.active_job_ids and not self._campaign_pending_cases:
            return True

        self._poll_job_statuses()

        if self._campaign_pending_cases:
            self._submit_campaign_jobs_until_limit()

        self._update_status_text()
        return not self.job_state.active_job_ids and not self._campaign_pending_cases

    def pause(self) -> None:
        for job_id in self.job_state.active_job_ids:
            self.client.pause_job(job_id)
        self.logger.info("Generation paused", job_ids=self.job_state.active_job_ids)

    def cancel(self) -> None:
        for job_id in self.job_state.active_job_ids:
            self.client.cancel_job(job_id)
        self.logger.info("Generation cancelled", job_ids=self.job_state.active_job_ids)
        self._campaign_pending_cases = []
        self.job_state.active_job_ids = []
        self.job_state.progress = 0
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
    # Polling helpers
    # ------------------------------------------------------------------

    def _poll_job_statuses(self) -> None:
        still_running: list[str] = []
        done_now = failed_now = 0
        steps_done = steps_total = 0

        for job_id in self.job_state.active_job_ids:
            status = self.client.get_job_status(job_id)
            steps_done += max(int(status.steps_done), 0)
            steps_total += max(int(status.steps_total), 1)
            if status.state.value in _COMPLETED_STATES:
                done_now += 1
                if status.state.value != "completed":
                    failed_now += 1
            else:
                still_running.append(job_id)

        self.job_state.completed_jobs += done_now
        self.job_state.failed_jobs += failed_now
        self.job_state.active_job_ids = still_running
        self.job_state.progress = int(100 * steps_done / max(steps_total, 1))

    def _update_status_text(self) -> None:
        js = self.job_state
        self.context.nav.status_text = (
            f"jobs {js.completed_jobs}/{max(js.total_jobs, 1)} completed, "
            f"failed={js.failed_jobs}, active={len(js.active_job_ids)}, "
            f"queued={len(self._campaign_pending_cases)}"
        )

    # ------------------------------------------------------------------
    # Single job
    # ------------------------------------------------------------------

    def _resolve_job_id(self, prefix: str) -> str:
        """Return a unique job_id: use *prefix* as-is if free, otherwise append ``_N``."""
        base = prefix or f"job_{uuid.uuid4().hex[:10]}"
        candidate = base
        ordinal = 1
        while True:
            status = self.client.get_job_status(candidate)
            if status.state == DatasetJobState.NOT_FOUND:
                return candidate
            candidate = f"{base}_{ordinal}"
            ordinal += 1

    def _start_single(self, config: SimulationConfig) -> None:
        s = self.generation_state
        out_dir = Path(s.output_dir.strip() or "dataset_out")
        job_id = self._resolve_job_id(s.job_id.strip())
        self.logger.debug(
            "Sending single dataset job parameters",
            job_id=job_id,
            output_dir=out_dir,
            steps=s.steps,
            snapshot_stride=s.snapshot_stride,
            config=config,
        )
        response = self.client.run_dataset_job(
            job_id=job_id,
            output_dir=str(out_dir),
            steps=s.steps,
            config=config,
            snapshot_stride=s.snapshot_stride,
        )
        self.job_state.total_jobs = 1
        self.job_state.completed_jobs = 0

        if not response.ok:
            self.job_state.failed_jobs = 1
            self.context.nav.status_text = f"Submission failed: {response.message}"
            self.logger.error("Single dataset job submission failed", detail=response.message)
            raise RuntimeError(response.message)

        self.job_state.failed_jobs = 0
        self.job_state.active_job_ids = [response.job_id]
        self.generation_state.job_id = response.job_id
        self.logger.info("Single dataset job submitted", job_id=response.job_id, output_dir=str(out_dir))

    # ------------------------------------------------------------------
    # Campaign
    # ------------------------------------------------------------------

    def _start_campaign(self, config: SimulationConfig) -> None:
        gs = self.generation_state
        cs = self.campaign_state
        out_dir = Path(gs.output_dir.strip() or "dataset_out")
        out_dir.mkdir(parents=True, exist_ok=True)
        campaign_id = self._resolve_job_id(gs.job_id.strip() or f"campaign_{uuid.uuid4().hex[:10]}")

        request = SimulationCampaignRequest(
            campaign_id=campaign_id,
            sample_count=cs.sample_count,
            steps=gs.steps,
            lr_nx=cs.lr_nx,
            hr_nx=cs.hr_nx,
            fixed_tu_seconds=cs.fixed_tu_seconds,
            fixed_epsp=cs.fixed_epsp,
            seed=cs.seed,
            base_config=replace(config, nx=cs.lr_nx),
            ranges=default_sr_parameter_ranges(),
        )
        strategy_id = cs.strategy or "lhs"
        self.logger.debug(
            "Prepared campaign generation request",
            request=request,
            strategy_id=strategy_id,
        )
        plan = self.campaign_service.build_plan(request, strategy_id=strategy_id)
        if not plan.cases:
            rejected_text = plan.rejected[0].reason if plan.rejected else "all cases rejected"
            self.logger.error("Campaign produced no valid cases", reason=rejected_text)
            raise RuntimeError(f"Campaign produced no valid cases: {rejected_text}")

        self._campaign_pending_cases = list(plan.cases)
        self._campaign_worker_limit = max(1, cs.workers)
        self._campaign_output_dir = str(out_dir)
        self._campaign_steps = gs.steps
        self.job_state.active_job_ids = []
        self.job_state.total_jobs = len(plan.cases)
        self.job_state.completed_jobs = 0
        self.job_state.failed_jobs = 0
        self._submit_campaign_jobs_until_limit()
        if not self.job_state.active_job_ids and not self._campaign_pending_cases:
            raise RuntimeError("Unable to submit campaign jobs")
        self.generation_state.job_id = campaign_id
        self.context.nav.status_text = (
            f"submitted {len(self.job_state.active_job_ids)} jobs, "
            f"queued={len(self._campaign_pending_cases)}, rejected={len(plan.rejected)}"
        )
        self.logger.info(
            "Campaign dataset jobs submitted",
            submitted=len(self.job_state.active_job_ids),
            queued=len(self._campaign_pending_cases),
            rejected=len(plan.rejected),
        )

    def _submit_campaign_jobs_until_limit(self) -> None:
        while self._campaign_pending_cases and len(self.job_state.active_job_ids) < self._campaign_worker_limit:
            case = self._campaign_pending_cases.pop(0)
            resolved_id = self._resolve_job_id(case.case_id)
            self.logger.debug(
                "Sending campaign dataset job parameters",
                job_id=resolved_id,
                output_dir=self._campaign_output_dir,
                steps=self._campaign_steps,
                snapshot_stride=self.generation_state.snapshot_stride,
                config=case.config,
            )
            response = self.client.run_dataset_job(
                job_id=resolved_id,
                output_dir=self._campaign_output_dir,
                steps=self._campaign_steps,
                config=case.config,
                snapshot_stride=self.generation_state.snapshot_stride,
            )
            if response.ok:
                self.job_state.active_job_ids.append(response.job_id)
            else:
                self.job_state.completed_jobs += 1
                self.job_state.failed_jobs += 1
