from __future__ import annotations

from dataclasses import asdict, dataclass, field
from reservoir_sr.app.settings_models import (
    DataModuleSettings,
    GeneralSettings,
    InferenceModuleSettings,
    TrainingModuleSettings,
)
from reservoir_sr.common.logging import LogBus
from enum import IntEnum
from reservoir_sr.common.observable import ObservableModel


class AppModuleTab(IntEnum):
    DATA = 0
    TRAINING = 1
    INFERENCE = 2


@dataclass
class AppNavState(ObservableModel):
    current_module: AppModuleTab = AppModuleTab.DATA
    status_text: str = ""


@dataclass
class AppContext:
    nav: AppNavState = field(default_factory=AppNavState)
    general: GeneralSettings = field(default_factory=GeneralSettings)
    data: DataModuleSettings = field(default_factory=DataModuleSettings)
    training: TrainingModuleSettings = field(default_factory=TrainingModuleSettings)
    inference: InferenceModuleSettings = field(default_factory=InferenceModuleSettings)
    log_bus: LogBus = field(default_factory=LogBus)

    def snapshot(self) -> "AppContext":
        return AppContext(
            nav=AppNavState(**asdict(self.nav)),
            general=GeneralSettings(**asdict(self.general)),
            data=DataModuleSettings(**asdict(self.data)),
            training=TrainingModuleSettings(**asdict(self.training)),
            inference=InferenceModuleSettings(**asdict(self.inference)),
            log_bus=self.log_bus,
        )

    def apply_from(self, other: "AppContext") -> None:
        _copy_model(self.nav, other.nav)
        _copy_model(self.general, other.general)
        _copy_model(self.data, other.data)
        _copy_model(self.training, other.training)
        _copy_model(self.inference, other.inference)


def _copy_model(target: object, source: object) -> None:
    for field_name in getattr(type(target), "__dataclass_fields__", {}):
        setattr(target, field_name, getattr(source, field_name))
