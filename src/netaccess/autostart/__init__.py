"""Per-user launch-at-login integration."""
import sys
from pathlib import Path
from platformdirs import user_config_dir, user_data_dir

APP_NAME = "netaccess-desktop"


def set_enabled(enabled: bool) -> None:
    if sys.platform.startswith("linux"):
        _linux(enabled)
    elif sys.platform == "win32":
        _windows(enabled)
    elif sys.platform == "darwin":
        _macos(enabled)
    else:
        raise RuntimeError(f"Autostart is not supported on {sys.platform}.")


def _command() -> str:
    # Packaged builds use the executable; source/dev installs use the module.
    exe = Path(sys.executable).resolve()
    if getattr(sys, "frozen", False):
        return f'"{exe}" --background'
    return f'"{exe}" -m netaccess.main --background'


def _linux(enabled: bool) -> None:
    path = Path(user_config_dir("", "")) / "autostart" / f"{APP_NAME}.desktop"
    if enabled:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "[Desktop Entry]\nType=Application\nName=NetAccess Desktop\n"
            f"Exec={_command()}\nX-GNOME-Autostart-enabled=true\n"
            "Terminal=false\nStartupNotify=false\n",
            encoding="utf-8",
        )
        path.chmod(0o600)
    else:
        path.unlink(missing_ok=True)


def _windows(enabled: bool) -> None:
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, "NetAccessDesktop", 0, winreg.REG_SZ, _command())
        else:
            try:
                winreg.DeleteValue(key, "NetAccessDesktop")
            except FileNotFoundError:
                pass


def _macos(enabled: bool) -> None:
    import plistlib
    path = Path.home() / "Library" / "LaunchAgents" / "org.netaccess.desktop.plist"
    if enabled:
        path.parent.mkdir(parents=True, exist_ok=True)
        if getattr(sys, "frozen", False):
            program = [str(Path(sys.executable).resolve()), "--background"]
        else:
            program = [str(Path(sys.executable).resolve()), "-m", "netaccess.main", "--background"]
        payload = {
            "Label": "org.netaccess.desktop",
            "ProgramArguments": program,
            "RunAtLoad": True,
            "LimitLoadToSessionType": "Aqua",
        }
        path.write_bytes(plistlib.dumps(payload))
        path.chmod(0o600)
    else:
        path.unlink(missing_ok=True)
