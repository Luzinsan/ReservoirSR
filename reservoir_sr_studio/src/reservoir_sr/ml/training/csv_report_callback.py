from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytorch_lightning as pl
from omegaconf import DictConfig

KPI_METRICS: list[str] = [
    "val_psnr/mean",
    "val_structural/ssim",
    "val_spectral/ergas",
    "val_physics/grad_mae",
    "val_physics/max_ae",
]

ALL_METRICS: list[str] = [
    "meta/params_total",
    "meta/params_model",
    "meta/params_generator",
    "meta/params_discriminator",
    "val/loss",
    "val/g_total",
    "val/g_adv",
    "val_mae/P",
    "val_mae/ST",
    "val_mae/SB",
    *KPI_METRICS,
]


@dataclass(frozen=True)
class KpiTarget:
    metric: str
    operator: str
    threshold: float

    def check(self, value: float | None) -> str:
        if value is None:
            return "n/a"
        if self.operator == ">=":
            return "ok" if value >= self.threshold else "warn"
        if self.operator == "<=":
            return "ok" if value <= self.threshold else "warn"
        return "n/a"


KPI_TARGETS: list[KpiTarget] = [
    KpiTarget("val_psnr/mean", ">=", 30.0),
    KpiTarget("val_structural/ssim", ">=", 0.88),
    KpiTarget("val_spectral/ergas", "<=", 6.0),
    KpiTarget("val_physics/grad_mae", "<=", 0.030),
    KpiTarget("val_physics/max_ae", "<=", 0.200),
]


_REPORT_COLUMNS: list[str] = [
    "experiment",
    "run_name",
    "started_at_utc",
    "finished_at_utc",
    "status",
    "meta/params_total",
    "meta/params_model",
    "meta/params_generator",
    "meta/params_discriminator",
    "val/loss",
    "val/g_total",
    "val/g_adv",
    "val_psnr/mean",
    "val_structural/ssim",
    "val_spectral/ergas",
    "val_physics/grad_mae",
    "val_physics/max_ae",
    "val_mae/P",
    "val_mae/ST",
    "val_mae/SB",
    "kpi_pass_ratio",
    "kpi_status",
]


def _fmt(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.6g}"
    return str(v)


def _now_utc() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


class ExperimentReportCallback(pl.Callback):
    """Appends a single summary row to ``report_path`` at the end of training.

    Aggregates the latest values of ``trainer.callback_metrics`` and computes a KPI gate.
    """

    def __init__(self, *, cfg: DictConfig, report_path: Path) -> None:
        self._cfg = cfg
        self._report_path = report_path
        self._started_at = _now_utc()

    def on_train_end(self, trainer: pl.Trainer, pl_module: pl.LightningModule) -> None:
        ckpt_cb = next(
            (cb for cb in trainer.callbacks if isinstance(cb, pl.callbacks.ModelCheckpoint)),
            None,
        )
        metrics = self._collect_metrics(trainer)
        if ckpt_cb is not None and ckpt_cb.best_model_score is not None:
            best_score = float(ckpt_cb.best_model_score.detach().cpu().item())
            monitor_key = ckpt_cb.monitor or "val/loss"
            metrics[monitor_key] = best_score
        row = self._build_row(metrics, trainer)
        self._append_row(row)


    def _collect_metrics(self, trainer: pl.Trainer) -> dict[str, float | None]:
        out: dict[str, float | None] = {}
        for name in ALL_METRICS:
            value = trainer.callback_metrics.get(name)
            out[name] = None if value is None else float(value.detach().cpu().item())
        return out

    def _build_row(self, metrics: dict[str, float | None], trainer: pl.Trainer) -> dict[str, Any]:
        row: dict[str, Any] = {
            "experiment": self._cfg.globals.experiment_name,
            "run_name": self._cfg.globals.experiment_name,
            "started_at_utc": self._started_at,
            "finished_at_utc": _now_utc(),
            "status": "INTERRUPTED" if trainer.interrupted else "FINISHED",
        }
        row.update(metrics)

        checks = [target.check(metrics.get(target.metric)) for target in KPI_TARGETS]
        passed = sum(1 for c in checks if c == "ok")
        total = sum(1 for c in checks if c != "n/a")
        row["kpi_pass_ratio"] = f"{passed}/{total}" if total > 0 else "n/a"
        row["kpi_status"] = "ok" if total > 0 and passed == total else ("warn" if total > 0 else "n/a")
        return row

    def _append_row(self, row: dict[str, Any]) -> None:
        path = self._report_path
        path.parent.mkdir(parents=True, exist_ok=True)
        is_new = not path.exists()
        with path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=_REPORT_COLUMNS)
            if is_new:
                writer.writeheader()
            writer.writerow({k: _fmt(row.get(k)) for k in _REPORT_COLUMNS})