from __future__ import annotations

from typing import Callable

Listener = Callable[[str, object], None]
_MISSING = object()


class ObservableModel:
    def subscribe(self, listener: Listener) -> None:
        listeners = self.__dict__.setdefault("_listeners", [])
        listeners.append(listener)

    def __setattr__(self, name: str, value: object) -> None:
        fields = getattr(type(self), "__dataclass_fields__", {})
        old = self.__dict__.get(name, _MISSING)
        object.__setattr__(self, name, value)
        listeners = self.__dict__.get("_listeners")
        if listeners and name in fields and old is not _MISSING and old != value:
            for listener in tuple(listeners):
                listener(name, value)
