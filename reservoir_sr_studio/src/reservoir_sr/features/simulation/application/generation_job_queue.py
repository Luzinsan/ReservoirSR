from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from reservoir_sr.common.logging import EventLogger
from reservoir_sr.domain.simulation.config_models import SimulationConfig
from reservoir_sr.domain.simulation.models import DatasetJobState
from reservoir_sr.features.simulation.application.campaign_models import CampaignCaseStream
from reservoir_sr.infrastructure.grpc.simulation_client import GrpcSimulationClient

if TYPE_CHECKING:
    from reservoir_sr.features.simulation.presentation.view_models import GenerationSessionState

_COMPLETED_STATES = frozenset({"completed", "failed", "cancelled", "not_found"})


class GenerationJobQueue:
    """Manages the full lifecycle of dataset generation jobs (single & campaign)."""

    def __init__(self, client: GrpcSimulationClient, state: GenerationSessionState, logger: EventLogger) -> None:
        self._client = client
        self._state = state
        self._logger = logger.child("GenerationJobQueue")
        self._campaign: CampaignCaseStream | None = None
        self._active: list[str] = []
        self.total_jobs: int = 0
        self.completed_jobs: int = 0
        self.failed_jobs: int = 0

    @property
    def is_active(self) -> bool:
        return bool(self._active) or (
            self._campaign is not None and not self._campaign.exhausted
        )

    # ------------------------------------------------------------------
    # Submission
    # ------------------------------------------------------------------

    def submit_single(self, config: SimulationConfig) -> str:
        """Submit a single dataset job. Returns the resolved job_id."""
        gs = self._state
        resolved = self._resolve_job_id(gs.job_id)
        self._logger.debug(
            "Submitting single job",
            job_id=resolved,
            steps=gs.steps,
            snapshot_stride=gs.snapshot_stride,
            hr_nx=gs.hr_nx,
            config=config,
        )
        response = self._client.run_dataset_job(
            job_id=resolved,
            output_dir=gs.output_dir,
            steps=gs.steps,
            config=config,
            snapshot_stride=gs.snapshot_stride,
            hr_nx=gs.hr_nx,
        )
        self._reset(total=1)
        if not response.ok:
            self.failed_jobs = 1
            raise RuntimeError(response.message)
        self._active = [response.job_id]
        return response.job_id

    def submit_campaign(self, stream: CampaignCaseStream, worker_limit: int = 1) -> int:
        """Start a campaign. Returns the number of initially submitted jobs."""
        self._campaign = stream
        self._reset(total=stream.request.sample_count)
        self._fill_slots(worker_limit)
        if not self.is_active:
            raise RuntimeError("Unable to submit campaign jobs")
        return len(self._active)

    # ------------------------------------------------------------------
    # Tick / polling
    # ------------------------------------------------------------------

    def tick(self, worker_limit: int = 1) -> None:
        """Poll running jobs, fill free slots with pending campaign cases."""
        self._poll()
        if self._campaign and not self._campaign.exhausted:
            self._fill_slots(worker_limit)

    # ------------------------------------------------------------------
    # Pause / resume / cancel
    # ------------------------------------------------------------------

    def pause(self) -> list[str]:
        """Pause all active jobs. Returns paused job ids."""
        for jid in self._active:
            self._client.pause_job(jid)
        return list(self._active)

    def resume(self) -> list[str]:
        """Resume all paused jobs. Returns list of resumed job ids."""
        resumed: list[str] = []
        for jid in self._active:
            if self._client.get_job_status(jid).state == DatasetJobState.PAUSED:
                self._client.resume_job(jid)
                resumed.append(jid)
        return resumed

    def cancel(self) -> None:
        for jid in self._active:
            self._client.cancel_job(jid)
        self._campaign = None
        self._active = []
        self._state.progress = 0

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status_summary(self) -> str:
        pending = ", queued=pending" if self._campaign and not self._campaign.exhausted else ""
        return (
            f"jobs {self.completed_jobs}/{max(self.total_jobs, 1)} completed, "
            f"failed={self.failed_jobs}, active={len(self._active)}{pending}"
        )

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _reset(self, total: int) -> None:
        self._active = []
        self.total_jobs = total
        self.completed_jobs = 0
        self.failed_jobs = 0
        self._state.progress = 0

    def _poll(self) -> None:
        still_running: list[str] = []
        done_now = failed_now = 0
        steps_done = steps_total = 0

        for jid in self._active:
            status = self._client.get_job_status(jid)
            steps_done += max(int(status.steps_done), 0)
            steps_total += max(int(status.steps_total), 1)
            if status.state.value in _COMPLETED_STATES:
                done_now += 1
                if status.state.value != "completed":
                    failed_now += 1
                self._logger.debug(
                    "Job finished",
                    job_id=jid,
                    state=status.state.value,
                    steps_done=status.steps_done,
                    steps_total=status.steps_total,
                    output=status.output_path,
                )
            else:
                still_running.append(jid)

        self.completed_jobs += done_now
        self.failed_jobs += failed_now
        self._active = still_running
        self._state.progress = int(100 * steps_done / max(steps_total, 1))

        if done_now:
            self._logger.debug(
                "Poll summary",
                completed=self.completed_jobs,
                failed=self.failed_jobs,
                total=self.total_jobs,
                active=len(self._active),
                progress=self._state.progress,
            )

    def _fill_slots(self, worker_limit: int) -> None:
        if self._campaign is None:
            return
        req = self._campaign.request
        limit = max(1, worker_limit)
        while not self._campaign.exhausted and len(self._active) < limit:
            case = self._campaign.take()
            if case is None:
                break
            resolved = self._resolve_job_id(case.case_id)
            self._logger.debug(
                "Submitting campaign case",
                case_id=resolved,
                steps=req.steps,
                snapshot_stride=req.snapshot_stride,
                hr_nx=req.hr_nx,
                config=case.config,
            )
            response = self._client.run_dataset_job(
                job_id=resolved,
                output_dir=req.output_dir,
                steps=req.steps,
                config=case.config,
                snapshot_stride=req.snapshot_stride,
                hr_nx=req.hr_nx,
            )
            if response.ok:
                self._active.append(response.job_id)
            else:
                self._logger.warning("Campaign case submission failed", case_id=resolved, detail=response.message)
                self.failed_jobs += 1

    def _resolve_job_id(self, raw_input: str, fallback_prefix: str = "job") -> str:
        base = raw_input.strip() or f"{fallback_prefix}_{uuid.uuid4().hex[:10]}"
        candidate = base
        ordinal = 1
        while True:
            status = self._client.get_job_status(candidate)
            if status.state == DatasetJobState.NOT_FOUND:
                return candidate
            candidate = f"{base}_{ordinal}"
            ordinal += 1
