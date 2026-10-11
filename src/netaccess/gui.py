from __future__ import annotations

import time
from PySide6.QtCore import QObject, QThread, QTimer, Signal, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPushButton, QSystemTrayIcon, QMenu, QVBoxLayout, QWidget,
)

from .auth import PortalConfig, check_status, login
from .autostart import set_enabled as set_autostart
from .connectivity import portal_reachable
from .credentials import delete_password, get_password, save_password
from .settings import settings


class Task(QObject):
    finished = Signal(str, object)

    def __init__(self, action: str, config: PortalConfig, username: str, password: str):
        super().__init__()
        self.action, self.config = action, config
        self.username, self.password = username, password

    def run(self):
        if self.action == "status":
            result = check_status(self.config)
        elif self.action == "auto":
            if not portal_reachable(self.config.login_url):
                from .auth import AuthResult
                result = AuthResult("unknown", "Portal is not reachable yet. Will retry when the network is ready.")
            else:
                result = check_status(self.config)
                if result.outcome == "authenticated":
                    pass
                elif self.username and self.password:
                    result = login(self.config, self.username, self.password)
                else:
                    from .auth import AuthResult
                    result = AuthResult("unknown", "No saved credentials. Enter them and save to the system keyring.")
        else:
            result = login(self.config, self.username, self.password)
        self.finished.emit(self.action, result)


class MainWindow(QMainWindow):
    def __init__(self, background: bool = False):
        super().__init__()
        self.setWindowTitle("NetAccess Desktop")
        self.setMinimumWidth(520)
        self._thread: QThread | None = None
        self._task: Task | None = None
        self._retry_delay = 30
        self._last_auto_login = 0.0
        self._quit_requested = False
        self._busy = False
        self._startup_background = background
        self.settings = settings()

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        heading = QLabel("NetAccess Desktop")
        heading.setStyleSheet("font-size: 22px; font-weight: 700;")
        root.addWidget(heading)
        root.addWidget(QLabel("Campus portal authentication · Credentials stored in your OS keyring"))

        form = QFormLayout()
        self.username = QLineEdit(self.settings.value("username", ""))
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Leave blank to use saved keyring password")
        self.login_url = QLineEdit(self.settings.value("login_url", "https://netaccess.iitism.ac.in:6082/"))
        self.status_url = QLineEdit(self.settings.value("status_url", "https://netaccess.iitism.ac.in:6082/"))
        self.username_field = QLineEdit(self.settings.value("username_field", "username"))
        self.password_field = QLineEdit(self.settings.value("password_field", "password"))
        self.success_markers = QLineEdit(self.settings.value("success_markers", "logout,log out,sign out"))
        self.failure_markers = QLineEdit(self.settings.value("failure_markers", "invalid username,invalid password,authentication failed,incorrect password,login failed"))
        form.addRow("LDAP username", self.username)
        form.addRow("LDAP password", self.password)
        form.addRow("Login URL", self.login_url)
        form.addRow("Status URL", self.status_url)
        form.addRow("Username form field", self.username_field)
        form.addRow("Password form field", self.password_field)
        form.addRow("Signed-in markers (comma separated)", self.success_markers)
        form.addRow("Failure markers (comma separated)", self.failure_markers)
        root.addLayout(form)

        self.save_credentials = QCheckBox("Save password in system keyring")
        self.save_credentials.setChecked(True)
        self.auto_login = QCheckBox("Attempt login automatically when the app starts / network returns")
        self.auto_login.setChecked(self.settings.value("auto_login", True, type=bool))
        self.auto_start = QCheckBox("Launch app when I sign in to this computer")
        self.auto_start.setChecked(self.settings.value("auto_start", False, type=bool))
        root.addWidget(self.save_credentials)
        root.addWidget(self.auto_login)
        root.addWidget(self.auto_start)

        buttons = QHBoxLayout()
        self.connect_button = QPushButton("Connect / Login")
        self.status_button = QPushButton("Check status")
        self.forget_button = QPushButton("Forget saved password")
        buttons.addWidget(self.connect_button)
        buttons.addWidget(self.status_button)
        root.addLayout(buttons)
        root.addWidget(self.forget_button)

        self.status_label = QLabel("Ready. Configure the portal fields if the defaults do not match.")
        self.status_label.setWordWrap(True)
        self.status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.status_label.setStyleSheet("padding: 12px; border-radius: 8px; background: palette(alternate-base);")
        root.addWidget(self.status_label)
        self.setCentralWidget(central)

        self.connect_button.clicked.connect(self.connect_now)
        self.status_button.clicked.connect(self.check_now)
        self.forget_button.clicked.connect(self.forget_password)
        self.auto_start.toggled.connect(self.toggle_autostart)
        self.auto_login.toggled.connect(lambda _: self.persist_settings())

        self.tray = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon), self)
            self.tray.setToolTip("NetAccess Desktop")
            menu = QMenu()
            show_action = QAction("Open NetAccess Desktop", self)
            show_action.triggered.connect(self.showNormal)
            connect_action = QAction("Connect / Login", self)
            connect_action.triggered.connect(self.connect_now)
            quit_action = QAction("Quit", self)
            quit_action.triggered.connect(self.quit_app)
            menu.addAction(show_action)
            menu.addAction(connect_action)
            menu.addSeparator()
            menu.addAction(quit_action)
            self.tray.setContextMenu(menu)
            self.tray.activated.connect(lambda reason: self.showNormal() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
            self.tray.show()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.background_check)
        self.timer.start(30_000)

        if background and self.tray:
            self.hide()
        if self.auto_login.isChecked():
            QTimer.singleShot(1200, self.auto_connect)

    def config(self) -> PortalConfig:
        return PortalConfig(
            login_url=self.login_url.text().strip(),
            status_url=self.status_url.text().strip(),
            username_field=self.username_field.text().strip(),
            password_field=self.password_field.text().strip(),
            success_markers=tuple(x.strip() for x in self.success_markers.text().split(",") if x.strip()),
            failure_markers=tuple(x.strip() for x in self.failure_markers.text().split(",") if x.strip()),
        )

    def persist_settings(self):
        for key, value in {
            "username": self.username.text().strip(),
            "login_url": self.login_url.text().strip(),
            "status_url": self.status_url.text().strip(),
            "username_field": self.username_field.text().strip(),
            "password_field": self.password_field.text().strip(),
            "success_markers": self.success_markers.text(),
            "failure_markers": self.failure_markers.text(),
            "auto_login": self.auto_login.isChecked(),
            "auto_start": self.auto_start.isChecked(),
        }.items():
            self.settings.setValue(key, value)
        self.settings.sync()

    def toggle_autostart(self, enabled: bool):
        try:
            set_autostart(enabled)
            self.persist_settings()
            self.status_label.setText("Startup launch enabled." if enabled else "Startup launch disabled.")
        except Exception as exc:
            self.auto_start.blockSignals(True)
            self.auto_start.setChecked(not enabled)
            self.auto_start.blockSignals(False)
            QMessageBox.warning(self, "Startup setting failed", str(exc))

    def current_password(self) -> str:
        typed = self.password.text()
        if typed:
            if self.save_credentials.isChecked():
                save_password(self.username.text().strip(), typed)
            return typed
        return get_password(self.username.text().strip()) or ""

    def launch_task(self, action: str, password: str = ""):
        if self._busy:
            return
        self.persist_settings()
        username = self.username.text().strip()
        try:
            config = self.config()
            config.validate()
        except ValueError as exc:
            self.status_label.setText(str(exc))
            return
        if action != "status" and (not username or not password):
            self.status_label.setText("Enter your LDAP username and password, or save a password in the system keyring.")
            return
        self._busy = True
        self.connect_button.setEnabled(False)
        self.status_button.setEnabled(False)
        self.status_label.setText("Working…")
        self._thread = QThread(self)
        self._task = Task(action, config, username, password)
        self._task.moveToThread(self._thread)
        self._thread.started.connect(self._task.run)
        self._task.finished.connect(self.on_task_finished)
        self._task.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._task.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def connect_now(self):
        try:
            password = self.current_password()
        except Exception as exc:
            self.status_label.setText(f"Could not access system keyring: {exc}")
            return
        self.launch_task("login", password)

    def auto_connect(self):
        if not self.auto_login.isChecked():
            return
        try:
            password = self.current_password()
        except Exception as exc:
            self.status_label.setText(f"System keyring unavailable: {exc}")
            return
        if not self.username.text().strip() or not password:
            self.status_label.setText("Automatic login is enabled, but credentials are not saved. Enter them once and save to keyring.")
            return
        self.launch_task("auto", password)

    def check_now(self):
        self.launch_task("status")

    def background_check(self):
        if self._busy or not self.auto_login.isChecked():
            return
        # Do not submit credentials every 30 seconds. Only retry after an explicit
        # unauthenticated response; ambiguous portal responses wait for user action.
        self.launch_task("status")

    def on_task_finished(self, action: str, result):
        self._busy = False
        self.connect_button.setEnabled(True)
        self.status_button.setEnabled(True)
        self.status_label.setText(
            f"{result.outcome.upper()}: {result.message}\n"
            f"HTTP: {result.status_code if result.status_code is not None else 'n/a'}\n"
            f"URL: {result.final_url or 'n/a'}"
        )
        if self.tray:
            self.tray.showMessage("NetAccess Desktop", result.message, QSystemTrayIcon.MessageIcon.Information, 4000)
        if action == "status" and result.outcome == "unauthenticated" and self.auto_login.isChecked():
            # Small cooldown/backoff prevents aggressive login attempts.
            now = time.monotonic()
            if now - self._last_auto_login >= self._retry_delay:
                self._last_auto_login = now
                self._retry_delay = min(self._retry_delay * 2, 300)
                QTimer.singleShot(1500, self.auto_connect)
        elif result.outcome == "authenticated":
            self._retry_delay = 30

    def forget_password(self):
        username = self.username.text().strip()
        if not username:
            return
        try:
            delete_password(username)
            self.password.clear()
            self.status_label.setText("Saved password removed from the system keyring.")
        except Exception as exc:
            QMessageBox.warning(self, "Could not remove password", str(exc))

    def quit_app(self):
        self._quit_requested = True
        if self.tray:
            self.tray.hide()
        self.close()
        QApplication.quit()

    def closeEvent(self, event):
        if self.tray and self.tray.isVisible() and not self._quit_requested:
            self.hide()
            event.ignore()
            return
        event.accept()
        if not self.tray:
            QApplication.quit()
