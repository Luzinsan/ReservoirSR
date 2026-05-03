from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from reservoir_sr.common.logging.bus import LogBus
from reservoir_sr.common.logging.formatter import format_field_html


class LogSettings(Protocol):
    log_level: str


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

    def child(self, scope: str) -> EventLogger:
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
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        parts = [format_field_html(key, value) for key, value in fields.items()]
        suffix = f' <span class="field-sep">|</span> {", ".join(parts)}' if parts else ""
        entry_html = (
            f'<div class="entry {level}">'
            f'<span class="ts">{timestamp}</span> '
            f'<span class="lvl {level}">[{level.upper()}]</span>'
            f'<span class="scope">[{html.escape(self.scope)}]</span> '
            f'<span class="msg">{html.escape(message)}</span>'
            f"{suffix}"
            f"</div>"
        )
        self.bus.publish(entry_html)
