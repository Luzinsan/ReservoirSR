from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch
import torch.nn as nn
from hydra.utils import instantiate
from omegaconf import DictConfig, OmegaConf


class _TensorInputWrapper(nn.Module):

    def __init__(self, inner: nn.Module) -> None:
        super().__init__()
        self.inner = inner

    def forward(self, lr: torch.Tensor) -> torch.Tensor:
        return self.inner({"lr": lr})


@dataclass
class _CheckpointPayload:
    state_dict: dict[str, torch.Tensor]
    ckpt_model_cfg: dict[str, object]
    source: str  # "ema" | "model"


class OnnxExporter:

    def __init__(self, cfg: DictConfig) -> None:
        self._cfg = cfg
        self._source_path = Path(cfg.source_checkpoint)
        self._output_path = Path(cfg.output_path)

    def run(self) -> Path:
        payload = self._extract_checkpoint()
        model = self._build_model(payload)
        self._export(model)
        self._verify(model)
        self._report(payload.source)
        return self._output_path

    # ------------------------------------------------------------------
    # Чекпоинт
    # ------------------------------------------------------------------

    def _extract_checkpoint(self) -> _CheckpointPayload:
        if not self._source_path.is_file():
            raise FileNotFoundError(f"Checkpoint not found: {self._source_path}")

        raw = torch.load(self._source_path, map_location="cpu", weights_only=False)
        state = raw.get("state_dict", raw)

        ema_state = self._strip_prefix(state, "ema_model.")
        model_state = self._strip_prefix(state, "model.")

        if self._cfg.prefer_ema and ema_state:
            weights, source = ema_state, "ema"
        elif model_state:
            weights, source = model_state, "model"
        elif ema_state:
            weights, source = ema_state, "ema"
        else:
            raise RuntimeError(f"No 'model.*' or 'ema_model.*' keys in {self._source_path}")

        return _CheckpointPayload(
            state_dict=weights,
            ckpt_model_cfg=self._read_ckpt_model_cfg(raw),
            source=source,
        )

    @staticmethod
    def _strip_prefix(state: dict, prefix: str) -> dict[str, torch.Tensor]:
        return {
            k[len(prefix):]: v.float().contiguous()
            for k, v in state.items()
            if k.startswith(prefix)
        }

    @staticmethod
    def _read_ckpt_model_cfg(raw: dict) -> dict[str, object]:
        hparams = raw.get("hyper_parameters", {})
        if not hasattr(hparams, "get"):
            return {}
        model_cfg = hparams.get("model")
        if model_cfg is None:
            return {}
        if OmegaConf.is_config(model_cfg):
            model_cfg = OmegaConf.to_container(model_cfg, resolve=True)
        return model_cfg if isinstance(model_cfg, dict) else {}

    # ------------------------------------------------------------------
    # Инстанциация
    # ------------------------------------------------------------------

    def _build_model(self, payload: _CheckpointPayload) -> nn.Module:
        applied = self._apply_ckpt_overrides(self._cfg.model, payload.ckpt_model_cfg)
        if applied:
            print(f"   ℹ️  arch from checkpoint: {applied}")

        model: nn.Module = instantiate(self._cfg.model, _recursive_=False)
        missing, unexpected = model.load_state_dict(payload.state_dict, strict=False)
        if missing or unexpected:
            raise RuntimeError(
                f"Checkpoint does not match architecture. "
                f"missing={list(missing)[:5]} unexpected={list(unexpected)[:5]}"
            )
        model.eval()
        return model

    @staticmethod
    def _apply_ckpt_overrides(
        target: DictConfig, source: dict[str, object]
    ) -> dict[str, object]:
        applied: dict[str, object] = {}
        OmegaConf.set_struct(target, False)
        try:
            for key in list(target.keys()):
                if key not in source:
                    continue
                new_value = source[key]
                if isinstance(new_value, dict):
                    continue
                if target.get(key) != new_value:
                    target[key] = new_value
                    applied[key] = new_value
        finally:
            OmegaConf.set_struct(target, True)
        return applied

    # ------------------------------------------------------------------
    # Экспорт
    # ------------------------------------------------------------------

    def _export(self, model: nn.Module) -> None:
        ex = self._cfg.export
        wrapped = _TensorInputWrapper(model).eval()
        dummy = torch.randn(*ex.dummy_input_shape)

        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        torch.onnx.export(
            wrapped,
            dummy,
            str(self._output_path),
            input_names=list(ex.input_names),
            output_names=list(ex.output_names),
            dynamic_axes={k: dict(v) for k, v in ex.dynamic_axes.items()},
            opset_version=int(ex.opset_version),
            do_constant_folding=bool(ex.do_constant_folding),
            dynamo=False,
            export_params=True,
            keep_initializers_as_inputs=False,
        )

    # ------------------------------------------------------------------
    # Проверка
    # ------------------------------------------------------------------

    def _verify(self, model: nn.Module) -> None:
        try:
            import numpy as np
            import onnxruntime as ort
        except ImportError:
            print("   ⚠️  onnxruntime не установлен — проверка пропущена")
            return

        ex = self._cfg.export
        wrapped = _TensorInputWrapper(model).eval()

        torch.manual_seed(42)
        test_input = torch.randn(*ex.dummy_input_shape) * 0.5

        with torch.no_grad():
            pt = wrapped(test_input).numpy()

        sess_opts = ort.SessionOptions()
        sess_opts.intra_op_num_threads = 1
        sess_opts.inter_op_num_threads = 1
        sess_opts.log_severity_level = 3

        session = ort.InferenceSession(
            str(self._output_path),
            sess_options=sess_opts,
            providers=["CPUExecutionProvider"],
        )
        ox = session.run(
            [session.get_outputs()[0].name],
            {session.get_inputs()[0].name: test_input.numpy()},
        )[0]

        max_diff = float(np.abs(pt - ox).max())
        mean_diff = float(np.abs(pt - ox).mean())
        out_range = float(pt.max() - pt.min())

        print(f"\n🧪 Verification (PyTorch vs ONNX)")
        print(f"   max abs diff:   {max_diff:.2e}")
        print(f"   mean abs diff:  {mean_diff:.2e}")
        print(f"   output range:   {out_range:.4f}")

        if max_diff > 1e-3:
            raise RuntimeError(
                f"ONNX output differs by {max_diff:.2e} (threshold 1e-3). "
                f"Export is broken."
            )
        print(f"   ✅ ONNX matches PyTorch (max diff < 1e-3)")

    # ------------------------------------------------------------------
    # Отчёт
    # ------------------------------------------------------------------

    def _report(self, weight_source: str) -> None:
        src_mb = self._source_path.stat().st_size / 1024**2
        dst_mb = self._output_path.stat().st_size / 1024**2

        print(f"\n✅ ONNX export finished")
        print(f"   source:  {self._source_path}")
        print(f"   weights: {weight_source}")
        print(f"   output:  {self._output_path}")
        print(f"   size:    {src_mb:.2f} MB → {dst_mb:.2f} MB")