from __future__ import annotations

from typing import Protocol


class DataModeController(Protocol):
    """Единый контракт контроллера режима данных для playback-оркестратора."""

    def enter(self) -> None:
        """Переводит контроллер в активное состояние при входе в его вкладку."""
        ...

    def exit(self) -> None:
        """Переводит контроллер в неактивное состояние и очищает временные ресурсы."""
        ...

    def prepare(self) -> None:
        """Подготавливает ресурсы перед началом воспроизведения (инициализация, проверки)."""
        ...

    def step(self, step_count: int) -> bool:
        """Выполняет один playback-тик из `step_count` шагов. True — достигнут конец."""
        ...
