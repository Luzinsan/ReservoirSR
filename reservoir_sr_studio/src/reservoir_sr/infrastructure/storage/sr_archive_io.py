from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Any

import numpy as np


def load_sr_archive(path: Path) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    arrays: dict[str, np.ndarray] = {}
    metadata: dict[str, Any] = {}

    with zipfile.ZipFile(path, "r") as archive:
        for name in archive.namelist():
            data = archive.read(name)
            if name.endswith(".npy"):
                arrays[Path(name).stem] = np.load(io.BytesIO(data), allow_pickle=False)
            elif name == "meta.json":
                metadata = json.loads(data.decode("utf-8-sig"))

    return arrays, metadata


def write_sr_archive(path: Path, arrays: dict[str, np.ndarray], metadata: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("meta.json", json.dumps(metadata, indent=2, ensure_ascii=True))
        for name, values in arrays.items():
            buffer = io.BytesIO()
            np.save(buffer, np.asarray(values), allow_pickle=False)
            archive.writestr(f"{name}.npy", buffer.getvalue())
