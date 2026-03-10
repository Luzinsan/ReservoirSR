from __future__ import annotations

from reservoir_sr.domain.simulation.config_models import SimulationConfig
from reservoir_sr.domain.simulation.models import SimulationFields, SimulationInitialization, SimulationStepResult
from reservoir_sr.infrastructure.grpc.simulation_client import GrpcSimulationClient


class RuntimeService:
    def __init__(self, client: GrpcSimulationClient) -> None:
        self._client = client

    def initialize(self, simulation_id: str, config: SimulationConfig) -> SimulationInitialization:
        return self._client.initialize(simulation_id, config)

    def step(self, simulation_id: str, step_count: int = 1) -> SimulationStepResult:
        return self._client.step(simulation_id, step_count=step_count)

    def get_fields(self, simulation_id: str, fields: tuple[str, ...] = ("P", "ST", "SB")) -> SimulationFields:
        return self._client.get_fields(simulation_id, fields)
