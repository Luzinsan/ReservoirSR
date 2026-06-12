from __future__ import annotations

import random
from pathlib import Path

import numpy as np
from PySide6 import QtWidgets, QtCore

from reservoir_sr.app.app_context import AppContext, AppModuleTab
from reservoir_sr.common.logging import EventLogger
from reservoir_sr.domain.training.normalization_stats import NormalizationStats
from reservoir_sr.domain.training.norm_config import NormConfig
from reservoir_sr.features.evaluation.presentation.panels.evaluation_panel import EvaluationPanel
from reservoir_sr.features.evaluation.presentation.view_models import EvaluationState
from reservoir_sr.features.inference.application.sr_inference_engine import SrInferenceEngine
from reservoir_sr.infrastructure.storage.sr_archive_io import load_sr_archive
from reservoir_sr.ml.data.loaded_archive import LoadedArchive
from reservoir_sr.ml.preprocessing.normalizer import Normalizer

_PREFETCH_BATCH = 16
_SPLIT_SEED = 42
_VAL_FRACTION = 0.15
_TEST_FRACTION = 0.15


class EvaluationController:
    """Контроллер вкладки Evaluation."""

    def __init__(self, context: AppContext, panel: EvaluationPanel) -> None:
        self.context = context
        self.panel = panel
        self.logger = EventLogger("EvaluationController", self.context.general, self.context.log_bus)

        self.state = EvaluationState()
        self.engine = SrInferenceEngine()

        self._archive: LoadedArchive | None = None
        self._archive_paths: list[Path] = []
        self._normalizer: Normalizer | None = None

        self._frame_cache: dict[int, tuple] = {}
        self._lr_hr_per_step: list[tuple[np.ndarray, np.ndarray]] = []
        self._render_timer = QtCore.QTimer()
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(16)
        self._render_timer.timeout.connect(self._render_current_step)

        self._connect_signals()
        self.context.nav.subscribe(self._on_nav_changed)
        self.context.inference.subscribe(self._on_settings_changed)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _on_nav_changed(self, name: str, value: object) -> None:
        if name == "current_module" and value == AppModuleTab.EVALUATION:
            self.context.nav.status_text = "Evaluation module active"
            self._refresh_models()
            self._refresh_archives()

    def _on_settings_changed(self, name: str, _value: object) -> None:
        if name in ("model_dir", "extra_model_paths"):
            self._refresh_models()
        elif name == "stats_path":
            self._normalizer = None
            self.engine.unload()
            self._refresh_models()
        elif name == "input_dir":
            self._refresh_archives()

    def _connect_signals(self) -> None:
        self.panel.model_combo.currentIndexChanged.connect(self._on_model_changed)
        self.panel.split_combo.currentIndexChanged.connect(self._on_split_changed)
        self.panel.archive_combo.currentIndexChanged.connect(self._on_archive_changed)
        self.panel.step_slider.valueChanged.connect(self._on_step_changed)
        self.panel.prefetch_button.clicked.connect(self._on_prefetch)

    # ------------------------------------------------------------------
    # Models
    # ------------------------------------------------------------------

    def _refresh_models(self) -> None:
        models = self.context.inference.available_models()
        self.panel.set_models(models)
        if not models:
            self._set_status("⚠️ No ONNX models found. Configure paths in Settings.", warn=True)
            return
        if not self.engine.is_ready:
            self._load_model(models[0])

    def _on_model_changed(self, index: int) -> None:
        if index < 0:
            return
        path = Path(self.panel.model_combo.itemData(index))
        if self.engine.model_path == path:
            return
        self._load_model(path)
        if self._archive is not None:
            self._render_current_step()

    def _load_model(self, path: Path) -> None:
        normalizer = self._ensure_normalizer()
        if normalizer is None:
            return
        self._set_status(f"⏳ Loading model {path.name}...")
        try:
            self.engine.load(path, normalizer)
        except Exception as exc:
            self.logger.error("Failed to load ONNX model", path=str(path), detail=str(exc))
            self._set_status(f"❌ Load failed: {exc}", warn=True)
            return
        self.state.model_path = path
        size_mb = path.stat().st_size / 1024**2
        self._set_status(f"✅ Model loaded ({size_mb:.2f} MB)")
        self._update_prefetch_button()

    def _ensure_normalizer(self) -> Normalizer | None:
        if self._normalizer is not None:
            return self._normalizer
        stats_path_str = self.context.inference.stats_path.strip()
        if not stats_path_str:
            self._set_status("⚠️ Stats file path not configured (Settings → Inference)", warn=True)
            return None
        stats_path = Path(stats_path_str)
        if not stats_path.is_file():
            self._set_status(f"⚠️ Stats file not found: {stats_path}", warn=True)
            return None
        try:
            stats = NormalizationStats.from_json(stats_path)
        except Exception as exc:
            self.logger.error("Failed to read stats", path=str(stats_path), detail=str(exc))
            self._set_status(f"❌ Stats load failed: {exc}", warn=True)
            return None
        self._normalizer = Normalizer(stats, config={"norm": NormConfig()})
        return self._normalizer

    # ------------------------------------------------------------------
    # Archives
    # ------------------------------------------------------------------

    def _on_split_changed(self, _index: int) -> None:
        self.state.split = self.panel.split_combo.currentData()
        self._refresh_archives()

    def _refresh_archives(self) -> None:
        input_dir_str = self.context.inference.input_dir.strip()
        if not input_dir_str:
            self._archive_paths = []
            self.panel.set_archives([])
            self._set_status("⚠️ Input dir not configured (Settings → Inference)", warn=True)
            return
        input_dir = Path(input_dir_str)
        if not input_dir.is_dir():
            self._archive_paths = []
            self.panel.set_archives([])
            self._set_status(f"⚠️ Input dir not found: {input_dir}", warn=True)
            return

        archives = sorted(
            list(input_dir.glob("*.npz"))
            + list(input_dir.glob("*.sr"))
            + list(input_dir.glob("*.zip"))
        )
        if not archives:
            self._archive_paths = []
            self.panel.set_archives([])
            self._set_status(f"⚠️ No archives in {input_dir}", warn=True)
            return

        paths = self._select_split(archives, self.state.split)
        self._archive_paths = paths
        self.panel.set_archives(paths)
        self._archive = None
        self._frame_cache.clear()
        self._lr_all = None
        self._hr_all = None
        self.engine.invalidate_cache()
        self.panel.grid.show_empty()
        self.panel.update_step(0, 0, 0)
        self._update_prefetch_button()
        self._set_status(f"Split «{self.state.split}»: {len(paths)} archives")

    @staticmethod
    def _select_split(all_archives: list[Path], split: str) -> list[Path]:
        """Воспроизводит логику SrDataModule._discover_and_split_datasets."""
        shuffled = all_archives.copy()
        random.Random(_SPLIT_SEED).shuffle(shuffled)
        total = len(shuffled)
        val_count = int(total * _VAL_FRACTION)
        test_count = int(total * _TEST_FRACTION)
        train_count = total - val_count - test_count

        if split == "train":
            return sorted(shuffled[:train_count])
        if split == "val":
            return sorted(shuffled[train_count : train_count + val_count])
        return sorted(shuffled[train_count + val_count :])

    def _on_archive_changed(self, _index: int) -> None:
        data = self.panel.archive_combo.currentData()
        if data is None or data < 0:
            return
        path = self._archive_paths[int(data)]
        self._load_archive(path)

    def _load_archive(self, path: Path) -> None:
        self._set_status(f"⏳ Loading archive {path.name}...")
        try:
            arrays, metadata = load_sr_archive(path)
        except Exception as exc:
            self.logger.error("Failed to load archive", path=str(path), detail=str(exc))
            self._set_status(f"Archive load failed: {exc}", warn=True)
            return

        self._archive = LoadedArchive(arrays, metadata)
        self.engine.invalidate_cache()
        self._frame_cache.clear()
        self._precompute_lr_hr_cache()
        self.state.archive_path = path
        self.state.step_index = 0
        total = self._archive.total_steps
        self.panel.update_step(1 if total > 0 else 0, total, 0)
        self._update_prefetch_button()
        self._set_status(f"Archive loaded ({total} timesteps)")
        if self.engine.is_ready and total > 0:
            self._render_current_step()

    # ------------------------------------------------------------------
    # Step navigation
    # ------------------------------------------------------------------

    def _on_step_changed(self, value: int) -> None:
        self.state.step_index = int(value)
        if self._archive is None or not self.engine.is_ready:
            return
        if not self._render_timer.isActive():
            self._render_timer.start()

    def _precompute_lr_hr_cache(self) -> None:
        if self._archive is None:
            return
        lr_all = self._archive._arrays["lr_fields"]  # (T, C, Z, X) — view
        hr_all = self._archive._arrays["hr_fields"]
        self._lr_all = np.ascontiguousarray(lr_all, dtype=np.float32)
        self._hr_all = np.ascontiguousarray(hr_all, dtype=np.float32)

    def _build_frame(self, step: int) -> tuple:
        lr = self._lr_all[step]
        hr = self._hr_all[step]
        sr = self.engine.upscale(lr, cache_key=step)
        diff = np.abs(sr - hr)

        hr_min = hr.reshape(hr.shape[0], -1).min(axis=1)
        hr_max = hr.reshape(hr.shape[0], -1).max(axis=1)
        safe_max = np.where(hr_max - hr_min < 1e-12, hr_min + 1e-6, hr_max)
        field_levels = list(zip(hr_min.tolist(), safe_max.tolist()))

        diff_max = diff.reshape(diff.shape[0], -1).max(axis=1)
        diff_max_safe = np.where(diff_max < 1e-12, 1e-6, diff_max)
        diff_levels = [(0.0, float(v)) for v in diff_max_safe]
        return lr, hr, sr, diff, field_levels, diff_levels

    def _render_current_step(self) -> None:
        if self._archive is None or not self.engine.is_ready:
            return

        step = self.state.step_index
        frame = self._frame_cache.get(step)
        if frame is None:
            frame = self._build_frame(step)
            if len(self._frame_cache) > 64:
                self._frame_cache.pop(next(iter(self._frame_cache)))
            self._frame_cache[step] = frame

        lr, hr, sr, diff, field_levels, diff_levels = frame
        self.panel.grid.update_frame_fast(lr, hr, sr, diff, field_levels, diff_levels)
        self.panel.update_step(step + 1, self._archive.total_steps, step)
        self.context.nav.status_text = self._format_step_info(self._archive, step)

    @staticmethod
    def _format_step_info(archive: LoadedArchive, step: int) -> str:
        try:
            t = archive.dynamic_value("time", step)
            ai = archive.dynamic_value("AI", step)
            return f"step {step + 1}/{archive.total_steps} | t={t:.2f} | H2O={ai * 100:.2f}%"
        except (KeyError, IndexError):
            return f"step {step + 1}/{archive.total_steps}"

    # ------------------------------------------------------------------
    # Prefetch
    # ------------------------------------------------------------------

    def _on_prefetch(self) -> None:
        if self._archive is None or not self.engine.is_ready:
            return
        total = self._archive.total_steps
        self.state.is_prefetching = True
        self.panel.set_progress(0, total, visible=True)
        self.panel.prefetch_button.setEnabled(False)
        try:
            for start in range(0, total, _PREFETCH_BATCH):
                end = min(start + _PREFETCH_BATCH, total)
                pending = [s for s in range(start, end) if not self.engine.is_cached(s)]
                if pending:
                    batch = np.stack([self._archive.field_tensor(s, "lr") for s in pending])
                    self.engine.upscale_batch(batch, cache_keys=pending)
                self.panel.set_progress(end, total, visible=True)
                QtWidgets.QApplication.processEvents()
            self._set_status(f"✅ Prefetched {total} steps")
        finally:
            self.state.is_prefetching = False
            self.panel.set_progress(0, 0, visible=False)
            self._update_prefetch_button()

    def _update_prefetch_button(self) -> None:
        ready = (
            self._archive is not None
            and self.engine.is_ready
            and self._archive.total_steps > 0
            and not self.state.is_prefetching
        )
        self.panel.prefetch_button.setEnabled(ready)

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    def _set_status(self, message: str, *, warn: bool = False) -> None:
        self.panel.status_label.setText(message)
        if warn:
            self.logger.warning(message)
        else:
            self.logger.info(message)