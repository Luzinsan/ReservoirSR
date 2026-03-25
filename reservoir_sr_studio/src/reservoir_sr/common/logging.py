from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Protocol

from PySide6 import QtCore


class LogSettings(Protocol):
    log_level: str


class LogBus(QtCore.QObject):
    message_logged = QtCore.Signal(str)

    def publish(self, message: str) -> None:
        self.message_logged.emit(message)


_LEVEL_PRIORITY = {
    "debug": 10,
    "info": 20,
    "warning": 30,
    "error": 40,
}


@dataclass(frozen=True)
class EventLogger:
    scope: str
    settings: LogSettings
    bus: LogBus

    def child(self, scope: str) -> "EventLogger":
        return EventLogger(scope=scope, settings=self.settings, bus=self.bus)

    def debug(self, message: str, **fields: object) -> None:
        self._emit("debug", message, **fields)

    def info(self, message: str, **fields: object) -> None:
        self._emit("info", message, **fields)

    def warning(self, message: str, **fields: object) -> None:
        self._emit("warning", message, **fields)

    def error(self, message: str, **fields: object) -> None:
        self._emit("error", message, **fields)

    def action(self, message: str, **fields: object) -> None:
        self.debug(message, **fields)

    def _emit(self, level: str, message: str, **fields: object) -> None:
        if _LEVEL_PRIORITY[level] < _LEVEL_PRIORITY.get(self.settings.log_level, 20):
            return
        suffix = ""
        if fields:
            parts = [f"{key}={_normalize_log_value(value)!r}" for key, value in fields.items()]
            suffix = " | " + ", ".join(parts)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.bus.publish(f"[{timestamp}][{level.upper()}][{self.scope}] {message}{suffix}")


def _normalize_log_value(value: object) -> object:
    if is_dataclass(value):
        return {key: _normalize_log_value(item) for key, item in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _normalize_log_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_log_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_normalize_log_value(item) for item in value)
    return value
