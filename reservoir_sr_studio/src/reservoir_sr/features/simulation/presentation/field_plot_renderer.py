from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets


class FieldPlotRenderer:
    def geographical_palette(self, pal_size: int = 21) -> np.ndarray:
        colors = np.zeros((pal_size, 3), dtype=np.uint8)
        third = pal_size // 3
        index = 0

        def _step(num: int, den: int, count: int) -> float:
            if count > 1:
                return count * (num - den) / (count + 1.0) / (count - 1.0)
            return count * (num - den) / (count + 1.0)

        mg = _step(237, 103, third)
        mr = _step(114, 103, third)
        for i in range(1, third + 1):
            index += 1
            colors[index - 1] = (103 + int(mr) * (i - 1), 237 - int(mg) * (i - 1), 255)

        mr = _step(207, 63, third)
        mg = _step(247, 141, third)
        mb = _step(186, 16, third)
        for i in range(1, third + 1):
            index += 1
            colors[index - 1] = (207 - int(mr) * (i - 1), 247 - int(mg) * (i - 1), 186 - int(mb) * (i - 1))

        mr = _step(237, 97, third)
        mg = _step(231, 81, third)
        mb = _step(207, 37, third)
        for i in range(1, third + 1):
            index += 1
            colors[index - 1] = (237 - int(mr) * (i - 1), 231 - int(mg) * (i - 1), 207 - int(mb) * (i - 1))
        return colors

    def linear_palette(self, c1: tuple[int, int, int], c2: tuple[int, int, int], n: int = 21) -> np.ndarray:
        t = np.linspace(0.0, 1.0, n, dtype=np.float64)[:, None]
        a = np.asarray(c1, dtype=np.float64)[None, :]
        b = np.asarray(c2, dtype=np.float64)[None, :]
        return (a + (b - a) * t).round().astype(np.uint8)

    def rainbow_palette(self, n: int = 21) -> np.ndarray:
        anchors = np.asarray(
            [
                (255, 103, 103),
                (244, 186, 103),
                (244, 255, 103),
                (103, 237, 156),
                (103, 203, 255),
                (114, 103, 255),
                (255, 103, 169),
            ],
            dtype=np.float64,
        )
        x = np.linspace(0.0, 1.0, anchors.shape[0], dtype=np.float64)
        xi = np.linspace(0.0, 1.0, n, dtype=np.float64)
        out = np.empty((n, 3), dtype=np.uint8)
        for k in range(3):
            out[:, k] = np.interp(xi, x, anchors[:, k]).round().astype(np.uint8)
        return out

    def active_palette(self, palette_name: str) -> np.ndarray:
        return {
            "geographical": self.geographical_palette(21),
            "water_oil": self.linear_palette((94, 94, 94), (120, 255, 255), 21),
            "mud_water": self.linear_palette((230, 255, 255), (74, 74, 74), 21),
            "ocean": self.linear_palette((8, 50, 180), (8, 242, 180), 21),
            "dawn": self.linear_palette((235, 0, 0), (0, 0, 128), 21),
            "sunset": self.linear_palette((95, 150, 255), (255, 240, 255), 21),
            "rainbow": self.rainbow_palette(21),
        }.get(palette_name, self.geographical_palette(21))

    def palette_degree_for_field(self, current_field: str) -> int:
        if current_field in {"SB", "ST"}:
            return 1
        if current_field == "P":
            return 0
        return 2

    def build_diap(self, s_min: float, s_max: float, pal_size: int, current_field: str) -> np.ndarray:
        if abs(s_max - s_min) < 1e-12:
            s_max = s_min + 1e-6
        pr1 = s_min - (s_max - s_min) / 100.0
        degree = self.palette_degree_for_field(current_field)
        diap = np.zeros((pal_size + 3,), dtype=np.float64)
        for i in range(1, pal_size + 1):
            prm = (i - 1) / pal_size
            if degree == 1:
                prm = prm**1.5
            elif degree == 2:
                prm = (prm**0.5 + np.log1p(prm) ** 0.5) / 2.0
            diap[i] = s_max - (s_max - pr1) * prm
        diap[0] = s_max + (s_max - s_min) / 100.0
        diap[pal_size + 2] = s_min - (s_max - s_min) / 80.0
        diap[1] = s_max
        diap[pal_size] = s_min + (s_max - s_min) / 100.0
        diap[pal_size + 1] = s_min - (s_max - s_min) / 100.0
        return diap

    def normalize_image(self, values: np.ndarray) -> np.ndarray:
        values = np.asarray(values, dtype=np.float64)
        if values.size == 0:
            return values
        v_min = float(values.min())
        v_max = float(values.max())
        if abs(v_max - v_min) < 1e-12:
            return np.zeros_like(values, dtype=np.float64)
        return (values - v_min) / (v_max - v_min)

    def render_legacy_palette_map(
        self,
        arr: np.ndarray,
        *,
        render_mode: str,
        palette_name: str,
        current_field: str,
    ) -> tuple[np.ndarray, np.ndarray]:
        palette = self.active_palette(palette_name)
        s_min = float(np.min(arr))
        s_max = float(np.max(arr))
        pal_size = 21
        diap = self.build_diap(s_min, s_max, pal_size, current_field)

        cell_subdiv = 2 if render_mode == "simple" else 4
        nz, nx = arr.shape
        h = max((nz - 1) * cell_subdiv, 1)
        w = max((nx - 1) * cell_subdiv, 1)
        if nz < 2 or nx < 2:
            idx = np.zeros((h, w), dtype=np.int32)
            scalar = np.full((h, w), float(arr[0, 0]), dtype=np.float64)
            return palette[idx], scalar

        rx = (np.arange(cell_subdiv, dtype=np.float64) + 0.5) / cell_subdiv
        ry = (np.arange(cell_subdiv, dtype=np.float64) + 0.5) / cell_subdiv
        rxg, ryg = np.meshgrid(rx, ry, indexing="xy")
        rxg = rxg[None, None, :, :]
        ryg = ryg[None, None, :, :]

        s1 = arr[:-1, :-1][:, :, None, None]
        s2 = arr[:-1, 1:][:, :, None, None]
        s3 = arr[1:, :-1][:, :, None, None]
        s4 = arr[1:, 1:][:, :, None, None]
        sampled = s1 + (s2 - s1) * rxg + (s3 - s1) * ryg + (s1 - s2 - s3 + s4) * rxg * ryg
        scalar = sampled.transpose(0, 2, 1, 3).reshape(h, w)

        bins_desc = diap[1 : pal_size + 1]
        bins_asc = bins_desc[::-1]
        idx = np.digitize(scalar, bins_asc, right=True)
        idx = np.clip(idx, 0, pal_size - 1)
        idx = (pal_size - 1) - idx
        return palette[idx], scalar

    def update_isolines(
        self,
        plot: pg.PlotWidget,
        existing_items: list[pg.IsocurveItem],
        *,
        arr: np.ndarray,
        mode: str,
        stride: int,
        width: int,
        palette_name: str,
        current_field: str,
        scene_dims: tuple[float, float],
    ) -> list[pg.IsocurveItem]:
        for item in existing_items:
            plot.removeItem(item)
        existing_items.clear()
        if mode == "off":
            return existing_items

        iso_data = np.ascontiguousarray(arr.T)
        ih, iw = iso_data.shape
        zmin = float(np.min(arr))
        zmax = float(np.max(arr))
        if abs(zmax - zmin) < 1e-12:
            return existing_items

        pal_size = 21
        levels = self.build_diap(zmin, zmax, pal_size, current_field)[1 : pal_size + 1]
        levels = levels[:: max(1, int(stride))]
        palette = self.active_palette(palette_name)
        scene_nx, scene_nz = scene_dims
        sx = scene_nx / max(1, (ih - 1))
        sy = scene_nz / max(1, (iw - 1))
        pen_w = float(max(1, int(width)))

        for idx, level in enumerate(levels):
            pal_idx = min(idx * max(1, int(stride)), pal_size - 1)
            rgb = tuple(int(v) for v in palette[pal_idx])
            iso = pg.IsocurveItem(level=float(level), pen=pg.mkPen(rgb, width=pen_w))
            iso.setData(iso_data)
            iso.setPos(0.0, 0.0)
            iso.setTransform(QtGui.QTransform.fromScale(sx, sy), False)
            iso.setZValue(20)
            plot.addItem(iso)
            existing_items.append(iso)
        return existing_items

    def update_scene_layout(
        self,
        plot: pg.PlotWidget,
        *,
        scene_dims: tuple[float, float],
        layer_boundaries: np.ndarray | None,
        layer_lines: list[pg.InfiniteLine],
        layer_labels: list[pg.TextItem],
    ) -> tuple[list[pg.InfiniteLine], list[pg.TextItem]]:
        """Обновляет viewport камеры и оверлеи слоёв при смене scene_dims."""
        for line in layer_lines:
            plot.removeItem(line)
        for label in layer_labels:
            plot.removeItem(label)

        scene_nx, scene_nz = scene_dims
        plot.getViewBox().setRange(rect=QtCore.QRectF(0.0, 0.0, scene_nx, scene_nz), padding=0.02)

        layer_lines = []
        layer_labels = []
        if layer_boundaries is None or layer_boundaries.size == 0:
            return layer_lines, layer_labels

        full = np.concatenate(([0.0], layer_boundaries, [scene_nz]))
        for y in layer_boundaries:
            line = pg.InfiniteLine(pos=float(y), angle=0, pen=pg.mkPen((20, 20, 20), width=1))
            plot.addItem(line)
            layer_lines.append(line)
        for idx in range(len(full) - 1):
            y_mid = float((full[idx] + full[idx + 1]) / 2.0)
            label = pg.TextItem(text=f"h{idx + 1}", color=(0, 0, 0), anchor=(0, 0.5))
            label.setPos(scene_nx + 0.5, y_mid)
            plot.addItem(label)
            layer_labels.append(label)
        return layer_lines, layer_labels

    def update_legend(self, label: QtWidgets.QLabel, *, palette_name: str) -> None:
        palette = self.active_palette(palette_name)
        grad = np.repeat(palette[np.newaxis, :, :], 20, axis=0)
        image = QtGui.QImage(
            grad.data,
            grad.shape[1],
            grad.shape[0],
            grad.shape[1] * 3,
            QtGui.QImage.Format.Format_RGB888,
        )
        pixmap = QtGui.QPixmap.fromImage(image.copy()).scaled(
            label.width() or 320,
            20,
            QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
        )
        label.setPixmap(pixmap)

    def field_title(self, current_field: str) -> str:
        if current_field == "P":
            return "Pressure distribution P"
        return f"{current_field} saturation distribution"
