from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import IntEnum
from pathlib import Path

from omegaconf import DictConfig, OmegaConf

from reservoir_sr.app.settings_models import (
    DataModuleSettings,
    GeneralSettings,
    InferenceModuleSettings,
)
from reservoir_sr.common.logging import LogBus
from reservoir_sr.common.observable import ObservableModel


class AppModuleTab(IntEnum):
    DATA = 0
    EVALUATION = 1


@dataclass
class AppNavState(ObservableModel):
    current_module: AppModuleTab = AppModuleTab.DATA
    status_text: str = ""


@dataclass
class AppContext:
    nav: AppNavState = field(default_factory=AppNavState)
    general: GeneralSettings = field(default_factory=GeneralSettings)
    data: DataModuleSettings = field(default_factory=DataModuleSettings)
    inference: InferenceModuleSettings = field(default_factory=InferenceModuleSettings)
    log_bus: LogBus = field(default_factory=LogBus)

    @classmethod
    def from_hydra(cls, cfg: DictConfig) -> "AppContext":
        return cls(
            general=GeneralSettings.from_mapping(OmegaConf.to_container(cfg.general, resolve=True)),
            data=DataModuleSettings.from_mapping(OmegaConf.to_container(cfg.data, resolve=True)),
            inference=InferenceModuleSettings.from_mapping(OmegaConf.to_container(cfg.inference, resolve=True)),
        )

    def save_to_yaml(self, conf_dir: Path) -> None:
        """Сохраняет настройки обратно в gui/general.yaml, data.yaml и т.д.
        Каждый раздел — в свой файл, чтобы git-diff был локальным.
        """
        sections = {
            "general": self.general,
            "data": self.data,
            "inference": self.inference,
        }
        for name, model in sections.items():
            path = conf_dir / f"{name}.yaml"
            payload = OmegaConf.create({name: model.to_mapping()})
            content = f"# @package {name}\n" + OmegaConf.to_yaml(getattr(payload, name))
            path.write_text(content, encoding="utf-8")

    def snapshot(self) -> "AppContext":
        return AppContext(
            nav=AppNavState(**asdict(self.nav)),
            general=GeneralSettings(**asdict(self.general)),
            data=DataModuleSettings(**asdict(self.data)),
            inference=InferenceModuleSettings(**asdict(self.inference)),
            log_bus=self.log_bus,
        )

    def apply_from(self, other: "AppContext") -> None:
        _copy_model(self.nav, other.nav)
        _copy_model(self.general, other.general)
        _copy_model(self.data, other.data)
        _copy_model(self.inference, other.inference)


def _copy_model(target: object, source: object) -> None:
    for field_name in getattr(type(target), "__dataclass_fields__", {}):
        setattr(target, field_name, getattr(source, field_name))
