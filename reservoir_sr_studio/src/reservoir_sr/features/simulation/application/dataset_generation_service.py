from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from reservoir_sr.domain.simulation.config_models import SimulationConfig, build_simulation_config
from reservoir_sr.domain.simulation.simulation_models import DatasetJobHandle, DatasetJobState, DatasetJobStatus
from reservoir_sr.infrastructure.grpc.simulation_client import GrpcSimulationClient


@dataclass(frozen=True)
class DatasetGenerationCase:
    case_id: str
    n_dr: int
    epsp: float
    tu_seconds: float
    tk_days: float
    nzm: int


class DatasetGenerationService:
    def __init__(self, endpoint: str) -> None:
        self._endpoint = endpoint

    def submit_job(
        self,
        *,
        job_id: str,
        output_dir: Path,
        steps: int,
        config: SimulationConfig,
        snapshot_stride: int = 1,
    ) -> DatasetJobHandle:
        client = GrpcSimulationClient(self._endpoint)
        try:
            return client.run_dataset_job(
                job_id=job_id,
                output_dir=str(output_dir),
                steps=steps,
                config=config,
                snapshot_stride=snapshot_stride,
            )
        finally:
            client.close()

    def wait_for_job(self, job_id: str, poll_seconds: float = 0.5) -> DatasetJobStatus:
        client = GrpcSimulationClient(self._endpoint)
        try:
            while True:
                status = client.get_job_status(job_id)
                if status.state in {
                    DatasetJobState.COMPLETED,
                    DatasetJobState.FAILED,
                    DatasetJobState.CANCELLED,
                    DatasetJobState.NOT_FOUND,
                }:
                    return status
                time.sleep(poll_seconds)
        finally:
            client.close()

    def run_case(
        self,
        *,
        case: DatasetGenerationCase,
        base_output_dir: Path,
        nx: int,
        steps: int,
        snapshot_stride: int = 1,
        poll_seconds: float = 0.5,
        base_config: SimulationConfig | None = None,
    ) -> Path:
        config = (base_config or SimulationConfig()).with_layer_nzm(case.nzm)
        config = build_simulation_config(
            **{
                **config.__dict__,
                "nx": nx,
                "n_dr": case.n_dr,
                "epsp": case.epsp,
                "tu_seconds": case.tu_seconds,
                "tk_days": case.tk_days,
            }
        )
        base_output_dir.mkdir(parents=True, exist_ok=True)
        handle = self.submit_job(
            job_id=case.case_id,
            output_dir=base_output_dir,
            steps=steps,
            config=config,
            snapshot_stride=snapshot_stride,
        )
        if not handle.ok:
            raise RuntimeError(f"Failed to start dataset job {case.case_id}: {handle.message}")
        status = self.wait_for_job(handle.job_id, poll_seconds=poll_seconds)
        if status.state != DatasetJobState.COMPLETED:
            raise RuntimeError(f"Job {status.job_id} ended with state={status.state}: {status.message}")
        return Path(status.output_path)

    def build_batch(
        self,
        *,
        cases: list[DatasetGenerationCase],
        base_output_dir: Path,
        nx: int,
        steps: int,
        snapshot_stride: int = 1,
        workers: int = 4,
        poll_seconds: float = 0.5,
    ) -> list[Path]:
        outputs: list[Path] = []
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = [
                pool.submit(
                    self.run_case,
                    case=case,
                    base_output_dir=base_output_dir,
                    nx=nx,
                    steps=steps,
                    snapshot_stride=snapshot_stride,
                    poll_seconds=poll_seconds,
                )
                for case in cases
            ]
            for future in as_completed(futures):
                outputs.append(future.result())
        return sorted(outputs)


def build_default_cases(case_count: int, nzm: int) -> list[DatasetGenerationCase]:
    return [
        DatasetGenerationCase(
            case_id=f"case_{index:05d}",
            n_dr=10 + (index % 3),
            epsp=1e-4 * (1.0 + 0.05 * (index % 5)),
            tu_seconds=86.4,
            tk_days=0.03,
            nzm=nzm,
        )
        for index in range(case_count)
    ]
