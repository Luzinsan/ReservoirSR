from __future__ import annotations

from pathlib import Path
from typing import Any

from reservoir_sr.infrastructure.storage.config_io import read_json, write_json


class ConfigPersistenceService:
    def load(self, path: Path) -> dict[str, Any]:
        return read_json(path)

    def save(self, path: Path, payload: dict[str, Any]) -> None:
        write_json(path, payload)
