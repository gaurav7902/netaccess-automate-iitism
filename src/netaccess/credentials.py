"""OS-backed credential storage using Python keyring."""
import keyring

SERVICE_NAME = "netaccess-desktop"


def save_password(username: str, password: str) -> None:
    keyring.set_password(SERVICE_NAME, username, password)


def get_password(username: str) -> str | None:
    return keyring.get_password(SERVICE_NAME, username)


def delete_password(username: str) -> None:
    try:
        keyring.delete_password(SERVICE_NAME, username)
    except keyring.errors.PasswordDeleteError:
        pass
