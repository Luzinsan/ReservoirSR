from __future__ import annotations

import uuid
from dataclasses import replace
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from reservoir_sr.app.app_context import AppContext
from reservoir_sr.common.logging import EventLogger
from reservoir_sr.common.qt_binding import autobind
from reservoir_sr.domain.simulation.config_models import SimulationConfig
from reservoir_sr.features.simulation.application.campaign_models import SimulationCampaignRequest
from reservoir_sr.features.simulation.application.campaign_service import (
    SimulationCampaignService,
    default_sr_parameter_ranges,
)
from reservoir_sr.features.simulation.presentation.controllers.map_render_controller import MapRenderController
from reservoir_sr.features.simulation.presentation.view_models import (
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
    ("mode", "mode_combo", "data"),
    ("strategy", "strategy_combo", "data"),
    ("sample_count", "sample_count_spin", "value"),
    ("seed", "seed_spin", "value"),
    ("workers", "workers_spin", "value"),
    ("lr_nx", "lr_nx_spin", "value"),
    ("hr_nx", "hr_nx_spin", "value"),
    ("fixed_tu_seconds", "fixed_tu_spin", "value"),
    ("fixed_epsp", "fixed_epsp_spin", "value"),
]


class GenerationController:
    """Запуск и мониторинг задач генерации датасетов (single / campaign)."""

    def __init__(
        self,
        widget: object,
        context: AppContext,
        logger: EventLogger,
        playback_state: PlaybackState,
        render_ctrl: MapRenderController,
    ) -> None:
        self.generation_state = GenerationSessionState()
        self.job_state = DatasetJobViewState()
        self._panel = widget
        self._timer = QtCore.QTimer()
        self.context = context
        self.logger = logger
        self.playback_state = playback_state
        self.render_ctrl = render_ctrl
        self.client: GrpcSimulationClient | None = None
        self.campaign_service = SimulationCampaignService()
        self._campaign_pending_cases: list[object] = []
        self._campaign_worker_limit: int = 1
        self._campaign_output_dir: str = ""
        self._campaign_steps: int = 0
        self._timer.timeout.connect(self._poll_status)
        self._bind_model()
        self._connect_signals()
        self._apply_initial_state()

    def _bind_model(self) -> None:
        """Привязывает поля панели генерации к `GenerationSessionState` через autobind."""
        autobind(self.generation_state, self._panel, GENERATION_BINDINGS)

    def _connect_signals(self) -> None:
        """Подключает действия UI панели генерации к обработчикам контроллера."""
        self._panel.browse_button.clicked.connect(self.browse_output_dir)
        self._panel.start_button.clicked.connect(self._on_start_requested)
        self._panel.cancel_button.clicked.connect(self.cancel)
        self.generation_state.subscribe(self._on_state_changed)

    def _apply_initial_state(self) -> None:
        """Применяет начальные ограничения UI в зависимости от режима генерации."""
        self._on_state_changed("mode", self.generation_state.mode)

    # ------------------------------------------------------------------
    # Start
    # ------------------------------------------------------------------

    def start_generation(self, config: SimulationConfig) -> None:
        assert self.client is not None
        self._campaign_pending_cases = []
        self._campaign_worker_limit = 1
        self._campaign_output_dir = ""
        self._campaign_steps = 0
        mode = self.generation_state.mode
        self.logger.debug("Dataset generation configuration prepared", mode=mode, config=config)
        self.logger.info("Start dataset generation", mode=mode)
        if mode == "campaign":
            self._start_campaign(config)
        else:
            self._start_single(config)
        self._panel.progress_bar.setValue(0)
        self._panel.status_label.setText("running...")
        self._timer.start(1000)

    def cancel(self) -> None:
        """Отправляет запросы отмены активных задач и останавливает polling-таймер."""
        assert self.client is not None
        self.logger.info("Cancel dataset generation requested")
        job_ids = [jid for jid in self.job_state.active_job_ids if jid]
        if not job_ids and self.job_state.active_job_id:
            job_ids = [self.job_state.active_job_id]
        self._campaign_pending_cases = []
        if not job_ids:
            self._panel.status_label.setText("cancel requested")
            return
        for job_id in job_ids:
            self.client.cancel_job(job_id)
        self.job_state.active_job_ids = []
        self.job_state.active_job_id = None
        self._timer.stop()
        self._panel.status_label.setText("cancel requested")

    def browse_output_dir(self) -> None:
        """Открывает диалог выбора выходной директории для генерации датасета."""
        self.logger.action("Browse generation output directory requested")
        # path = QtWidgets.QFileDialog.getExistingDirectory(
        #     self._parent,
        #     "Select simulation output directory",
        #     self.generation_state.output_dir,
        # )
        # if path:
        #     self.generation_state.output_dir = path

    def _on_start_requested(self) -> None:
        """UI-обработчик кнопки запуска генерации."""
        self.logger.action("Generation start requested")
        self._ensure_client_connected()
        self.start_generation(self._build_runtime_config())

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    def _poll_status(self) -> None:
        """Опрашивает статусы активных job и обновляет агрегированный прогресс UI."""
        assert self.client is not None
        active_job_ids = [jid for jid in self.job_state.active_job_ids if jid]
        if not active_job_ids:
            if self.job_state.active_job_id:
                active_job_ids = [self.job_state.active_job_id]
            elif not self._campaign_pending_cases:
                self._timer.stop()
                return

        completed_states = {"completed", "failed", "cancelled", "not_found"}
        still_running: list[str] = []
        done_now = 0
        failed_now = 0
        total_steps_done = 0
        total_steps_all = 0
        first_message = ""
        for job_id in active_job_ids:
            status = self.client.get_job_status(job_id)
            total_steps_done += max(int(status.steps_done), 0)
            total_steps_all += max(int(status.steps_total), 1)
            if not first_message:
                first_message = str(status.message)
            state_name = str(status.state.value)
            if state_name in completed_states:
                done_now += 1
                if state_name != "completed":
                    failed_now += 1
            else:
                still_running.append(job_id)

        self.job_state.completed_jobs += done_now
        self.job_state.failed_jobs += failed_now
        self.job_state.active_job_ids = still_running
        self.job_state.active_job_id = still_running[0] if still_running else None
        progress = int(100 * total_steps_done / max(total_steps_all, 1))
        self._panel.progress_bar.setValue(progress)
        if self._campaign_pending_cases:
            self._submit_campaign_jobs_until_limit()
        active_total = len(self.job_state.active_job_ids)
        queued_total = len(self._campaign_pending_cases)
        total_jobs = max(self.job_state.total_jobs, 1)
        self._panel.status_label.setText(
            f"jobs {self.job_state.completed_jobs}/{total_jobs} completed, "
            f"failed={self.job_state.failed_jobs}, active={active_total}, queued={queued_total} ({first_message})"
        )
        if not self.job_state.active_job_ids and not self._campaign_pending_cases:
            self._timer.stop()

    # ------------------------------------------------------------------
    # Single job
    # ------------------------------------------------------------------

    def _start_single(self, config: SimulationConfig) -> None:
        """Создает и отправляет одиночную задачу генерации датасета на сервер."""
        assert self.client is not None
        s = self.generation_state
        out_dir = Path(s.output_dir.strip() or "dataset_out")
        job_id = s.job_id.strip() or f"job_{uuid.uuid4().hex[:10]}"
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
        if not response.ok:
            self.logger.error("Single dataset job submission failed", message=response.message)
            raise RuntimeError(response.message)
        self.job_state.active_job_id = response.job_id
        self.job_state.active_job_ids = [response.job_id]
        self.job_state.total_jobs = 1
        self.job_state.completed_jobs = 0
        self.job_state.failed_jobs = 0
        self.generation_state.job_id = response.job_id
        self.logger.info("Single dataset job submitted", job_id=response.job_id, output_dir=str(out_dir))

    # ------------------------------------------------------------------
    # Campaign
    # ------------------------------------------------------------------

    def _start_campaign(self, config: SimulationConfig) -> None:
        """Строит campaign-план и отправляет первую пачку задач с учетом лимита workers."""
        assert self.client is not None
        s = self.generation_state
        out_dir = Path(s.output_dir.strip() or "dataset_out")
        out_dir.mkdir(parents=True, exist_ok=True)
        campaign_id = s.job_id.strip() or f"campaign_{uuid.uuid4().hex[:10]}"
        request = SimulationCampaignRequest(
            campaign_id=campaign_id,
            sample_count=s.sample_count,
            steps=s.steps,
            lr_nx=s.lr_nx,
            hr_nx=s.hr_nx,
            fixed_tu_seconds=s.fixed_tu_seconds,
            fixed_epsp=s.fixed_epsp,
            seed=s.seed,
            base_config=replace(config, nx=s.lr_nx),
            ranges=default_sr_parameter_ranges(),
        )
        strategy_id = s.strategy or "lhs"
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
        self._campaign_worker_limit = max(1, s.workers)
        self._campaign_output_dir = str(out_dir)
        self._campaign_steps = s.steps
        self.job_state.active_job_ids = []
        self.job_state.active_job_id = None
        self.job_state.total_jobs = len(plan.cases)
        self.job_state.completed_jobs = 0
        self.job_state.failed_jobs = 0
        self._submit_campaign_jobs_until_limit()
        if not self.job_state.active_job_ids and not self._campaign_pending_cases:
            raise RuntimeError("Unable to submit campaign jobs")
        self.generation_state.job_id = campaign_id
        self._panel.status_label.setText(
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
        """Догружает campaign-задачи в очередь исполнения пока есть свободные воркеры."""
        assert self.client is not None
        while self._campaign_pending_cases and len(self.job_state.active_job_ids) < self._campaign_worker_limit:
            case = self._campaign_pending_cases.pop(0)
            self.logger.debug(
                "Sending campaign dataset job parameters",
                job_id=case.case_id,
                output_dir=self._campaign_output_dir,
                steps=self._campaign_steps,
                snapshot_stride=self.generation_state.snapshot_stride,
                config=case.config,
            )
            response = self.client.run_dataset_job(
                job_id=case.case_id,
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
        self.job_state.active_job_id = (
            self.job_state.active_job_ids[0] if self.job_state.active_job_ids else None
        )

    # ------------------------------------------------------------------
    # Model listener
    # ------------------------------------------------------------------

    def _on_state_changed(self, name: str, value: object) -> None:
        """Реагирует на изменения state-режима и включает/отключает campaign-поля."""
        if name == "mode":
            is_campaign = value == "campaign"
            self._panel.strategy_combo.setEnabled(is_campaign)
            self._panel.sample_count_spin.setEnabled(is_campaign)
            self._panel.seed_spin.setEnabled(is_campaign)
            self._panel.workers_spin.setEnabled(is_campaign)
            self._panel.lr_nx_spin.setEnabled(is_campaign)
            self._panel.hr_nx_spin.setEnabled(is_campaign)
            self._panel.fixed_tu_spin.setEnabled(is_campaign)
            self._panel.fixed_epsp_spin.setEnabled(is_campaign)
            self.logger.debug("Generation mode changed", campaign=is_campaign)

    def prepare(self) -> None:
        """Подготовка не требуется — генерация не участвует в playback."""

    def step(self, step_count: int) -> bool:
        """Generation не поддерживает playback — всегда сигнализирует конец."""
        _ = step_count
        return True

    def enter(self) -> None:
        self.playback_state.playback_ready = False
        self.render_ctrl.clear()

    def exit(self) -> None:
        pass
