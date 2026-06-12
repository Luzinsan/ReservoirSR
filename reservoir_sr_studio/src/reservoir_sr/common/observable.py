from typing import Any, Callable, Mapping
from collections.abc import Sequence

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

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]):
        fields = cls.__dataclass_fields__
        kwargs: dict[str, Any] = {}
        for name, fld in fields.items():
            if name not in data:
                continue
            value = data[name]
            type_str = str(fld.type)
            if "tuple" in type_str and isinstance(value, Sequence) and not isinstance(value, str):
                value = tuple(value)
            kwargs[name] = value
        return cls(**kwargs)

    def to_mapping(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name in type(self).__dataclass_fields__:
            value = getattr(self, name)
            if isinstance(value, tuple):
                value = list(value)
            result[name] = value
        return result