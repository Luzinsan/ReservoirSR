from __future__ import annotations

from typing import Any

from PySide6 import QtWidgets

from reservoir_sr.app.app_context import AppContext, AppModuleTab
from reservoir_sr.common.logging import EventLogger


class TrainingModule:
    """Модуль обучения SR-моделей.

    TODO: конфигурация датасета, выбор архитектуры, запуск обучения,
    мониторинг loss/метрик, сохранение чекпоинтов.
    """

    def __init__(self, context: AppContext) -> None:
        self.context = context
        self.logger = EventLogger("TrainingModule", self.context.general, self.context.log_bus)
        self._is_module_active: bool = False

        self._widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self._widget)
        title = QtWidgets.QLabel("Training Module")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        description = QtWidgets.QLabel(
            "Конфигурация датасетов, запуск обучения, мониторинг метрик.\n"
            "Функционал будет реализован в следующих итерациях."
        )
        description.setWordWrap(True)

        placeholder = QtWidgets.QGroupBox("Training Workspace")
        placeholder_layout = QtWidgets.QVBoxLayout(placeholder)
        placeholder_layout.addWidget(
            QtWidgets.QLabel("Placeholder: trainers, experiment controls, loss plots.")
        )

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(placeholder)
        layout.addStretch(1)

        self._bind_subscriptions()
        self.on_nav_changed("current_module", self.context.nav.current_module)

    # ------------------------------------------------------------------
    # Активность модуля
    # ------------------------------------------------------------------

    def _bind_subscriptions(self) -> None:
        self.context.nav.subscribe(self.on_nav_changed)

    def on_nav_changed(self, name: str, value: object) -> None:
        if name == "current_module":
            if value == AppModuleTab.TRAINING:
                self.enter()
            else:
                self.exit()

    def enter(self) -> None:
        self._is_module_active = True
        self.context.nav.status_text = "Training module active"

    def exit(self) -> None:
        self._is_module_active = False

    # ------------------------------------------------------------------
    # ModuleProtocol
    # ------------------------------------------------------------------

    @property
    def widget(self) -> QtWidgets.QWidget:
        return self._widget

    def export_data(self) -> None:
        """TODO: экспорт чекпоинта, графиков обучения, конфигурации эксперимента."""
        self.logger.action("Export requested")
        self.logger.warning("Export not implemented")

    def reset_module(self) -> None:
        """TODO: сброс состояния обучения."""
        self.logger.action("Reset requested")
        self.logger.warning("Reset not implemented")

    def close_resources(self) -> None:
        """TODO: остановка обучения, освобождение GPU/потоков."""
        pass

    def apply_project(self, project: dict[str, Any]) -> None:
        """TODO: применить секцию «training» из проектного файла."""
        self.logger.action("Apply project requested")
        self.logger.warning("Apply project not implemented")

    def collect_project(self) -> dict[str, Any]:
        """TODO: собрать параметры обучения для проектного файла."""
        self.logger.action("Collect project requested")
        self.logger.warning("Collect project not implemented")
        return {}
