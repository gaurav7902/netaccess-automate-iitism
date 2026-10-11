"""Small non-secret settings store."""
from PySide6.QtCore import QSettings


def settings() -> QSettings:
    return QSettings("NetAccessDesktop", "NetAccessDesktop")
