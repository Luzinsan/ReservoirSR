from __future__ import annotations

import sys
from pathlib import Path

from hydra import compose, initialize_config_dir
from PySide6 import QtWidgets

from reservoir_sr.app.app_context import AppContext
from reservoir_sr.app.main_window import MainWindow

_CONF_DIR = Path(__file__).resolve().parent.parent / "conf" / "gui"


def main() -> int:
    with initialize_config_dir(version_base="1.3", config_dir=str(_CONF_DIR)):
        cfg = compose(config_name="default")
    
    app = QtWidgets.QApplication(sys.argv)
    context = AppContext.from_hydra(cfg)
    window = MainWindow(context=context, window_cfg=cfg.window)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
