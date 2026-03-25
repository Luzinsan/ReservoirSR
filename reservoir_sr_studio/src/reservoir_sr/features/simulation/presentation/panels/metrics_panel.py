from __future__ import annotations

import pyqtgraph as pg
from PySide6 import QtWidgets


class MetricsPanel(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)

        self.plot = pg.PlotWidget(title="AI / AIT / AIB")
        self.plot.addLegend()
        self.curve_ai = self.plot.plot(name="AI", pen="r")
        self.curve_ait = self.plot.plot(name="AIT", pen="g")
        self.curve_aib = self.plot.plot(name="AIB", pen="b")
        layout.addWidget(self.plot)
