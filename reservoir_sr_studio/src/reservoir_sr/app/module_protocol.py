from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ModuleProtocol(Protocol):
    """Контракт, которому должен соответствовать каждый модуль-вкладка.

    MainWindow вызывает эти методы через ``module_tabs.currentWidget()``
    без знания о конкретном типе модуля.
    """

    def export_data(self) -> None:
        """Экспорт результатов текущего модуля (карта, метрики, чекпоинт, ...)."""
        ...

    def reset_module(self) -> None:
        """Полный сброс состояния модуля в начальное."""
        ...

    def close_resources(self) -> None:
        """Освобождение ресурсов при закрытии приложения (таймеры, gRPC, ...)."""
        ...

    def apply_project(self, project: dict[str, Any]) -> None:
        """Применить настройки из проектного файла."""
        ...

    def collect_project(self) -> dict[str, Any]:
        """Собрать текущие настройки модуля для записи в проектный файл."""
        ...
