from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6 import QtWidgets

from reservoir_sr.app.app_context import AppContext
from reservoir_sr.common.logging import EventLogger
from reservoir_sr.common.qt_binding import autobind
from reservoir_sr.domain.simulation.archive_models import LoadedArchive
from reservoir_sr.features.simulation.application.dataset_view_service import DatasetViewService
from reservoir_sr.features.simulation.presentation.controllers.map_render_controller import MapRenderController
from reservoir_sr.features.simulation.presentation.controllers.mode_protocol import DataModeController
from reservoir_sr.features.simulation.presentation.view_models import (
    DatasetViewState,
    FieldSnapshot,
    MetricsSnapshot,
    PlaybackState,
)

DATASET_VIEW_BINDINGS = [
    ("step_index", "step_slider", "value"),
]


class DatasetViewController(DataModeController):
    """Загрузка, навигация и отображение архивов симуляции."""

    def __init__(
        self,
        service: DatasetViewService,
        widget: object,
        context: AppContext,
        logger: EventLogger,
        playback_state: PlaybackState,
        render_ctrl: MapRenderController,
    ) -> None:
        self.state = DatasetViewState()
        self._service = service
        self._panel = widget
        self.context = context
        self.logger = logger
        self.playback_state = playback_state
        self.render_ctrl = render_ctrl
        self._bind_model()
        self._connect_signals()

    def _bind_model(self) -> None:
        autobind(self.state, self._panel, DATASET_VIEW_BINDINGS)

    # ------------------------------------------------------------------
    # Wiring
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        """Подключает сигналы элементов панели просмотра датасета к обработчикам."""
        self._panel.browse_button.clicked.connect(self.browse_file)
        self._panel.browse_folder_button.clicked.connect(self.browse_folder)
        self._panel.load_button.clicked.connect(self._on_load_dataset_file)
        self._panel.load_folder_button.clicked.connect(self._on_load_dataset_folder)
        self._panel.resolution_combo.currentIndexChanged.connect(self._on_resolution_changed)
        self._panel.step_slider.valueChanged.connect(self._on_slider_changed)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def has_dataset(self) -> bool:
        """Проверяет, загружен ли в контроллер набор массивов и метаданные архива."""
        return self.state.arrays is not None and self.state.metadata is not None

    def total_steps(self) -> int:
        """Возвращает общее число шагов во временном ряду загруженного датасета."""
        if not self.has_dataset():
            return 0
        assert self.state.arrays is not None
        return int(self.state.arrays["dynamic_scalars"].shape[0])

    def dynamic_value(self, name: str, step_index: int | None = None) -> float:
        """Читает значение динамического скаляра по имени на выбранном шаге."""
        if not self.has_dataset():
            return 0.0
        assert self.state.arrays is not None
        idx = self.state.dynamic_index[name]
        pos = self.state.step_index if step_index is None else step_index
        return float(self.state.arrays["dynamic_scalars"][pos, idx])

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    def advance(self, step_count: int) -> bool:
        """Сдвигает step_index. Возвращает True если достигнут конец."""
        total = self.total_steps()
        if total == 0:
            return True
        self.state.step_index = min(self.state.step_index + step_count, total - 1)
        return self.state.step_index >= total - 1

    def prepare(self) -> None:
        """Подготовка не требуется — датасет уже загружен."""

    def step(self, step_count: int) -> bool:
        """Сдвигает шаг датасета, обновляет UI и возвращает True, если достигнут конец."""
        reached_end = self.advance(step_count)
        self.update_labels()
        snapshot = self._build_snapshot(include_metrics=True)
        if snapshot is not None:
            self.render_ctrl.refresh(snapshot)
        return reached_end

    def enter(self) -> None:
        self.playback_state.playback_ready = self.has_dataset()
        self.update_labels()
        snapshot = self._build_snapshot(include_metrics=True)
        if snapshot is not None:
            self.render_ctrl.refresh(snapshot)
        else:
            self.render_ctrl.clear()

    def reset_step(self) -> None:
        """Сбрасывает индекс шага просмотра датасета в начало временного ряда."""
        self.state.step_index = 0
        self.logger.debug("Dataset step reset")

    # ------------------------------------------------------------------
    # Field arrays
    # ------------------------------------------------------------------

    def current_field_array(self, field_name: str) -> np.ndarray:
        """Возвращает массив выбранного поля для текущего шага и разрешения (LR/HR)."""
        assert self.state.arrays is not None
        key = "lr_fields" if self._panel.resolution_combo.currentData() == "lr" else "hr_fields"
        channel_idx = {"P": 0, "ST": 1, "SB": 2}[field_name]
        return self.state.arrays[key][self.state.step_index, channel_idx].astype(np.float64, copy=False)

    def grid_dims(self) -> tuple[int, int]:
        """Возвращает размерность сетки текущего представления (LR или HR)."""
        assert self.state.arrays is not None
        key = "lr_fields" if self._panel.resolution_combo.currentData() == "lr" else "hr_fields"
        _, _, nz, nx = self.state.arrays[key].shape
        return int(nz), int(nx)

    def scene_dims(self) -> tuple[float, float]:
        """Размеры сцены; fallback на дефолт если нет метаданных."""
        if self.has_dataset():
            assert self.state.metadata is not None
            lr_grid = self.state.metadata.get("lr_grid", {})
            return float(lr_grid.get("nx", 100)), float(lr_grid.get("nz", 1))
        return 100.0, 1.0

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def _build_snapshot(self, *, include_metrics: bool = False) -> FieldSnapshot | None:
        """Формирует FieldSnapshot из загруженного архива для текущего шага."""
        if not self.has_dataset():
            return None
        fields = {name: self.current_field_array(name) for name in ("P", "ST", "SB")}
        metrics = None
        if include_metrics:
            time, ai, ait, aib = self.build_metrics_data()
            metrics = MetricsSnapshot(time=time, ai=ai, ait=ait, aib=aib)
        return FieldSnapshot(fields=fields, scene_dims=self.scene_dims(), metrics=metrics)

    def build_metrics_data(self) -> tuple[list[float], list[float], list[float], list[float]]:
        if not self.has_dataset():
            return [], [], [], []
        total = self.state.step_index + 1
        time = [self.dynamic_value("time", i) for i in range(total)]
        ai = [self.dynamic_value("AI", i) for i in range(total)]
        ait = [self.dynamic_value("AIT", i) for i in range(total)]
        aib = [self.dynamic_value("AIB", i) for i in range(total)]
        return time, ai, ait, aib

    def build_status_text(self) -> str:
        if not self.has_dataset():
            return "Simulation archive not loaded"
        return (
            f"dataset step={self.state.step_index + 1}/{self.total_steps()}  "
            f"t={self.dynamic_value('time'):.3f}  "
            f"Q={self.dynamic_value('Q_fld'):.6f}  "
            f"Pz={self.dynamic_value('P_zab'):.6f}  "
            f"H2O={self.dynamic_value('AI') * 100.0:.3f}%"
        )

    # ------------------------------------------------------------------
    # Labels
    # ------------------------------------------------------------------

    def update_labels(self) -> None:
        panel = self._panel
        if not self.has_dataset():
            panel.loaded_label.setText("Simulation archive not loaded")
            panel.info_label.setText("Нет загруженного архива или папки")
            panel.step_label.setText("Step: 0/0")
            return

        assert self.state.arrays is not None
        assert self.state.metadata is not None
        total_steps = self.total_steps()
        lr_shape = tuple(self.state.arrays["lr_fields"].shape)
        hr_shape = tuple(self.state.arrays["hr_fields"].shape)
        channels = ", ".join(self.state.metadata.get("channels", []))
        archive_count = len(self.state.metadata.get("source_archives", []))
        source = "LR" if panel.resolution_combo.currentData() == "lr" else "HR"
        panel.loaded_label.setText(
            f"{self.state.archive_path.name if self.state.archive_path else ''} | "
            f"LR {lr_shape[2]}x{lr_shape[3]} | HR {hr_shape[2]}x{hr_shape[3]} | "
            f"steps={total_steps}"
        )
        panel.info_label.setText(
            f"Источник: {source}\n"
            f"Архивов в источнике: {archive_count if archive_count > 0 else 1}\n"
            f"Каналы: {channels}\n"
            f"LR tensor: {lr_shape}\n"
            f"HR tensor: {hr_shape}\n"
            f"Dynamic scalars: {tuple(self.state.arrays['dynamic_scalars'].shape)}\n"
            f"Static scalars: {tuple(self.state.arrays['static_scalars'].shape)}\n"
            f"Layer scalars: {tuple(self.state.arrays['layer_scalars'].shape)}"
        )
        current = 0 if total_steps == 0 else self.state.step_index + 1
        panel.step_label.setText(f"Step: {current}/{total_steps}")
        panel.step_slider.blockSignals(True)
        panel.step_slider.setRange(0, max(total_steps - 1, 0))
        panel.step_slider.setValue(self.state.step_index)
        panel.step_slider.blockSignals(False)

    def clear_state(self) -> None:
        """Полностью очищает состояние загруженного архива и связанные UI-метки."""
        self.state.archive_path = None
        self.state.arrays = None
        self.state.metadata = None
        self.state.step_index = 0
        self.state.dynamic_index.clear()
        self.update_labels()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_file(self, path: Path) -> LoadedArchive:
        """Загружает архив симуляции из файла и возвращает распакованные структуры."""
        if not path.exists():
            raise FileNotFoundError(f"Simulation archive not found: {path}")
        self.logger.info("Load dataset archive", path=str(path))
        return self._service.load_archive(path)

    def load_folder(self, folder: Path, max_archives: int) -> LoadedArchive:
        """Загружает объединенный архив из директории с ограничением количества файлов."""
        if not folder.exists() or not folder.is_dir():
            raise FileNotFoundError(f"Archive folder not found: {folder}")
        self.logger.info("Load dataset archive folder", folder=str(folder), max_archives=max_archives)
        return self._service.load_archive_folder(folder, max_archives=max_archives)

    def activate_archive(self, source_path: Path, archive: LoadedArchive) -> None:
        """Переключает контроллер на новый архив и инициализирует индекс скаляров."""
        self.state.arrays = archive.arrays
        self.state.metadata = archive.metadata
        self.state.archive_path = source_path
        self.state.dynamic_index = {
            name: idx for idx, name in enumerate(archive.metadata.get("dynamic_scalar_names", []))
        }
        self.state.step_index = 0
        
        self.playback_state.playback_ready = True
        self.logger.info("Dataset archive activated", source=str(source_path))

    def _on_load_dataset_file(self) -> None:
        """UI-обработчик загрузки датасета из выбранного файла."""
        path = Path(self._panel.archive_path_edit.text().strip())
        self.logger.action("Load dataset file requested", path=str(path))
        self.playback_state.is_playing = False
        archive = self.load_file(path)
        self._activate_archive(path, archive)

    def _on_load_dataset_folder(self) -> None:
        """UI-обработчик загрузки набора архивов из выбранной папки."""
        folder = Path(self._panel.folder_path_edit.text().strip())
        self.logger.action("Load dataset folder requested", folder=str(folder))
        self.playback_state.is_playing = False
        archive = self.load_folder(
            folder,
            max_archives=int(self._panel.folder_limit_spin.value()),
        )
        self._activate_archive(folder, archive)

    def _activate_archive(self, source_path: Path, archive: LoadedArchive) -> None:
        """Выполняет активацию архива и синхронизацию зависимых UI-частей."""
        self.logger.info("Activate dataset archive", source=str(source_path))
        self.activate_archive(source_path, archive)
        self.update_labels()
        snapshot = self._build_snapshot(include_metrics=True)
        if snapshot is not None:
            self.render_ctrl.refresh(snapshot)

    def _on_resolution_changed(self, _: int) -> None:
        """Обрабатывает переключение LR/HR и инициирует пересчет отображения."""
        if not self.has_dataset():
            return
        self.logger.action("Dataset resolution changed")
        self.update_labels()
        snapshot = self._build_snapshot(include_metrics=True)
        if snapshot is not None:
            self.render_ctrl.refresh(snapshot)

    def _on_slider_changed(self, value: int) -> None:
        """Обрабатывает ручное перемещение слайдера шага во времени."""
        if not self.has_dataset():
            return
        self.logger.debug("Dataset slider changed", step_index=value)
        self.update_labels()
        snapshot = self._build_snapshot(include_metrics=True)
        if snapshot is not None:
            self.render_ctrl.refresh(snapshot)

    # ------------------------------------------------------------------
    # Browse dialogs
    # ------------------------------------------------------------------

    def browse_file(self) -> None:
        """Открывает диалог выбора файла архива и записывает путь в поле панели."""
        self.logger.action("Browse dataset archive requested")
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self._parent,
            "Select simulation archive",
            str(Path.cwd()),
            "Simulation archive (*.npz *.sr *.zip)",
        )
        if file_path:
            self._panel.archive_path_edit.setText(file_path)

    def browse_folder(self) -> None:
        """Открывает диалог выбора папки архивов и записывает путь в поле панели."""
        self.logger.action("Browse dataset folder requested")
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(
            self._parent,
            "Select archive folder",
            self._panel.folder_path_edit.text() or str(Path.cwd()),
        )
        if folder_path:
            self._panel.folder_path_edit.setText(folder_path)
