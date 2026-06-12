from __future__ import annotations

from pathlib import Path

import hydra
from omegaconf import DictConfig, OmegaConf

from reservoir_sr.ml.export.onnx_exporter import OnnxExporter


def _run_single(cfg: DictConfig, source: Path, output: Path) -> None:
    OmegaConf.set_struct(cfg, False)
    cfg.source_checkpoint = str(source)
    cfg.output_path = str(output)
    OmegaConf.set_struct(cfg, True)

    print(f"\n=== Exporting {source.name} → {output} ===")
    OnnxExporter(cfg).run()


def _batch_export(cfg: DictConfig) -> None:
    src_dir = Path(cfg.source_dir)
    dst_root = Path(cfg.destination_dir)

    if not src_dir.is_dir():
        raise FileNotFoundError(f"source_dir is not a directory: {src_dir}")

    ckpts = sorted(src_dir.glob("*.ckpt"))
    if not ckpts:
        raise RuntimeError(f"No *.ckpt files found in {src_dir}")

    dst_dir = dst_root / src_dir.name
    dst_dir.mkdir(parents=True, exist_ok=True)

    print(f"📦 Batch export: {len(ckpts)} checkpoints")
    print(f"   from:  {src_dir}")
    print(f"   to:    {dst_dir}")

    failed: list[tuple[str, str]] = []
    for ckpt in ckpts:
        output = dst_dir / f"{ckpt.stem}.onnx"
        try:
            _run_single(cfg, ckpt, output)
        except Exception as e:
            print(f"!!! Failed: {ckpt.name}: {e}")
            failed.append((ckpt.name, str(e)))

    print(f"\n{'=' * 60}")
    print(f"Summary: {len(ckpts) - len(failed)}/{len(ckpts)} succeeded")
    if failed:
        print(f"\nFailed:")
        for name, err in failed:
            print(f"  • {name}: {err}")
        raise RuntimeError(f"{len(failed)} checkpoint(s) failed to export")


@hydra.main(config_path="../conf", config_name="export", version_base="1.3")
def main(cfg: DictConfig) -> None:
    single_mode = bool(cfg.get("source_checkpoint")) and bool(cfg.get("output_path"))
    batch_mode = bool(cfg.get("source_dir")) and bool(cfg.get("destination_dir"))

    if single_mode and batch_mode:
        raise ValueError(
            "Specify either (source_checkpoint + output_path) for single export "
            "OR (source_dir + destination_dir) for batch export — not both."
        )
    if not single_mode and not batch_mode:
        raise ValueError(
            "Nothing to export. Set either source_checkpoint+output_path "
            "or source_dir+destination_dir."
        )

    if single_mode:
        OnnxExporter(cfg).run()
    else:
        _batch_export(cfg)


if __name__ == "__main__":
    main()