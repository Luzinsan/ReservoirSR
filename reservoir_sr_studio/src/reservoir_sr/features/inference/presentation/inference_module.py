from __future__ import annotations

from typing import Any

from PySide6 import QtWidgets

from reservoir_sr.app.app_context import AppContext, AppModuleTab
from reservoir_sr.common.logging import EventLogger


class InferenceModule:
    """Модуль инференса SR-моделей.

    TODO: выбор чекпоинта, загрузка входных данных (LR),
    запуск суперразрешения, визуализация и сравнение результатов.
    """

    def __init__(self, context: AppContext) -> None:
        self.context = context
        self.logger = EventLogger("InferenceModule", self.context.general, self.context.log_bus)
        self._is_module_active: bool = False

        self._widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self._widget)
        title = QtWidgets.QLabel("Inference Module")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        description = QtWidgets.QLabel(
            "Запуск SR-моделей, визуализация результатов, сравнение LR/HR.\n"
            "Функционал будет реализован в следующих итерациях."
        )
        description.setWordWrap(True)

        placeholder = QtWidgets.QGroupBox("Inference Workspace")
        placeholder_layout = QtWidgets.QVBoxLayout(placeholder)
        placeholder_layout.addWidget(
            QtWidgets.QLabel("Placeholder: model loading, batch inference, result viewer.")
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
            if value == AppModuleTab.INFERENCE:
                self.enter()
            else:
                self.exit()

    def enter(self) -> None:
        self._is_module_active = True
        self.context.nav.status_text = "Inference module active"

    def exit(self) -> None:
        self._is_module_active = False

    # ------------------------------------------------------------------
    # ModuleProtocol
    # ------------------------------------------------------------------

    @property
    def widget(self) -> QtWidgets.QWidget:
        return self._widget

    def export_data(self) -> None:
        """TODO: экспорт SR-результатов (изображения, массивы, метрики качества)."""
        self.logger.action("Export requested")
        self.logger.warning("Export not implemented")

    def reset_module(self) -> None:
        """TODO: сброс загруженной модели и результатов."""
        self.logger.action("Reset requested")
        self.logger.warning("Reset not implemented")

    def close_resources(self) -> None:
        """TODO: освобождение GPU/модели."""
        pass

    def apply_project(self, project: dict[str, Any]) -> None:
        """TODO: применить секцию «inference» из проектного файла."""
        self.logger.action("Apply project requested")
        self.logger.warning("Apply project not implemented")

    def collect_project(self) -> dict[str, Any]:
        """TODO: собрать настройки инференса для проектного файла."""
        self.logger.action("Collect project requested")
        self.logger.warning("Collect project not implemented")
        return {}
