from __future__ import annotations

from PySide6 import QtWidgets
from PySide6.QtWebEngineWidgets import QWebEngineView

_MAX_ENTRIES = 3000

_BASE_HTML = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  :root {
    --bg: #1e1e2e;
    --fg: #cdd6f4;
    --muted: #6c7086;
    --border: #313244;
    --key: #89b4fa;
    --str: #a6e3a1;
    --num: #fab387;
    --debug-bg: #1e1e2e;
    --info-bg: #1e1e2e;
    --warn-bg: #332b1e;
    --error-bg: #2e1e1e;
    --debug-accent: #6c7086;
    --info-accent: #89b4fa;
    --warn-accent: #f9e2af;
    --error-accent: #f38ba8;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: var(--bg);
    color: var(--fg);
    font-family: "Cascadia Code", "Consolas", "Fira Code", monospace;
    font-size: 12px;
    line-height: 1.5;
    padding: 4px 0;
  }
  .entry {
    padding: 2px 10px;
    border-bottom: 1px solid var(--border);
  }
  .entry.debug { background: var(--debug-bg); }
  .entry.info  { background: var(--info-bg); }
  .entry.warning { background: var(--warn-bg); }
  .entry.error { background: var(--error-bg); }
  .ts { color: var(--muted); }
  .lvl { font-weight: 700; text-transform: uppercase; }
  .lvl.debug   { color: var(--debug-accent); }
  .lvl.info    { color: var(--info-accent); }
  .lvl.warning { color: var(--warn-accent); }
  .lvl.error   { color: var(--error-accent); }
  .scope { color: var(--muted); }
  .msg { color: var(--fg); }
  .field-key { color: var(--key); }
  .field-sep { color: var(--muted); }
  .jt { display: inline; }
  .jt details { display: block; }
  .jt > details { display: inline; }
  .jt details[open] { display: block; margin: 4px 0 2px 0; }
  .jt > details[open] { display: block; margin: 4px 0 2px 12px; }
  details summary {
    cursor: pointer;
    list-style: none;
    color: var(--muted);
  }
  details summary::-webkit-details-marker { display: none; }
  details summary:hover { color: var(--fg); }
  details summary .arrow::before { content: "▶ "; font-size: 9px; }
  details[open] > summary .arrow::before { content: "▼ "; font-size: 9px; }
  .jt-body {
    margin-left: 16px;
    border-left: 1px solid var(--border);
    padding-left: 8px;
  }
  .jt-row { display: block; line-height: 1.6; }
  .bracket { color: var(--muted); }
  .json-key { color: var(--key); }
  .json-str { color: var(--str); }
  .json-num { color: var(--num); }
  .json-bool { color: var(--num); }
  .json-null { color: var(--muted); }
  .jt-preview { color: var(--muted); font-style: italic; }
</style>
</head>
<body id="log"></body>
</html>
"""


class LogPanel(QtWidgets.QWidget):
    """Log panel with collapsible JSON payloads via QWebEngineView."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._view = QWebEngineView()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)

        self._entry_count = 0
        self._page_ready = False
        self._pending: list[str] = []

        self._view.setHtml(_BASE_HTML)
        self._view.loadFinished.connect(self._on_load_finished)

    def _on_load_finished(self, ok: bool) -> None:
        if not ok:
            return
        self._page_ready = True
        for entry_html in self._pending:
            self._inject(entry_html)
        self._pending.clear()

    def append_html(self, entry_html: str) -> None:
        if not self._page_ready:
            self._pending.append(entry_html)
            return
        self._inject(entry_html)

    def _inject(self, entry_html: str) -> None:
        escaped = entry_html.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
        js = (
            f"var e=document.createElement('div');"
            f"e.innerHTML=`{escaped}`;"
            f"document.getElementById('log').appendChild(e.firstElementChild);"
            f"window.scrollTo(0, document.body.scrollHeight);"
        )
        self._entry_count += 1
        if self._entry_count > _MAX_ENTRIES:
            js += "var f=document.getElementById('log').firstChild;if(f)f.remove();"
        self._view.page().runJavaScript(js)

    def clear(self) -> None:
        if self._page_ready:
            self._view.page().runJavaScript("document.getElementById('log').innerHTML='';")
        self._entry_count = 0
        self._pending.clear()
