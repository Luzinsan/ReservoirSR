from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from reservoir_sr.common.observable import ObservableModel

DEFAULT_ENDPOINT = "localhost:5000"


def normalize_endpoint(value: str) -> str:
    endpoint = value.strip()
    return endpoint or DEFAULT_ENDPOINT


@dataclass
class GeneralSettings(ObservableModel):
    endpoint: str = DEFAULT_ENDPOINT
    project_directory: str = ""
    log_level: str = "debug"


@dataclass
class DataModuleSettings(ObservableModel):
    palette_name: str = "geographical"
    show_legend: bool = True
    live_render: bool = True
    isoline_layer_mode: str = "off"
    isoline_width: int = 2
    isoline_level_stride: int = 1
    simulation_config_path: str = ""



@dataclass
class InferenceModuleSettings(ObservableModel):
    device: str = "auto"
    model_dir: str = ""
    extra_model_paths: tuple[str, ...] = ()
    preferred_model: str = ""
    stats_path: str = ""
    input_dir: str = ""
    batch_size: int = 1
    cache_results: bool = True

    def available_models(self) -> list[Path]:
        models: list[Path] = []
        if self.model_dir:
            models.extend(sorted(Path(self.model_dir).rglob("*.onnx")))
        models.extend(Path(p) for p in self.extra_model_paths)
        return models

    def resolve_initial_model(self) -> Path | None:
        models = self.available_models()
        if not models:
            return None
        if self.preferred_model:
            for m in models:
                if m.name == self.preferred_model:
                    return m
        return models[0]