from __future__ import annotations

from PySide6 import QtWidgets

from reservoir_sr.common.observable import ObservableModel

BindingSpec = tuple[str, str, str]


def autobind(model: ObservableModel, panel: QtWidgets.QWidget, bindings: list[BindingSpec]) -> None:
    widget_map: dict[str, tuple[QtWidgets.QWidget, str]] = {}
    for field_name, widget_name, binding_kind in bindings:
        widget = _resolve_widget(panel, widget_name)
        widget_map[field_name] = (widget, binding_kind)
        field_type = type(getattr(model, field_name))
        if binding_kind == "text":
            widget.textChanged.connect(lambda value, f=field_name: setattr(model, f, value))
        elif binding_kind == "value":
            widget.valueChanged.connect(lambda value, f=field_name: setattr(model, f, value))
        elif binding_kind == "checked":
            widget.toggled.connect(lambda value, f=field_name: setattr(model, f, value))
        elif binding_kind == "data":
            widget.currentIndexChanged.connect(
                lambda _index, f=field_name, w=widget: setattr(model, f, w.currentData())
            )
        elif binding_kind == "index":
            widget.currentChanged.connect(
                lambda idx, f=field_name, ft=field_type: setattr(model, f, ft(idx))
            )

    def sync_field(name: str, value: object) -> None:
        mapped = widget_map.get(name)
        if mapped is None:
            return
        widget, binding_kind = mapped
        widget.blockSignals(True)
        if binding_kind == "text":
            widget.setText("" if value is None else str(value))
        elif binding_kind == "value":
            widget.setValue(value)
        elif binding_kind == "checked":
            widget.setChecked(bool(value))
        elif binding_kind == "data":
            widget.setCurrentIndex(max(0, widget.findData(value)))
        elif binding_kind == "index":
            widget.setCurrentIndex(int(value))
        widget.blockSignals(False)

    model.subscribe(sync_field)
    for field_name, _, _ in bindings:
        sync_field(field_name, getattr(model, field_name))


def _resolve_widget(root: QtWidgets.QWidget, dotted_name: str) -> QtWidgets.QWidget:
    obj = root
    for part in dotted_name.split("."):
        obj = getattr(obj, part)
    return obj
