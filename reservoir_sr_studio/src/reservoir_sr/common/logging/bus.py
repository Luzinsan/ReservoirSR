from __future__ import annotations

from PySide6 import QtCore


class LogBus(QtCore.QObject):
    message_logged = QtCore.Signal(str)

    def publish(self, message: str) -> None:
        self.message_logged.emit(message)
