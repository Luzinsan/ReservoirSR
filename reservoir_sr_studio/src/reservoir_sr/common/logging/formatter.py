from __future__ import annotations

import html
import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path

_COLLAPSIBLE_THRESHOLD = 80


def format_field_html(key: str, value: object) -> str:
    normalized = _normalize(value)
    k = f'<span class="field-key">{html.escape(key)}</span>'
    if isinstance(normalized, (dict, list)):
        compact = json.dumps(normalized, ensure_ascii=False, default=str)
        if len(compact) > _COLLAPSIBLE_THRESHOLD:
            tree = _render_tree(normalized)
            return f'{k}=<span class="jt">{tree}</span>'
        return f"{k}={html.escape(compact)}"
    return f"{k}={html.escape(repr(normalized))}"


def _render_tree(value: object) -> str:
    if isinstance(value, dict):
        if not value:
            return '<span class="bracket">{}</span>'
        preview = f"{len(value)} keys"
        rows = "".join(
            f'<div class="jt-row">'
            f'<span class="json-key">"{html.escape(k)}"</span>: '
            f"{_render_tree(v)},"
            f"</div>"
            for k, v in value.items()
        )
        return (
            f"<details>"
            f'<summary><span class="arrow"></span>'
            f'<span class="bracket">{{</span>'
            f'<span class="jt-preview"> {html.escape(preview)} </span>'
            f'<span class="bracket">}}</span></summary>'
            f'<div class="jt-body">{rows}</div>'
            f'<span class="bracket">}}</span>'
            f"</details>"
        )
    if isinstance(value, list):
        if not value:
            return '<span class="bracket">[]</span>'
        preview = f"{len(value)} items"
        rows = "".join(
            f'<div class="jt-row">{_render_tree(v)},</div>'
            for v in value
        )
        return (
            f"<details>"
            f'<summary><span class="arrow"></span>'
            f'<span class="bracket">[</span>'
            f'<span class="jt-preview"> {html.escape(preview)} </span>'
            f'<span class="bracket">]</span></summary>'
            f'<div class="jt-body">{rows}</div>'
            f'<span class="bracket">]</span>'
            f"</details>"
        )
    if isinstance(value, str):
        return f'<span class="json-str">"{html.escape(value)}"</span>'
    if isinstance(value, bool):
        return f'<span class="json-bool">{"true" if value else "false"}</span>'
    if value is None:
        return '<span class="json-null">null</span>'
    return f'<span class="json-num">{html.escape(str(value))}</span>'


def _normalize(value: object) -> object:
    if is_dataclass(value):
        return {key: _normalize(item) for key, item in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_normalize(item) for item in value)
    return value
