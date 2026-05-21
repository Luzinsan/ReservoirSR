from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mlflow.entities import Run
from mlflow.tracking import MlflowClient


# Minimal KPI set for SR fractured-porous reservoir reporting.
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


def _fmt(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.6g}"
    return str(v)


def _run_timestamp(run: Run) -> str:
    ts = run.info.start_time
    if ts is None:
        return ""
    return datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc).isoformat()


def _get(run: Run, key: str) -> float | None:
    val = run.data.metrics.get(key)
    if val is None:
        return None
    return float(val)


def _collect_rows(client: MlflowClient, experiment_names: list[str], max_runs: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for experiment_name in experiment_names:
        exp = client.get_experiment_by_name(experiment_name)
        if exp is None:
            continue

        runs = client.search_runs(
            experiment_ids=[exp.experiment_id],
            filter_string="attributes.status = 'FINISHED'",
            max_results=max_runs,
            order_by=["attributes.start_time DESC"],
        )

        for run in runs:
            row: dict[str, Any] = {
                "experiment": experiment_name,
                "run_id": run.info.run_id,
                "run_name": run.data.tags.get("mlflow.runName", ""),
                "started_at_utc": _run_timestamp(run),
                "status": run.info.status,
            }
            for metric_name in ALL_METRICS:
                row[metric_name] = _get(run, metric_name)

            # KPI gate summary from the selected key metrics.
            checks = [target.check(row.get(target.metric)) for target in KPI_TARGETS]
            passed = sum(1 for c in checks if c == "ok")
            total = sum(1 for c in checks if c != "n/a")
            row["kpi_pass_ratio"] = f"{passed}/{total}" if total > 0 else "n/a"
            row["kpi_status"] = "ok" if total > 0 and passed == total else ("warn" if total > 0 else "n/a")

            rows.append(row)
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "experiment",
        "run_name",
        "run_id",
        "started_at_utc",
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
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _fmt(row.get(k)) for k in headers})


def _write_md(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "experiment",
        "run_name",
        "params_total",
        "val/loss",
        "val_psnr/mean",
        "val_structural/ssim",
        "val_spectral/ergas",
        "val_physics/grad_mae",
        "val_physics/max_ae",
        "kpi_pass_ratio",
        "kpi_status",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        vals = [
            row.get("experiment"),
            row.get("run_name"),
            row.get("meta/params_total"),
            row.get("val/loss"),
            row.get("val_psnr/mean"),
            row.get("val_structural/ssim"),
            row.get("val_spectral/ergas"),
            row.get("val_physics/grad_mae"),
            row.get("val_physics/max_ae"),
            row.get("kpi_pass_ratio"),
            row.get("kpi_status"),
        ]
        lines.append("| " + " | ".join(_fmt(v) for v in vals) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export compact SR report from MLflow runs.")
    parser.add_argument(
        "--tracking-uri",
        default="http://127.0.0.1:5000",
        help="MLflow tracking URI.",
    )
    parser.add_argument(
        "--experiments",
        nargs="+",
        default=[
            "mdsr_baseline",
            "mdsr_conditioned",
            "rrdb_baseline",
            "srresnet_baseline",
            "rrdb_v1"
        ],
        help="Experiment names to include.",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=20,
        help="Max FINISHED runs per experiment.",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/reports",
        help="Output directory for exported report files.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    out_dir = Path(args.output_dir)
    client = MlflowClient(tracking_uri=args.tracking_uri)
    rows = _collect_rows(client, args.experiments, args.max_runs)

    csv_path = out_dir / "mlflow_sr_report.csv"
    md_path = out_dir / "mlflow_sr_report.md"
    _write_csv(csv_path, rows)
    _write_md(md_path, rows)
    print(f"Exported: {csv_path}")
    print(f"Exported: {md_path}")
    print(f"Rows: {len(rows)}")


if __name__ == "__main__":
    main()
