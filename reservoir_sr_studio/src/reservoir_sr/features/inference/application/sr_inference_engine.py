from __future__ import annotations

from pathlib import Path

import numpy as np
import onnxruntime as ort

from reservoir_sr.ml.preprocessing.normalizer import Normalizer


class SrInferenceEngine:
    """ONNX-based SR engine: LR (RAW) → SR (physical units)."""

    _CACHE_LIMIT = 1024

    def __init__(self) -> None:
        self._session: ort.InferenceSession | None = None
        self._normalizer: Normalizer | None = None
        self._model_path: Path | None = None
        self._input_name: str = ""
        self._output_name: str = ""
        self._cache: dict[int, np.ndarray] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def load(self, model_path: Path, normalizer: Normalizer, num_threads: int = 4) -> None:
        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        opts.intra_op_num_threads = num_threads
        opts.log_severity_level = 3
        session = ort.InferenceSession(
            str(model_path),
            sess_options=opts,
            providers=["CPUExecutionProvider"],
        )
        self._session = session
        self._normalizer = normalizer
        self._model_path = model_path
        self._input_name = session.get_inputs()[0].name
        self._output_name = session.get_outputs()[0].name
        self._cache.clear()

    def unload(self) -> None:
        self._session = None
        self._normalizer = None
        self._model_path = None
        self._cache.clear()

    @property
    def is_ready(self) -> bool:
        return self._session is not None and self._normalizer is not None

    @property
    def model_path(self) -> Path | None:
        return self._model_path

    def invalidate_cache(self) -> None:
        self._cache.clear()

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def upscale(self, lr_raw: np.ndarray, cache_key: int | None = None) -> np.ndarray:
        """LR (C, Z, X) raw → SR (C, Z', X') physical units."""
        if cache_key is not None and cache_key in self._cache:
            return self._cache[cache_key]

        sr = self._run(lr_raw[np.newaxis, ...])[0]

        if cache_key is not None:
            self._store_in_cache(cache_key, sr)
        return sr

    def upscale_batch(self, lr_batch_raw: np.ndarray, cache_keys: list[int] | None = None) -> np.ndarray:
        """LR (B, C, Z, X) raw → SR (B, C, Z', X') physical units."""
        sr_batch = self._run(lr_batch_raw)
        if cache_keys is not None:
            for key, arr in zip(cache_keys, sr_batch, strict=True):
                self._store_in_cache(key, arr)
        return sr_batch

    def is_cached(self, cache_key: int) -> bool:
        return cache_key in self._cache

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run(self, lr_batch_raw: np.ndarray) -> np.ndarray:
        if self._session is None or self._normalizer is None:
            raise RuntimeError("SrInferenceEngine: model is not loaded")

        normalized = np.stack(
            [self._normalizer.normalize_fields(arr, "lr") for arr in lr_batch_raw]
        ).astype(np.float32)
        sr_norm = self._session.run([self._output_name], {self._input_name: normalized})[0]
        return np.stack(
            [self._normalizer.denormalize_fields(arr, "hr") for arr in sr_norm]
        )

    def _store_in_cache(self, key: int, value: np.ndarray) -> None:
        if len(self._cache) >= self._CACHE_LIMIT:
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = value
