from __future__ import annotations

import numpy as np

from reservoir_sr.domain.simulation.config_models import build_simulation_config
from reservoir_sr.domain.simulation.models import DatasetJobState
from reservoir_sr.infrastructure.grpc.generated import simulation_pb2
from reservoir_sr.infrastructure.grpc.simulation_client import GrpcSimulationClient


class _DummyChannel:
    def close(self) -> None:
        return None


class _FakeStub:
    instance = None

    def __init__(self, channel) -> None:
        self.channel = channel
        self.initialize_request = None
        self.fields_request = None
        self.job_request = None
        _FakeStub.instance = self

    def InitializeSimulation(self, request):
        self.initialize_request = request
        return simulation_pb2.InitializeSimulationResponse(
            simulation_id=request.simulation_id,
            ok=True,
            message="initialized",
            nx=request.config.nx,
            nz=sum(layer.nzm for layer in request.config.layers),
        )

    def StepSimulation(self, request):
        return simulation_pb2.StepSimulationResponse(ok=True, message="", steps_performed=request.step_count, time=1.5)

    def GetFields(self, request):
        self.fields_request = request
        return simulation_pb2.GetFieldsResponse(
            ok=True,
            message="",
            nx=3,
            nz=2,
            data=[
                simulation_pb2.FieldData(name="ST", values=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0]),
            ],
        )

    def RunDatasetJob(self, request):
        self.job_request = request
        return simulation_pb2.RunDatasetJobResponse(ok=True, message="queued", job_id=request.job_id)

    def GetJobStatus(self, request):
        return simulation_pb2.GetJobStatusResponse(
            job_id=request.job_id,
            state="completed",
            message="done",
            steps_done=8,
            steps_total=8,
            output_path="tmp/out",
        )

    def CancelJob(self, request):
        return simulation_pb2.CancelJobResponse(ok=True, message=f"cancelled {request.job_id}")


def _client() -> GrpcSimulationClient:
    return GrpcSimulationClient(
        endpoint="unused:0",
        channel_factory=lambda _: _DummyChannel(),
        stub_class=_FakeStub,
    )


def test_simulation_client_maps_proto_to_domain_models() -> None:
    client = _client()
    config = build_simulation_config(nx=32, n_dr=12).with_layer_nzm(2)

    init = client.initialize("sim_a", config)
    step = client.step("sim_a", step_count=3)
    fields = client.get_fields("sim_a", ("ST",))
    handle = client.run_dataset_job("job_a", "tmp/out", 8, config)
    status = client.get_job_status("job_a")
    cancelled = client.cancel_job("job_a")

    assert init.ok is True
    assert init.nx == 32
    assert init.nz == 10
    assert step.steps_performed == 3
    assert np.array_equal(fields.data["ST"].values, np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]))
    assert handle.job_id == "job_a"
    assert status.state == DatasetJobState.COMPLETED
    assert cancelled.ok is True


def test_simulation_client_sends_explicit_defaults_without_zero_fallback() -> None:
    client = _client()
    config = build_simulation_config()

    client.initialize("sim_defaults", config)

    request = _FakeStub.instance.initialize_request
    assert request.config.nx == 100
    assert request.config.n_dr == 10
    assert request.config.epsp == 1e-6
    assert request.config.tu_seconds == 86.4
    assert request.config.tk_days == 1000.3
