from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path

from reservoir_sr.common.observable import ObservableModel
from reservoir_sr.domain.simulation.config_models import SimulationConfig


class TabMode(IntEnum):
    RUNTIME = 0
    GENERATION = 1
    DATASET = 2


@dataclass
class DataTabViewModel(ObservableModel):
    """Общее состояние модуля симуляции (Shared State)."""
    active_tab: TabMode = TabMode.RUNTIME

@dataclass
class RuntimeSessionState(ObservableModel):
    """UI-слой параметров текущей runtime-сессии симуляции.

    Промысловые параметры (оборудование, режим скважины),
    расчётная сетка и клиентские настройки. Свойства пласта
    и флюида живут в ``SimulationConfig`` и загружаются из JSON.

    Attributes:
        simulation_id: Идентификатор сессии на gRPC-сервере.
        nx: Разрешение сетки по горизонтали (направление r).
            После инициализации перезаписывается сервером.
        nz: Разрешение сетки по вертикали (направление z).
            Вычисляется сервером как ``sum(nzm)`` всех слоёв.
        q_zab: Дебит скважины (м³/сут). Граничное условие
            на стенке скважины в уравнении давления.
        obv_p: Давление на контуре питания (атм). Энергия
            вытеснения нефти водой.
        r_skv: Радиус скважины (м). Призабойное сопротивление
            потоку. Типичные значения: 0.05-0.35 м.
        mu_pazp: Эффективная вязкость нефти в призабойной
            зоне (мПа*с). При ``|v| >= x_a`` вязкость в
            реологической модели равна ``mu_pazp``.
    """

    simulation_id: str = ""
    nx: int = 100
    nz: int = 1
    q_zab: float = 50.0
    obv_p: float = 180.0
    r_skv: float = 0.1
    mu_pazp: float = 8.0

    def build_config(self, base: SimulationConfig) -> SimulationConfig:
        """Применяет промысловые переопределения к базовой конфигурации."""
        from dataclasses import replace

        return replace(
            base,
            nx=self.nx,
            q_zab=self.q_zab,
            obv_p=self.obv_p,
            r_skv=self.r_skv,
            mu_pazp=self.mu_pazp,
        )


@dataclass
class GenerationSessionState(ObservableModel):
    """Общие UI-параметры генерации датасетов (single и campaign)."""

    output_dir: str = field(default_factory=lambda: str(Path.cwd() / "dataset_out"))
    job_id: str = ""
    steps: int = 500
    snapshot_stride: int = 1
    lr_nx: int = 100
    hr_nx: int = 400
    fixed_tu_seconds: float = 86.4
    fixed_epsp: float = 1e-6
    progress: int = 0


@dataclass
class CampaignSessionState(ObservableModel):
    """UI-параметры, специфичные для campaign-режима генерации."""

    strategy: str = "lhs"
    sample_count: int = 32
    seed: int = 1234
    workers: int = 4


@dataclass
class DatasetViewState(ObservableModel):
    """Состояние загруженного архива симуляции для просмотра."""

    archive_path: Path | None = None
    step_index: int = 0
    resolution: str = "lr"


@dataclass
class RenderViewState(ObservableModel):
    """Настройки визуализации карты полей."""

    current_field: str = "ST"
    render_mode: str = "smooth"
    scene_dims: tuple[float, float] = (1.0, 1.0)


@dataclass
class PlaybackState(ObservableModel):
    is_playing: bool = False
    step_batch: int = 10
    interval_ms: int = 100
    playback_ready: bool = False


@dataclass
class RuntimeTrackingState(ObservableModel):
    """Предыдущие значения величин для вычисления приращений."""

    prev_q: float | None = None
    prev_pz: float | None = None
