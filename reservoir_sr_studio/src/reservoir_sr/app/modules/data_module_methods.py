from __future__ import annotations

import uuid
from dataclasses import asdict
from pathlib import Path

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

from reservoir_sr.domain.simulation.config_models import ReservoirLayerConfig, SimulationConfig
from reservoir_sr.features.simulation.presentation.state import ViewMode
from reservoir_sr.infrastructure.grpc.simulation_client import GrpcSimulationClient
from reservoir_sr.features.simulation.application.runtime_service import RuntimeService
from reservoir_sr.features.simulation.application.dataset_generation_service import DatasetGenerationService


class DataModuleMethods:
    @staticmethod
    def _fallback_layers() -> list[ReservoirLayerConfig]:
        return [ReservoirLayerConfig(**asdict(layer)) for layer in SimulationConfig().layers]

    @staticmethod
    def _normalize_layers(raw_layers: object) -> list[ReservoirLayerConfig]:
        if not isinstance(raw_layers, list):
            return DataModuleMethods._fallback_layers()
        layers: list[ReservoirLayerConfig] = []
        for raw in raw_layers:
            if isinstance(raw, dict):
                layers.append(ReservoirLayerConfig(**raw))
            elif isinstance(raw, ReservoirLayerConfig):
                layers.append(raw)
        return layers or DataModuleMethods._fallback_layers()

    def _runtime_cfg(self) -> SimulationConfig:
        payload = dict(self.runtime_state.payload)
        payload.update(
            {
                "nx": int(self.runtime_panel.nx_spin.value()),
                "n_dr": int(self.runtime_panel.n_dr_spin.value()),
                "epsp": float(self.runtime_panel.epsp_spin.value()),
                "tu_seconds": float(self.runtime_panel.tu_spin.value()),
                "tk_days": float(self.runtime_panel.tk_spin.value()),
            }
        )
        cfg_payload = {key: payload[key] for key in self.config_keys if key in payload}
        cfg_payload["layers"] = self._normalize_layers(cfg_payload.get("layers"))
        self.runtime_state.payload = dict(payload)
        return SimulationConfig(**cfg_payload)

    def _clear_metrics(self) -> None:
        self.metrics_state.time.clear()
        self.metrics_state.ai.clear()
        self.metrics_state.ait.clear()
        self.metrics_state.aib.clear()
        self.metrics_panel.curve_ai.setData([], [])
        self.metrics_panel.curve_ait.setData([], [])
        self.metrics_panel.curve_aib.setData([], [])

    def _clear_runtime_tracking(self) -> None:
        self.tracking_state.prev_q = None
        self.tracking_state.prev_pz = None
        self.tracking_state.prev_st = None

    def _clear_dataset_state(self) -> None:
        self.dataset_view_state.archive_path = None
        self.dataset_view_state.arrays = None
        self.dataset_view_state.metadata = None
        self.dataset_view_state.step_index = 0
        self.dataset_view_state.dynamic_index.clear()
        self.dataset_view_panel.loaded_label.setText("Dataset not loaded")
        self.dataset_view_panel.info_label.setText("Нет загруженного архива")
        self.dataset_view_panel.step_label.setText("Step: 0/0")
        self.dataset_view_panel.step_slider.blockSignals(True)
        self.dataset_view_panel.step_slider.setRange(0, 0)
        self.dataset_view_panel.step_slider.setValue(0)
        self.dataset_view_panel.step_slider.blockSignals(False)

    def _has_dataset(self) -> bool:
        return self.dataset_view_state.arrays is not None and self.dataset_view_state.metadata is not None

    def _ensure_runtime_ready(self) -> None:
        if self.runtime_state.runtime_needs_init:
            self._init_simulation()

    def _set_view_mode(self, mode: ViewMode) -> None:
        self.view_mode = mode
        self.data_sources_panel.mode_tabs.blockSignals(True)
        self.data_sources_panel.mode_tabs.setCurrentIndex(0 if mode == ViewMode.RUNTIME else 2)
        self.data_sources_panel.mode_tabs.blockSignals(False)
        self._update_mode_controls()

    def _dataset_total_steps(self) -> int:
        if not self._has_dataset():
            return 0
        assert self.dataset_view_state.arrays is not None
        return int(self.dataset_view_state.arrays["dynamic_scalars"].shape[0])

    def _dataset_dynamic_value(self, name: str, step_index: int | None = None) -> float:
        if not self._has_dataset():
            return 0.0
        assert self.dataset_view_state.arrays is not None
        idx = self.dataset_view_state.dynamic_index[name]
        pos = self.dataset_view_state.step_index if step_index is None else step_index
        return float(self.dataset_view_state.arrays["dynamic_scalars"][pos, idx])

    def _update_dataset_labels(self) -> None:
        panel = self.dataset_view_panel
        if not self._has_dataset():
            panel.loaded_label.setText("Dataset not loaded")
            panel.info_label.setText("Нет загруженного архива")
            panel.step_label.setText("Step: 0/0")
            return

        assert self.dataset_view_state.arrays is not None
        assert self.dataset_view_state.metadata is not None
        total_steps = self._dataset_total_steps()
        lr_shape = tuple(self.dataset_view_state.arrays["lr_fields"].shape)
        hr_shape = tuple(self.dataset_view_state.arrays["hr_fields"].shape)
        channels = ", ".join(self.dataset_view_state.metadata.get("channels", []))
        source = "LR" if panel.resolution_combo.currentData() == "lr" else "HR"
        panel.loaded_label.setText(
            f"{self.dataset_view_state.archive_path.name if self.dataset_view_state.archive_path else ''} | "
            f"LR {lr_shape[2]}x{lr_shape[3]} | HR {hr_shape[2]}x{hr_shape[3]} | "
            f"steps={total_steps}"
        )
        panel.info_label.setText(
            f"Источник: {source}\n"
            f"Каналы: {channels}\n"
            f"LR tensor: {lr_shape}\n"
            f"HR tensor: {hr_shape}\n"
            f"Dynamic scalars: {tuple(self.dataset_view_state.arrays['dynamic_scalars'].shape)}\n"
            f"Static scalars: {tuple(self.dataset_view_state.arrays['static_scalars'].shape)}\n"
            f"Layer scalars: {tuple(self.dataset_view_state.arrays['layer_scalars'].shape)}"
        )
        current = 0 if total_steps == 0 else self.dataset_view_state.step_index + 1
        panel.step_label.setText(f"Step: {current}/{total_steps}")
        panel.step_slider.blockSignals(True)
        panel.step_slider.setRange(0, max(total_steps - 1, 0))
        panel.step_slider.setValue(self.dataset_view_state.step_index)
        panel.step_slider.blockSignals(False)

    def _update_mode_controls(self) -> None:
        data_module_active = self._is_data_module_active()
        runtime_active = self.view_mode == ViewMode.RUNTIME and self.runtime_timer.isActive()
        dataset_ready = self._has_dataset()

        self.data_sources_panel.mode_tabs.setTabEnabled(1, not runtime_active)
        self.data_sources_panel.mode_tabs.setTabEnabled(2, not runtime_active or self.view_mode == ViewMode.DATASET)
        self.dataset_view_panel.load_button.setEnabled(not runtime_active)
        self.dataset_view_panel.browse_button.setEnabled(not runtime_active)
        self.dataset_view_panel.resolution_combo.setEnabled(dataset_ready and self.view_mode == ViewMode.DATASET)
        self.dataset_view_panel.step_slider.setEnabled(dataset_ready and self.view_mode == ViewMode.DATASET)
        self.playback_panel.apply_runtime_button.setEnabled(self.view_mode == ViewMode.RUNTIME)
        self.playback_panel.apply_runtime_button.setText(
            "Apply Runtime" if self.view_mode == ViewMode.RUNTIME else "Runtime unavailable"
        )
        self.playback_panel.start_button.setEnabled(data_module_active and (self.view_mode == ViewMode.RUNTIME or dataset_ready))
        self.playback_panel.step_button.setEnabled(data_module_active and (self.view_mode == ViewMode.RUNTIME or dataset_ready))
        self.playback_panel.reset_button.setEnabled(data_module_active and (self.view_mode == ViewMode.RUNTIME or dataset_ready))
        self.playback_panel.pause_button.setEnabled(data_module_active)
        self.playback_panel.apply_runtime_button.setEnabled(data_module_active and self.view_mode == ViewMode.RUNTIME)
        self.data_sources_panel.setEnabled(data_module_active)
        self.config_panel.setEnabled(data_module_active)
        self.tabs.setEnabled(data_module_active)
        self.act_start.setEnabled(data_module_active)
        self.act_metrics.setEnabled(data_module_active)
        self.act_settings.setEnabled(data_module_active)

    def _rebuild_dataset_metrics(self) -> None:
        if not self._has_dataset():
            self._clear_metrics()
            return

        total = self.dataset_view_state.step_index + 1
        self.metrics_state.time = [self._dataset_dynamic_value("time", i) for i in range(total)]
        self.metrics_state.ai = [self._dataset_dynamic_value("AI", i) for i in range(total)]
        self.metrics_state.ait = [self._dataset_dynamic_value("AIT", i) for i in range(total)]
        self.metrics_state.aib = [self._dataset_dynamic_value("AIB", i) for i in range(total)]
        self.metrics_panel.curve_ai.setData(self.metrics_state.time, self.metrics_state.ai)
        self.metrics_panel.curve_ait.setData(self.metrics_state.time, self.metrics_state.ait)
        self.metrics_panel.curve_aib.setData(self.metrics_state.time, self.metrics_state.aib)

    def _update_status_for_dataset(self, st_arr: np.ndarray | None) -> None:
        if not self._has_dataset():
            self.status_runtime.setText("Dataset not loaded")
            return

        st_delta = 0.0
        if st_arr is not None and self.tracking_state.prev_st is not None and self.tracking_state.prev_st.shape == st_arr.shape:
            st_delta = float(np.max(np.abs(st_arr - self.tracking_state.prev_st)))
        if st_arr is not None:
            self.tracking_state.prev_st = st_arr.copy()

        self.status_runtime.setText(
            f"dataset step={self.dataset_view_state.step_index + 1}/{self._dataset_total_steps()}  "
            f"t={self._dataset_dynamic_value('time'):.3f}  "
            f"Q={self._dataset_dynamic_value('Q_fld'):.6f}  "
            f"Pz={self._dataset_dynamic_value('P_zab'):.6f}  "
            f"dST(L1)={st_delta:.3e}  "
            f"H2O={self._dataset_dynamic_value('AI') * 100.0:.3f}%"
        )

    def _current_dataset_field_array(self) -> np.ndarray:
        assert self.dataset_view_state.arrays is not None
        key = "lr_fields" if self.dataset_view_panel.resolution_combo.currentData() == "lr" else "hr_fields"
        channel_idx = {"P": 0, "ST": 1, "SB": 2}[self.render_state.current_field]
        return self.dataset_view_state.arrays[key][self.dataset_view_state.step_index, channel_idx].astype(np.float64, copy=False)

    def _current_runtime_field_array(self) -> np.ndarray:
        fields = self.runtime_service.get_fields(self.runtime_state.simulation_id, (self.render_state.current_field,))
        return fields.data[self.render_state.current_field].values

    def _dataset_grid_dims(self) -> tuple[int, int]:
        assert self.dataset_view_state.arrays is not None
        key = "lr_fields" if self.dataset_view_panel.resolution_combo.currentData() == "lr" else "hr_fields"
        _, _, nz, nx = self.dataset_view_state.arrays[key].shape
        return int(nz), int(nx)

    def _current_field_array(self) -> np.ndarray:
        if self.view_mode == ViewMode.DATASET:
            return self._current_dataset_field_array()
        self._ensure_runtime_ready()
        return self._current_runtime_field_array()

    def _scene_dims(self) -> tuple[float, float]:
        if self.view_mode == ViewMode.DATASET and self._has_dataset():
            assert self.dataset_view_state.metadata is not None
            lr_grid = self.dataset_view_state.metadata.get("lr_grid", {})
            return float(lr_grid.get("nx", self.runtime_state.runtime_nx)), float(
                lr_grid.get("nz", self.runtime_state.runtime_nz)
            )
        return float(self.runtime_state.runtime_nx), float(self.runtime_state.runtime_nz)

    def _init_simulation(self) -> None:
        self.on_pause()
        self._reconnect_client_if_needed()
        self.runtime_state.simulation_id = self.runtime_panel.simulation_id_edit.text().strip() or "sim_main"
        cfg = self._runtime_cfg()
        response = self.runtime_service.initialize(self.runtime_state.simulation_id, cfg)
        if not response.ok:
            raise RuntimeError(response.message)
        self.runtime_state.runtime_nx = response.nx
        self.runtime_state.runtime_nz = response.nz
        self.runtime_state.runtime_needs_init = False
        self.render_state.viewport_signature = None
        self._clear_metrics()
        self._clear_runtime_tracking()
        self._set_view_mode(ViewMode.RUNTIME)
        self._refresh_plots()

    def _reconnect_client_if_needed(self) -> None:
        new_endpoint = self.runtime_panel.endpoint_edit.text().strip() or "localhost:5000"
        if self.runtime_state.endpoint == new_endpoint:
            return
        self.client.close()
        self.client = GrpcSimulationClient(new_endpoint)
        self.runtime_service = RuntimeService(self.client)
        self.runtime_state.endpoint = new_endpoint
        self.generation_service = DatasetGenerationService(new_endpoint)

    def on_start(self) -> None:
        if not self._is_data_module_active():
            return
        if self.view_mode == ViewMode.RUNTIME:
            self._ensure_runtime_ready()
        self.runtime_timer.start(int(self.runtime_panel.timer_spin.value()))
        self._update_mode_controls()

    def on_pause(self) -> None:
        if not self._is_data_module_active():
            return
        self.runtime_timer.stop()
        self._update_mode_controls()

    def on_step(self) -> None:
        if not self._is_data_module_active():
            return
        step_count = int(self.runtime_panel.batch_spin.value())
        if self.view_mode == ViewMode.DATASET:
            self._advance_dataset(step_count)
        else:
            self._advance(step_count)

    def on_reset(self) -> None:
        if not self._is_data_module_active():
            return
        if self.view_mode == ViewMode.DATASET:
            self._reset_dataset_view()
        else:
            self._init_simulation()

    def on_timer_tick(self) -> None:
        self.on_step()

    def _advance(self, step_count: int) -> None:
        self._ensure_runtime_ready()
        step = self.runtime_service.step(self.runtime_state.simulation_id, step_count=step_count)
        if not step.ok:
            self.on_pause()
            raise RuntimeError(step.message)

        self.metrics_state.time.append(step.time)
        self.metrics_state.ai.append(step.ai)
        self.metrics_state.ait.append(step.ait)
        self.metrics_state.aib.append(step.aib)
        self.metrics_panel.curve_ai.setData(self.metrics_state.time, self.metrics_state.ai)
        self.metrics_panel.curve_ait.setData(self.metrics_state.time, self.metrics_state.ait)
        self.metrics_panel.curve_aib.setData(self.metrics_state.time, self.metrics_state.aib)
        st_arr = self._refresh_plots() if self.render_state.live_render else None
        st_delta = 0.0
        if st_arr is not None and self.tracking_state.prev_st is not None and self.tracking_state.prev_st.shape == st_arr.shape:
            st_delta = float(np.max(np.abs(st_arr - self.tracking_state.prev_st)))
        if st_arr is not None:
            self.tracking_state.prev_st = st_arr.copy()
        dq = 0.0 if self.tracking_state.prev_q is None else float(step.q_fld - self.tracking_state.prev_q)
        dpz = 0.0 if self.tracking_state.prev_pz is None else float(step.p_zab - self.tracking_state.prev_pz)
        self.tracking_state.prev_q = float(step.q_fld)
        self.tracking_state.prev_pz = float(step.p_zab)
        self.status_runtime.setText(
            f"t={step.time:.3f}  Q={step.q_fld:.6f} (dQ={dq:+.3e})  "
            f"Pz={step.p_zab:.6f} (dPz={dpz:+.3e})  dST(L1)={st_delta:.3e}  H2O={step.ai * 100.0:.3f}%"
        )

    def _advance_dataset(self, step_count: int) -> None:
        if not self._has_dataset():
            return
        total_steps = self._dataset_total_steps()
        if total_steps == 0:
            return
        self.dataset_view_state.step_index = min(self.dataset_view_state.step_index + step_count, total_steps - 1)
        self._rebuild_dataset_metrics()
        self._show_dataset_step(force_render=self.render_state.live_render)
        if self.dataset_view_state.step_index >= total_steps - 1 and self.runtime_timer.isActive():
            self.on_pause()

    def _show_dataset_step(self, force_render: bool = True) -> None:
        self._rebuild_dataset_metrics()
        st_arr = self._refresh_plots() if (force_render or self.render_state.live_render) else None
        self._update_dataset_labels()
        self._update_status_for_dataset(st_arr)

    def _reset_dataset_view(self) -> None:
        if not self._has_dataset():
            return
        self.on_pause()
        self.dataset_view_state.step_index = 0
        self._clear_runtime_tracking()
        self._show_dataset_step()

    def _refresh_plots(self) -> np.ndarray | None:
        arr = self._current_field_array()
        scene_dims = self._scene_dims()
        rgb, _ = self.plot_controller.render_legacy_palette_map(
            arr,
            render_mode=self.render_state.render_mode,
            palette_name=self.render_state.palette_name,
            current_field=self.render_state.current_field,
        )
        if self.render_state.isoline_layer_mode == "only":
            rgb = np.full_like(rgb, 255)
        self.maps_panel.image.setLookupTable(None)
        self.maps_panel.image.setImage(rgb, autoLevels=False)
        self.maps_panel.image.setRect(QtCore.QRectF(0, 0, scene_dims[0], scene_dims[1]))
        self.isoline_items = self.plot_controller.update_isolines(
            self.maps_panel.plot,
            self.isoline_items,
            arr=arr,
            mode=self.render_state.isoline_layer_mode,
            stride=self.render_state.isoline_level_stride,
            width=self.render_state.isoline_width,
            palette_name=self.render_state.palette_name,
            current_field=self.render_state.current_field,
            scene_dims=scene_dims,
        )
        self.maps_panel.title_label.setText(self.plot_controller.field_title(self.render_state.current_field))
        self._update_map_overlays()
        self._fit_map_to_grid()
        self._update_legend()
        return arr if self.render_state.current_field == "ST" else None

    def _sync_field_buttons(self) -> None:
        for label, button in self.maps_panel.field_buttons.items():
            button.setChecked(self.maps_panel.field_button_map[label] == self.render_state.current_field)

    def on_select_field(self, field_name: str) -> None:
        self.render_state.current_field = field_name
        self._sync_field_buttons()
        self._refresh_plots()

    def on_render_mode_changed(self, _: int) -> None:
        mode = self.maps_panel.render_mode_combo.currentData()
        self.render_state.render_mode = mode if isinstance(mode, str) else "smooth"
        self._refresh_plots()

    def on_isoline_layer_changed(self, _: int) -> None:
        mode = self.maps_panel.isoline_combo.currentData()
        self.render_state.isoline_layer_mode = mode if isinstance(mode, str) else "off"
        self._refresh_plots()

    def on_palette_changed(self, _: int) -> None:
        palette_name = self.maps_panel.palette_combo.currentData()
        self.render_state.palette_name = palette_name if isinstance(palette_name, str) else "geographical"
        self._refresh_plots()

    def on_toggle_legend(self, checked: bool) -> None:
        self.render_state.show_legend = checked
        self.maps_panel.legend_label.setVisible(checked)
        if checked:
            self._update_legend()

    def on_toggle_live_render(self, checked: bool) -> None:
        self.render_state.live_render = checked
        if checked:
            self._refresh_plots()

    def on_toggle_zoom(self, checked: bool) -> None:
        self.maps_panel.plot.getPlotItem().setMouseEnabled(x=checked, y=checked)

    def on_zoom_reset(self) -> None:
        self._fit_map_to_grid(force=True)

    def on_isoline_width_changed(self, value: int) -> None:
        self.render_state.isoline_width = int(value)
        if self.render_state.isoline_layer_mode != "off":
            self._refresh_plots()

    def on_isoline_stride_changed(self, value: int) -> None:
        self.render_state.isoline_level_stride = int(value)
        if self.render_state.isoline_layer_mode != "off":
            self._refresh_plots()

    def on_pick_vector_color(self) -> None:
        base_color = QtGui.QColor(self.render_state.vector_color_name)
        color = QtWidgets.QColorDialog.getColor(base_color, self, "Цвет векторов")
        if color.isValid():
            self.render_state.vector_color_name = color.name()
            self.render_state.overlay_signature = None
            self._update_map_overlays()
            self._fit_map_to_grid(force=True)

    def _update_map_overlays(self) -> None:
        sig = self._scene_dims()
        if self.render_state.overlay_signature == sig:
            return
        self.render_state.overlay_signature = sig
        self.layer_lines, self.layer_labels, self.vector_items = self.plot_controller.update_map_overlays(
            self.maps_panel.plot,
            scene_dims=sig,
            vector_color=QtGui.QColor(self.render_state.vector_color_name),
            layer_lines=self.layer_lines,
            layer_labels=self.layer_labels,
            vector_items=self.vector_items,
        )

    def _fit_map_to_grid(self, force: bool = False) -> None:
        sig = self._scene_dims()
        if not force and self.render_state.viewport_signature == sig:
            return
        self.render_state.viewport_signature = sig
        self.plot_controller.fit_map_to_grid(self.maps_panel.plot, scene_dims=sig)

    def _update_legend(self) -> None:
        if not self.render_state.show_legend:
            return
        self.plot_controller.update_legend(self.maps_panel.legend_label, palette_name=self.render_state.palette_name)

    def on_browse_cfg(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select config file", str(Path.cwd()), "JSON (*.json)")
        if file_path:
            self.config_panel.path_edit.setText(file_path)

    def on_save_cfg(self) -> None:
        path = Path(self.config_panel.path_edit.text().strip())
        cfg = self._runtime_cfg()
        runtime = asdict(cfg)
        runtime.update(
            {
                "step_batch": self.runtime_panel.batch_spin.value(),
                "timer_ms": self.runtime_panel.timer_spin.value(),
                "render_mode": self.render_state.render_mode,
                "isoline_layer_mode": self.render_state.isoline_layer_mode,
                "palette": self.render_state.palette_name,
                "show_legend": self.render_state.show_legend,
                "live_render": self.render_state.live_render,
                "isoline_width": self.render_state.isoline_width,
                "isoline_level_stride": self.render_state.isoline_level_stride,
                "vector_color": self.render_state.vector_color_name,
            }
        )
        self.runtime_state.payload = dict(runtime)
        payload = {
            "endpoint": self.runtime_panel.endpoint_edit.text().strip(),
            "simulation_id": self.runtime_panel.simulation_id_edit.text().strip(),
            "runtime": runtime,
            "dataset": {
                "output_dir": self.dataset_generation_panel.output_dir_edit.text().strip(),
                "job_id": self.dataset_generation_panel.job_id_edit.text().strip(),
                "steps": self.dataset_generation_panel.steps_spin.value(),
                "file": self.dataset_view_panel.archive_path_edit.text().strip(),
            },
        }
        self.config_service.save(path, payload)
        self.statusBar().showMessage(f"Config saved: {path}", 3000)

    def on_load_cfg(self) -> None:
        path = Path(self.config_panel.path_edit.text().strip())
        payload = self.config_service.load(path)
        runtime = payload.get("runtime", {})
        if isinstance(runtime, dict):
            self.runtime_state.payload = dict(runtime)
        dataset = payload.get("dataset", {})
        self.runtime_panel.endpoint_edit.setText(payload.get("endpoint", self.runtime_panel.endpoint_edit.text()))
        self.runtime_panel.simulation_id_edit.setText(payload.get("simulation_id", self.runtime_panel.simulation_id_edit.text()))
        self.runtime_panel.nx_spin.setValue(int(runtime.get("nx", self.runtime_panel.nx_spin.value())))
        self.runtime_panel.n_dr_spin.setValue(int(runtime.get("n_dr", self.runtime_panel.n_dr_spin.value())))
        self.runtime_panel.epsp_spin.setValue(float(runtime.get("epsp", self.runtime_panel.epsp_spin.value())))
        self.runtime_panel.tu_spin.setValue(float(runtime.get("tu_seconds", self.runtime_panel.tu_spin.value())))
        self.runtime_panel.tk_spin.setValue(float(runtime.get("tk_days", self.runtime_panel.tk_spin.value())))
        self.runtime_panel.batch_spin.setValue(int(runtime.get("step_batch", self.runtime_panel.batch_spin.value())))
        self.runtime_panel.timer_spin.setValue(int(runtime.get("timer_ms", self.runtime_panel.timer_spin.value())))
        rm = runtime.get("render_mode")
        if isinstance(rm, str):
            idx_rm = self.maps_panel.render_mode_combo.findData(rm if rm in {"simple", "smooth"} else "smooth")
            if idx_rm >= 0:
                self.maps_panel.render_mode_combo.setCurrentIndex(idx_rm)
        ilm = runtime.get("isoline_layer_mode")
        if not isinstance(ilm, str) and rm == "isolines":
            ilm = "only"
        if isinstance(ilm, str):
            idx_ilm = self.maps_panel.isoline_combo.findData(ilm)
            if idx_ilm >= 0:
                self.maps_panel.isoline_combo.setCurrentIndex(idx_ilm)
        palette_name = runtime.get("palette")
        if isinstance(palette_name, str):
            idx_pal = self.maps_panel.palette_combo.findData(palette_name)
            if idx_pal >= 0:
                self.maps_panel.palette_combo.setCurrentIndex(idx_pal)
        self.maps_panel.show_legend_checkbox.setChecked(
            bool(runtime.get("show_legend", self.maps_panel.show_legend_checkbox.isChecked()))
        )
        self.maps_panel.live_render_checkbox.setChecked(
            bool(runtime.get("live_render", self.maps_panel.live_render_checkbox.isChecked()))
        )
        self.maps_panel.isoline_width_spin.setValue(int(runtime.get("isoline_width", self.maps_panel.isoline_width_spin.value())))
        self.maps_panel.isoline_stride_spin.setValue(
            int(runtime.get("isoline_level_stride", self.maps_panel.isoline_stride_spin.value()))
        )
        color_name = runtime.get("vector_color")
        if isinstance(color_name, str):
            color = QtGui.QColor(color_name)
            if color.isValid():
                self.render_state.vector_color_name = color.name()
                self.render_state.overlay_signature = None
                self._update_map_overlays()
        self.dataset_generation_panel.output_dir_edit.setText(
            dataset.get("output_dir", self.dataset_generation_panel.output_dir_edit.text())
        )
        self.dataset_generation_panel.job_id_edit.setText(
            dataset.get("job_id", self.dataset_generation_panel.job_id_edit.text())
        )
        self.dataset_generation_panel.steps_spin.setValue(
            int(dataset.get("steps", self.dataset_generation_panel.steps_spin.value()))
        )
        self.dataset_view_panel.archive_path_edit.setText(
            dataset.get("file", self.dataset_view_panel.archive_path_edit.text())
        )
        self.statusBar().showMessage(f"Config loaded: {path}", 3000)

    def on_browse_dataset_out(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select dataset output directory",
            self.dataset_generation_panel.output_dir_edit.text(),
        )
        if path:
            self.dataset_generation_panel.output_dir_edit.setText(path)

    def on_browse_dataset_file(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select dataset file",
            str(Path.cwd()),
            "Dataset (*.npz *.sr *.zip)",
        )
        if file_path:
            self.dataset_view_panel.archive_path_edit.setText(file_path)

    def on_load_dataset_file(self) -> None:
        path = Path(self.dataset_view_panel.archive_path_edit.text().strip())
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {path}")
        self.on_pause()
        archive = self.view_service.load_archive(path)
        self.dataset_view_state.arrays = archive.arrays
        self.dataset_view_state.metadata = archive.metadata
        self.dataset_view_state.archive_path = path
        self.dataset_view_state.dynamic_index = {
            name: idx for idx, name in enumerate(archive.metadata.get("dynamic_scalar_names", []))
        }
        self.dataset_view_state.step_index = 0
        self.runtime_state.runtime_needs_init = True
        self.render_state.viewport_signature = None
        self._clear_metrics()
        self._clear_runtime_tracking()
        self._set_view_mode(ViewMode.DATASET)
        self._show_dataset_step(force_render=True)

    def on_mode_tab_changed(self, index: int) -> None:
        target_mode = ViewMode.DATASET if index == 2 else ViewMode.RUNTIME
        self.view_mode = target_mode
        self.render_state.viewport_signature = None
        if self.view_mode == ViewMode.RUNTIME:
            self._ensure_runtime_ready()
            self._refresh_plots()
        else:
            self._update_dataset_labels()
            if self._has_dataset():
                self._show_dataset_step(force_render=True)
            else:
                self._clear_metrics()
                self._clear_runtime_tracking()
                self.status_runtime.setText(
                    "Dataset mode: загрузите архив для просмотра или используйте Runtime / Dataset generation"
                )
        self._update_mode_controls()

    def on_dataset_resolution_changed(self, _: int) -> None:
        if self.view_mode != ViewMode.DATASET or not self._has_dataset():
            return
        self._clear_runtime_tracking()
        self.render_state.viewport_signature = None
        self._show_dataset_step(force_render=True)

    def on_dataset_slider_changed(self, value: int) -> None:
        if self.view_mode != ViewMode.DATASET or not self._has_dataset():
            return
        if value == self.dataset_view_state.step_index:
            return
        self.dataset_view_state.step_index = int(value)
        self._clear_runtime_tracking()
        self._show_dataset_step(force_render=True)

    def on_dataset_start(self) -> None:
        self._reconnect_client_if_needed()
        cfg = self._runtime_cfg()
        out_dir = Path(self.dataset_generation_panel.output_dir_edit.text().strip() or "dataset_out")
        user_job = self.dataset_generation_panel.job_id_edit.text().strip()
        job_id = user_job or f"job_{uuid.uuid4().hex[:10]}"
        response = self.client.run_dataset_job(
            job_id=job_id,
            output_dir=str(out_dir),
            steps=int(self.dataset_generation_panel.steps_spin.value()),
            config=cfg,
        )
        if not response.ok:
            raise RuntimeError(response.message)
        self.dataset_job_state.active_job_id = response.job_id
        self.dataset_generation_panel.job_id_edit.setText(response.job_id)
        self.dataset_generation_panel.progress_bar.setValue(0)
        self.dataset_generation_panel.status_label.setText("running")
        self.dataset_timer.start(1000)

    def _poll_dataset_status(self) -> None:
        if not self.dataset_job_state.active_job_id:
            return
        status = self.client.get_job_status(self.dataset_job_state.active_job_id)
        total = max(status.steps_total, 1)
        self.dataset_generation_panel.progress_bar.setValue(int(status.steps_done * 100 / total))
        self.dataset_generation_panel.status_label.setText(
            f"{status.state}: {status.steps_done}/{status.steps_total} ({status.message})"
        )
        if status.state.value in {"completed", "failed", "cancelled", "not_found"}:
            self.dataset_timer.stop()
            self.dataset_job_state.active_job_id = None

    def on_dataset_cancel(self) -> None:
        if not self.dataset_job_state.active_job_id:
            return
        self.client.cancel_job(self.dataset_job_state.active_job_id)
        self.dataset_timer.stop()
        self.dataset_generation_panel.status_label.setText("cancel requested")
