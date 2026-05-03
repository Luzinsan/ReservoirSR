from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets


class DatasetViewPanel(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QFormLayout(self)

        self._build_path_row(layout)
        self._build_load_row(layout)
        self._build_archive_row(layout)
        self._build_view_section(layout)

    # ------------------------------------------------------------------
    # Path input
    # ------------------------------------------------------------------

    def _build_path_row(self, layout: QtWidgets.QFormLayout) -> None:
        self.path_edit = QtWidgets.QLineEdit("")
        self.path_edit.setPlaceholderText("File (.npz) or folder path")

        browse_file_action = QtGui.QAction("File...", self)
        browse_folder_action = QtGui.QAction("Folder...", self)
        browse_file_action.triggered.connect(self._browse_file)
        browse_folder_action.triggered.connect(self._browse_folder)

        browse_menu = QtWidgets.QMenu(self)
        browse_menu.addAction(browse_file_action)
        browse_menu.addAction(browse_folder_action)

        browse_button = QtWidgets.QToolButton()
        browse_button.setText("...")
        browse_button.setMenu(browse_menu)
        browse_button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)

        layout.addRow("Path", self._hbox(self.path_edit, browse_button))

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def _build_load_row(self, layout: QtWidgets.QFormLayout) -> None:
        self.load_button = QtWidgets.QPushButton("Load")
        layout.addRow("", self.load_button)

    # ------------------------------------------------------------------
    # Archive selector (hidden by default)
    # ------------------------------------------------------------------

    def _build_archive_row(self, layout: QtWidgets.QFormLayout) -> None:
        self.archive_combo = QtWidgets.QComboBox()
        self._archive_row = layout.rowCount()
        layout.addRow("Archive", self.archive_combo)
        layout.setRowVisible(self._archive_row, False)

    # ------------------------------------------------------------------
    # Viewing controls
    # ------------------------------------------------------------------

    def _build_view_section(self, layout: QtWidgets.QFormLayout) -> None:
        self.resolution_combo = QtWidgets.QComboBox()
        self.resolution_combo.addItem("LR", "lr")
        self.resolution_combo.addItem("HR", "hr")

        self.info_label = QtWidgets.QLabel("No archive loaded")
        self.info_label.setWordWrap(True)

        self.step_label = QtWidgets.QLabel("Step: 0/0")

        self.step_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.step_slider.setRange(0, 0)
        self.step_slider.setEnabled(False)

        layout.addRow("Resolution", self.resolution_combo)
        layout.addRow("Info", self.info_label)
        layout.addRow("Current step", self.step_label)
        layout.addRow("Timeline", self.step_slider)

    # ------------------------------------------------------------------
    # Public methods (called by controller)
    # ------------------------------------------------------------------

    @property
    def path(self) -> str:
        return self.path_edit.text().strip()

    @property
    def selected_archive_path(self) -> str | None:
        return self.archive_combo.currentData()

    def set_archive_list(self, paths: list[Path]) -> None:
        self.archive_combo.blockSignals(True)
        self.archive_combo.clear()
        for p in paths:
            self.archive_combo.addItem(p.name, str(p))
        self.archive_combo.setCurrentIndex(0)
        self.archive_combo.blockSignals(False)

    def set_folder_mode(self, enabled: bool) -> None:
        layout: QtWidgets.QFormLayout = self.layout()
        layout.setRowVisible(self._archive_row, enabled)

    def update_info(self, text: str) -> None:
        self.info_label.setText(text)

    def update_step(self, current: int, total: int, slider_value: int) -> None:
        self.step_label.setText(f"Step: {current}/{total}")
        self.step_slider.blockSignals(True)
        self.step_slider.setRange(0, max(total - 1, 0))
        self.step_slider.setValue(slider_value)
        self.step_slider.setEnabled(total > 1)
        self.step_slider.blockSignals(False)

    # ------------------------------------------------------------------
    # Browse dialogs
    # ------------------------------------------------------------------

    def _browse_file(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select simulation archive",
            self.path_edit.text() or str(Path.cwd()),
            "Simulation archive (*.npz *.sr *.zip)",
        )
        if file_path:
            self.path_edit.setText(file_path)

    def _browse_folder(self) -> None:
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select archive folder",
            self.path_edit.text() or str(Path.cwd()),
        )
        if folder_path:
            self.path_edit.setText(folder_path)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hbox(*widgets: QtWidgets.QWidget) -> QtWidgets.QWidget:
        container = QtWidgets.QWidget()
        box = QtWidgets.QHBoxLayout(container)
        box.setContentsMargins(0, 0, 0, 0)
        for w in widgets:
            box.addWidget(w)
        return container
