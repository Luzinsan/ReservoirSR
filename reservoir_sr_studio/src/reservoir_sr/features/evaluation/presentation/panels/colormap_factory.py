from __future__ import annotations

import numpy as np
import pyqtgraph as pg


def _geographical_lut(n: int = 256) -> np.ndarray:
    """LUT 256×4 (RGBA uint8) — geographical palette."""
    third = n // 3
    lut = np.zeros((n, 4), dtype=np.uint8)
    lut[:, 3] = 255  # alpha

    def _fill(start: int, count: int, r: tuple, g: tuple, b: tuple) -> None:
        for i in range(count):
            t = i / max(count - 1, 1)
            lut[start + i, 0] = int(r[0] + (r[1] - r[0]) * t)
            lut[start + i, 1] = int(g[0] + (g[1] - g[0]) * t)
            lut[start + i, 2] = int(b[0] + (b[1] - b[0]) * t)

    _fill(0, third, (103, 114), (237, 103), (255, 255))
    _fill(third, third, (207, 63), (247, 141), (186, 16))
    _fill(2 * third, n - 2 * third, (237, 97), (231, 81), (207, 37))
    return lut


def _linear_lut(c1: tuple[int, int, int], c2: tuple[int, int, int], n: int = 256) -> np.ndarray:
    lut = np.zeros((n, 4), dtype=np.uint8)
    lut[:, 3] = 255
    for k in range(3):
        lut[:, k] = np.linspace(c1[k], c2[k], n, dtype=np.float32).astype(np.uint8)
    return lut


def _hot_lut(n: int = 256) -> np.ndarray:
    """matplotlib-like 'hot' colormap: black → red → yellow → white."""
    lut = np.zeros((n, 4), dtype=np.uint8)
    lut[:, 3] = 255
    third = n // 3
    # 0..third: black → red
    lut[:third, 0] = np.linspace(0, 255, third, dtype=np.uint8)
    # third..2/3: red+green ramp
    lut[third:2 * third, 0] = 255
    lut[third:2 * third, 1] = np.linspace(0, 255, third, dtype=np.uint8)
    # 2/3..n: yellow → white
    rest = n - 2 * third
    lut[2 * third:, 0] = 255
    lut[2 * third:, 1] = 255
    lut[2 * third:, 2] = np.linspace(0, 255, rest, dtype=np.uint8)
    return lut


# Build once at module import — these are constants.
LUT_GEOGRAPHICAL = _geographical_lut()
LUT_WATER_OIL = _linear_lut((94, 94, 94), (120, 255, 255))
LUT_HOT = _hot_lut()

# (channel_name) → LUT for LR/HR/SR
CHANNEL_LUTS: dict[str, np.ndarray] = {
    "P": LUT_GEOGRAPHICAL,
    "ST": LUT_WATER_OIL,
    "SB": LUT_WATER_OIL,
}

# LUT for diff column
DIFF_LUT = LUT_HOT