import argparse
import sys
from PySide6.QtWidgets import QApplication

if __package__:
    from .gui import MainWindow
else:
    from netaccess.gui import MainWindow


def main():
    parser = argparse.ArgumentParser(description="NetAccess Desktop")
    parser.add_argument("--background", action="store_true", help="Start minimized to the system tray")
    args, qt_args = parser.parse_known_args()
    app = QApplication([sys.argv[0], *qt_args])
    app.setApplicationName("NetAccess Desktop")
    app.setOrganizationName("NetAccessDesktop")
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow(background=args.background)
    if not args.background:
        window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
