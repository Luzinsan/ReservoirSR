from __future__ import annotations

from PySide6 import QtWidgets

from reservoir_sr.app.app_context import AppContext
from reservoir_sr.app.settings_models import normalize_endpoint
from reservoir_sr.common.qt_binding import autobind

from pathlib import Path

_CONF_DIR = Path(__file__).resolve().parent.parent / "conf" / "gui"

GENERAL_BINDINGS = [
    ("endpoint", "endpoint_edit", "text"),
    ("project_directory", "project_directory_edit", "text"),
    ("log_level", "log_level_combo", "data"),
]

DATA_BINDINGS = [
    ("isoline_layer_mode", "data_isoline_mode_combo", "data"),
    ("palette_name", "data_palette_combo", "data"),
    ("isoline_width", "data_isoline_width_spin", "value"),
    ("isoline_level_stride", "data_isoline_stride_spin", "value"),
    # ("vector_color_name", "data_vector_color_edit", "text"),
    ("show_legend", "data_show_legend_checkbox", "checked"),
    ("live_render", "data_live_render_checkbox", "checked"),
    ("simulation_config_path", "data_simulation_config_path_edit", "text"),
]

INFERENCE_BINDINGS = [
    ("device", "inference_device_combo", "data"),
    ("model_dir", "inference_model_dir_edit", "text"),
    ("stats_path", "inference_stats_path_edit", "text"),
    ("input_dir", "inference_input_dir_edit", "text"),
    ("batch_size", "inference_batch_spin", "value"),
    ("cache_results", "inference_cache_checkbox", "checked"),
]


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, context: AppContext, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._context = context
        self._draft = context.snapshot()
        self.setWindowTitle("Settings")
        self.resize(640, 520)

        layout = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs)

        self._build_general_tab()
        self._build_data_tab()
        self._build_inference_tab()
        self._bind_models()

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_general_tab(self) -> None:
        tab = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(tab)

        self.endpoint_edit = QtWidgets.QLineEdit()
        self.project_directory_edit = QtWidgets.QLineEdit()
        self.log_level_combo = QtWidgets.QComboBox()
        for level in ("debug", "info", "warning", "error"):
            self.log_level_combo.addItem(level, level)

        form.addRow("gRPC endpoint", self.endpoint_edit)
        form.addRow("Default project dir", self.project_directory_edit)
        form.addRow("Log level", self.log_level_combo)
        self.tabs.addTab(tab, "General")

    def _build_data_tab(self) -> None:
        tab = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(tab)

        self.data_isoline_mode_combo = QtWidgets.QComboBox()
        for mode in ("off", "overlay", "only"):
            self.data_isoline_mode_combo.addItem(mode, mode)
        self.data_palette_combo = QtWidgets.QComboBox()
        for palette in ("geographical", "water_oil", "mud_water", "ocean", "dawn", "sunset", "rainbow"):
            self.data_palette_combo.addItem(palette, palette)
        self.data_isoline_width_spin = QtWidgets.QSpinBox()
        self.data_isoline_width_spin.setRange(1, 8)
        self.data_isoline_stride_spin = QtWidgets.QSpinBox()
        self.data_isoline_stride_spin.setRange(1, 32)
        # self.data_vector_color_edit = QtWidgets.QLineEdit()
        self.data_show_legend_checkbox = QtWidgets.QCheckBox("Show legend")
        self.data_live_render_checkbox = QtWidgets.QCheckBox("Live render")
        self.data_simulation_config_path_edit = QtWidgets.QLineEdit()
        self.data_simulation_config_path_edit.setPlaceholderText("Путь к JSON-конфигу симуляции")

        form.addRow("Isoline mode", self.data_isoline_mode_combo)
        form.addRow("Palette", self.data_palette_combo)
        form.addRow("Isoline width", self.data_isoline_width_spin)
        form.addRow("Isoline stride", self.data_isoline_stride_spin)
        # form.addRow("Vector color", self.data_vector_color_edit)
        form.addRow("", self.data_show_legend_checkbox)
        form.addRow("", self.data_live_render_checkbox)
        form.addRow("Simulation config", self.data_simulation_config_path_edit)
        self.tabs.addTab(tab, "Data")


    def _build_inference_tab(self) -> None:
        tab = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(tab)

        self.inference_device_combo = QtWidgets.QComboBox()
        for device_name in ("auto", "cpu", "cuda"):
            self.inference_device_combo.addItem(device_name, device_name)
        self.inference_model_dir_edit = QtWidgets.QLineEdit()
        self.inference_stats_path_edit = QtWidgets.QLineEdit()
        self.inference_input_dir_edit = QtWidgets.QLineEdit()
        self.inference_output_dir_edit = QtWidgets.QLineEdit()
        self.inference_batch_spin = QtWidgets.QSpinBox()
        self.inference_batch_spin.setRange(1, 1024)
        self.inference_cache_checkbox = QtWidgets.QCheckBox("Cache results")

        # Extra model files
        self.inference_extra_models_list = QtWidgets.QListWidget()
        self.inference_extra_models_list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.inference_extra_models_list.setMaximumHeight(110)
        add_btn = QtWidgets.QPushButton("Add...")
        remove_btn = QtWidgets.QPushButton("Remove")
        add_btn.clicked.connect(self._on_add_extra_model)
        remove_btn.clicked.connect(self._on_remove_extra_model)

        extra_buttons = QtWidgets.QVBoxLayout()
        extra_buttons.addWidget(add_btn)
        extra_buttons.addWidget(remove_btn)
        extra_buttons.addStretch(1)

        extra_row = QtWidgets.QHBoxLayout()
        extra_row.addWidget(self.inference_extra_models_list, 1)
        extra_row.addLayout(extra_buttons)
        extra_container = QtWidgets.QWidget()
        extra_container.setLayout(extra_row)

        form.addRow("Default device", self.inference_device_combo)
        form.addRow("Default model dir", self.inference_model_dir_edit)
        form.addRow("Extra model files", extra_container)
        form.addRow("Stats file (JSON)", self.inference_stats_path_edit)
        form.addRow("Default input dir", self.inference_input_dir_edit)
        form.addRow("Default output dir", self.inference_output_dir_edit)
        form.addRow("Default batch size", self.inference_batch_spin)
        form.addRow("", self.inference_cache_checkbox)
        self.tabs.addTab(tab, "Inference")

        self._refresh_extra_models_list()

    def _refresh_extra_models_list(self) -> None:
        self.inference_extra_models_list.clear()
        for path in self._draft.inference.extra_model_paths:
            self.inference_extra_models_list.addItem(path)

    def _on_add_extra_model(self) -> None:
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Select ONNX model file(s)", "", "ONNX models (*.onnx)"
        )
        if not files:
            return
        current = list(self._draft.inference.extra_model_paths)
        for f in files:
            if f not in current:
                current.append(f)
        self._draft.inference.extra_model_paths = tuple(current)
        self._refresh_extra_models_list()

    def _on_remove_extra_model(self) -> None:
        selected = {item.text() for item in self.inference_extra_models_list.selectedItems()}
        if not selected:
            return
        remaining = tuple(p for p in self._draft.inference.extra_model_paths if p not in selected)
        self._draft.inference.extra_model_paths = remaining
        self._refresh_extra_models_list()

    def _bind_models(self) -> None:
        autobind(self._draft.general, self, GENERAL_BINDINGS)
        autobind(self._draft.data, self, DATA_BINDINGS)
        autobind(self._draft.inference, self, INFERENCE_BINDINGS)

    def accept(self) -> None:
        self._draft.general.endpoint = normalize_endpoint(self._draft.general.endpoint)
        self._context.apply_from(self._draft)
        self._context.save_to_yaml(_CONF_DIR)
        super().accept()
