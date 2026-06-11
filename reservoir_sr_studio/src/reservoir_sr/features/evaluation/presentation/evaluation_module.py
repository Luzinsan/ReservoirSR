from __future__ import annotations

from typing import Any

from PySide6 import QtWidgets

from reservoir_sr.app.app_context import AppContext
from reservoir_sr.features.evaluation.presentation.controllers.evaluation_controller import (
    EvaluationController,
)
from reservoir_sr.features.evaluation.presentation.panels.evaluation_panel import EvaluationPanel


class EvaluationModule:
    """Модуль оценки SR-моделей на готовых архивах."""

    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._panel = EvaluationPanel()
        self._controller = EvaluationController(context=context, panel=self._panel)

    @property
    def widget(self) -> QtWidgets.QWidget:
        return self._panel

    def export_data(self) -> None:
        self._controller.logger.action("Export requested")
        self._controller.logger.warning("Export not implemented")

    def reset_module(self) -> None:
        self._controller.engine.unload()
        self._controller._archive = None
        self._panel.grid.show_empty()
        self._panel.update_step(0, 0, 0)

    def close_resources(self) -> None:
        self._controller.engine.unload()

    def apply_project(self, project: dict[str, Any]) -> None:
        self._controller.logger.action("Apply project requested")
        self._controller.logger.warning("Apply project not implemented")

    def collect_project(self) -> dict[str, Any]:
        return {}
