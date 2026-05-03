from __future__ import annotations

from dataclasses import dataclass

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
    vector_color_name: str = "#ff0000"


@dataclass
class TrainingModuleSettings(ObservableModel):
    default_device: str = "auto"
    default_dataset_dir: str = ""
    default_checkpoint_dir: str = ""
    default_num_workers: int = 4
    mixed_precision: bool = True


@dataclass
class InferenceModuleSettings(ObservableModel):
    default_device: str = "auto"
    default_model_dir: str = ""
    default_input_dir: str = ""
    default_output_dir: str = ""
    default_batch_size: int = 1
    cache_results: bool = True

