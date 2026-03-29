from __future__ import annotations

from pathlib import Path

from reservoir_sr.app.app_context import AppContext
from reservoir_sr.common.logging import EventLogger
from reservoir_sr.common.qt_binding import autobind
from reservoir_sr.domain.simulation.dataset_models import LoadedDataset
from reservoir_sr.domain.simulation.value_objects import FieldSnapshot, MetricsSnapshot
from reservoir_sr.features.simulation.presentation.controllers.map_render_controller import MapRenderController
from reservoir_sr.features.simulation.presentation.controllers.mode_protocol import DataModeController
from reservoir_sr.features.simulation.presentation.panels.dataset_view_panel import DatasetViewPanel
from reservoir_sr.features.simulation.presentation.view_models import (
    DatasetViewState,
    PlaybackState,
)
from reservoir_sr.infrastructure.storage.sr_archive_io import load_sr_archive

DATASET_VIEW_BINDINGS = [
    ("step_index", "step_slider", "value"),
    ("resolution", "resolution_combo", "data"),
]


class DatasetViewController(DataModeController):
    """Загрузка, навигация и отображение архивов симуляции."""

    def __init__(
        self,
        panel: DatasetViewPanel,
        context: AppContext,
        logger: EventLogger,
        playback_state: PlaybackState,
        render_ctrl: MapRenderController,
    ) -> None:
        self.state = DatasetViewState()
        self._panel = panel
        self.context = context
        self.logger = logger
        self.playback_state = playback_state
        self.render_ctrl = render_ctrl
        self._dataset: LoadedDataset | None = None

        autobind(self.state, self._panel, DATASET_VIEW_BINDINGS)
        self._connect_signals()

    # ------------------------------------------------------------------
    # Wiring
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._panel.load_button.clicked.connect(self._on_load)
        self._panel.archive_combo.currentIndexChanged.connect(self._on_archive_selected)
        self.state.subscribe(self._on_state_changed)

    def _on_state_changed(self, name: str, _value: object) -> None:
        if name in ("step_index", "resolution", "archive_path") and self.has_dataset():
            self._sync_ui()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def has_dataset(self) -> bool:
        return self._dataset is not None

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------


    def step(self, step_count: int) -> bool:
        if not self.has_dataset():
            return True
        total = self._dataset.total_steps
        self.state.step_index = min(self.state.step_index + step_count, total - 1)
        return self.state.step_index >= total - 1

    def enter(self) -> None:
        self.playback_state.playback_ready = self.has_dataset()
        if self.has_dataset():
            self._sync_ui()
        else:
            self._update_labels_empty()
            self.render_ctrl.clear()


    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def _build_snapshot(self) -> FieldSnapshot:
        ds = self._dataset
        step = self.state.step_index
        time, ai, ait, aib = ds.metrics_arrays(step)
        return FieldSnapshot(
            fields=ds.field_arrays(step, self.state.resolution),
            metrics=MetricsSnapshot(time=time, ai=ai, ait=ait, aib=aib),
        )

    def build_status_text(self) -> str:
        if not self.has_dataset():
            return "Simulation archive not loaded"
        ds = self._dataset
        step = self.state.step_index
        return (
            f"dataset step={step + 1}/{ds.total_steps}  "
            f"t={ds.dynamic_value('time', step):.3f}  "
            f"Q={ds.dynamic_value('Q_fld', step):.6f}  "
            f"Pz={ds.dynamic_value('P_zab', step):.6f}  "
            f"H2O={ds.dynamic_value('AI', step) * 100.0:.3f}%"
        )

    # ------------------------------------------------------------------
    # UI sync
    # ------------------------------------------------------------------

    def _sync_ui(self) -> None:
        self._update_labels()
        self.context.nav.status_text = self.build_status_text()
        self.render_ctrl.refresh(self._build_snapshot())

    def _update_labels(self) -> None:
        if not self.has_dataset():
            self._update_labels_empty()
            return

        ds = self._dataset
        total = ds.total_steps
        source = "LR" if self.state.resolution == "lr" else "HR"
        name = self.state.archive_path.name if self.state.archive_path else "—"
        lr, hr = ds.lr_shape, ds.hr_shape

        self._panel.update_info(
            f"{name} | LR {lr[2]}x{lr[3]} | HR {hr[2]}x{hr[3]} | steps={total}\n"
            f"Source: {source} | Archives: {ds.archive_count or 1} | Channels: {', '.join(ds.channels)}\n"
            f"LR tensor: {lr} | HR tensor: {hr}\n"
            f"Dynamic: {ds.dynamic_shape} | Static: {ds.static_shape} | Layers: {ds.layer_shape}"
        )
        current = 0 if total == 0 else self.state.step_index + 1
        self._panel.update_step(current, total, self.state.step_index)

    def _update_labels_empty(self) -> None:
        self._panel.update_info("No archive loaded")
        self._panel.update_step(0, 0, 0)

    def clear_state(self) -> None:
        self._dataset = None
        self.state.archive_path = None
        self.state.step_index = 0
        self._update_labels_empty()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _on_load(self) -> None:
        path = Path(self._panel.path)
        self.playback_state.is_playing = False
        if path.is_dir():
            self._scan_folder(path)
            self._panel.set_folder_mode(True)
        else:
            self._panel.set_folder_mode(False)
            self._load_and_activate(path)

    def _scan_folder(self, folder: Path) -> None:
        if not folder.exists() or not folder.is_dir():
            raise FileNotFoundError(f"Archive folder not found: {folder}")
        paths = sorted(
            p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".npz"
        )
        if not paths:
            raise FileNotFoundError(f"No .npz archives found in: {folder}")
        self.logger.info("Folder scanned", folder=str(folder), archives=len(paths))
        self._panel.set_archive_list(paths)
        self._load_and_activate(paths[0])

    def _on_archive_selected(self, index: int) -> None:
        if index < 0:
            return
        data = self._panel.selected_archive_path
        if data is None:
            return
        path = Path(data)
        self.logger.action("Archive selected from list", archive=path.name)
        self.playback_state.is_playing = False
        self._load_and_activate(path)

    def _load_and_activate(self, path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(f"Simulation archive not found: {path}")
        self.logger.info("Load dataset archive", path=str(path))
        arrays, metadata = load_sr_archive(path)
        self._dataset = LoadedDataset(arrays, metadata)
        self.state.step_index = 0
        self.state.archive_path = path
        self.playback_state.playback_ready = True
