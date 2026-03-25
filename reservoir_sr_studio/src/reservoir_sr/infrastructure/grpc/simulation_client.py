from __future__ import annotations

from dataclasses import asdict
from typing import Iterable, Protocol

import grpc
import numpy as np

from reservoir_sr.domain.simulation.config_models import ReservoirLayerConfig, SimulationConfig
from reservoir_sr.domain.simulation.models import (
    DatasetJobCancellation,
    DatasetJobHandle,
    DatasetJobPause,
    DatasetJobResume,
    DatasetJobState,
    DatasetJobStatus,
    FieldGrid,
    SimulationFields,
    SimulationInitialization,
    SimulationStepResult,
)


class SimulationStubProtocol(Protocol):
    def InitializeSimulation(self, request: object) -> object: ...

    def StepSimulation(self, request: object) -> object: ...

    def GetFields(self, request: object) -> object: ...

    def RunDatasetJob(self, request: object) -> object: ...

    def GetJobStatus(self, request: object) -> object: ...

    def CancelJob(self, request: object) -> object: ...

    def PauseJob(self, request: object) -> object: ...

    def ResumeJob(self, request: object) -> object: ...


class SimulationServiceError(RuntimeError):
    pass


def _generated_modules() -> tuple[object, object]:
    from reservoir_sr.infrastructure.grpc.generated import simulation_pb2, simulation_pb2_grpc

    return simulation_pb2, simulation_pb2_grpc


def _to_proto_layer(simulation_pb2: object, layer: ReservoirLayerConfig) -> object:
    return simulation_pb2.LayerConfig(**asdict(layer))


def _to_proto_config(simulation_pb2: object, config: SimulationConfig) -> object:
    payload = asdict(config)
    payload["layers"] = [_to_proto_layer(simulation_pb2, layer) for layer in config.layers]
    return simulation_pb2.SimulationConfig(**payload)


class GrpcSimulationClient:
    def __init__(
        self,
        endpoint: str,
        *,
        channel_factory=grpc.insecure_channel,
        stub_class: type[SimulationStubProtocol] | None = None,
    ) -> None:
        simulation_pb2, simulation_pb2_grpc = _generated_modules()
        self._simulation_pb2 = simulation_pb2
        self.endpoint = endpoint
        self._channel = channel_factory(endpoint)
        resolved_stub_class = stub_class or simulation_pb2_grpc.SimulationServiceStub
        self._stub = resolved_stub_class(self._channel)

    def initialize(self, simulation_id: str, config: SimulationConfig) -> SimulationInitialization:
        request = self._simulation_pb2.InitializeSimulationRequest(
            simulation_id=simulation_id,
            config=_to_proto_config(self._simulation_pb2, config),
        )
        response = self._stub.InitializeSimulation(request)
        return SimulationInitialization(
            simulation_id=response.simulation_id,
            ok=response.ok,
            message=response.message,
            nx=response.nx,
            nz=response.nz,
        )

    def step(self, simulation_id: str, step_count: int = 1) -> SimulationStepResult:
        response = self._stub.StepSimulation(
            self._simulation_pb2.StepSimulationRequest(simulation_id=simulation_id, step_count=step_count)
        )
        return SimulationStepResult(
            ok=response.ok,
            message=response.message,
            steps_performed=response.steps_performed,
            time=response.time,
            ai=response.ai,
            ait=response.ait,
            aib=response.aib,
            p_zab=response.p_zab,
            q_fld=response.q_fld,
            diss=response.diss,
            disq=response.disq,
            tbt=response.tbt,
            tb=response.tb,
            tt=response.tt,
            q_oil_total=response.q_oil_total,
            q_oil_blocks=response.q_oil_blocks,
            q_oil_fractures=response.q_oil_fractures,
        )

    def get_fields(self, simulation_id: str, fields: Iterable[str]) -> SimulationFields:
        response = self._stub.GetFields(
            self._simulation_pb2.GetFieldsRequest(simulation_id=simulation_id, fields=list(fields))
        )
        if not response.ok:
            raise SimulationServiceError(response.message)

        data = {
            entry.name: FieldGrid(
                name=entry.name,
                values=np.asarray(entry.values, dtype=np.float64).reshape(response.nz, response.nx),
            )
            for entry in response.data
        }
        return SimulationFields(nx=response.nx, nz=response.nz, data=data)

    def run_dataset_job(
        self,
        job_id: str,
        output_dir: str,
        steps: int,
        config: SimulationConfig,
        snapshot_stride: int = 1,
    ) -> DatasetJobHandle:
        response = self._stub.RunDatasetJob(
            self._simulation_pb2.RunDatasetJobRequest(
                job_id=job_id,
                output_dir=output_dir,
                steps=steps,
                config=_to_proto_config(self._simulation_pb2, config),
                snapshot_stride=snapshot_stride,
            )
        )
        return DatasetJobHandle(ok=response.ok, message=response.message, job_id=response.job_id)

    def get_job_status(self, job_id: str) -> DatasetJobStatus:
        response = self._stub.GetJobStatus(self._simulation_pb2.GetJobStatusRequest(job_id=job_id))
        return DatasetJobStatus(
            job_id=response.job_id,
            state=DatasetJobState(response.state),
            message=response.message,
            steps_done=response.steps_done,
            steps_total=response.steps_total,
            output_path=response.output_path,
        )

    def cancel_job(self, job_id: str) -> DatasetJobCancellation:
        response = self._stub.CancelJob(self._simulation_pb2.CancelJobRequest(job_id=job_id))
        return DatasetJobCancellation(ok=response.ok, message=response.message)

    def pause_job(self, job_id: str) -> DatasetJobPause:
        response = self._stub.PauseJob(self._simulation_pb2.PauseJobRequest(job_id=job_id))
        return DatasetJobPause(ok=response.ok, message=response.message)

    def resume_job(self, job_id: str) -> DatasetJobResume:
        response = self._stub.ResumeJob(self._simulation_pb2.ResumeJobRequest(job_id=job_id))
        return DatasetJobResume(ok=response.ok, message=response.message)

    def close(self) -> None:
        self._channel.close()
