"""Portal HTTP adapter. Cookies live only for the duration of each operation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

import requests

Outcome = Literal["authenticated", "unauthenticated", "unknown"]


@dataclass(frozen=True)
class PortalConfig:
    login_url: str = "https://netaccess.iitism.ac.in:6082/"
    status_url: str = "https://netaccess.iitism.ac.in:6082/"
    username_field: str = "username"
    password_field: str = "password"
    success_markers: tuple[str, ...] = ("logout", "log out", "sign out")
    failure_markers: tuple[str, ...] = (
        "invalid username", "invalid password", "authentication failed",
        "incorrect password", "login failed",
    )

    def validate(self) -> None:
        for label, value in (("Login URL", self.login_url), ("Status URL", self.status_url)):
            parsed = urlparse(value)
            if parsed.scheme != "https" or not parsed.hostname:
                raise ValueError(f"{label} must be a valid HTTPS URL.")
        if not self.username_field.strip() or not self.password_field.strip():
            raise ValueError("Form field names cannot be empty.")


@dataclass(frozen=True)
class AuthResult:
    outcome: Outcome
    message: str
    status_code: int | None = None
    final_url: str | None = None


def _classify(body: str, config: PortalConfig) -> Outcome:
    text = body.casefold()
    if any(marker.casefold() in text for marker in config.failure_markers if marker.strip()):
        return "unauthenticated"
    if any(marker.casefold() in text for marker in config.success_markers if marker.strip()):
        return "authenticated"
    return "unknown"


def check_status(config: PortalConfig, timeout: float = 12) -> AuthResult:
    """Check status without persisting cookies; markers are only heuristics."""
    config.validate()
    try:
        with requests.Session() as session:
            response = session.get(config.status_url, timeout=timeout, allow_redirects=True)
            if response.status_code >= 500:
                return AuthResult("unknown", f"Portal returned HTTP {response.status_code}.", response.status_code, response.url)
            outcome = _classify(response.text, config)
            if outcome == "unknown" and response.status_code >= 400:
                return AuthResult("unknown", f"Status check returned HTTP {response.status_code}.", response.status_code, response.url)
            messages = {
                "authenticated": "The response contains a configured signed-in marker; verify it matches the portal.",
                "unauthenticated": "The response contains a configured login/failure marker.",
                "unknown": "Could not determine login state from the response. Configure reliable status markers/URL.",
            }
            return AuthResult(outcome, messages[outcome], response.status_code, response.url)
    except requests.RequestException as exc:
        return AuthResult("unknown", f"Network or portal error: {exc}")


def login(config: PortalConfig, username: str, password: str, timeout: float = 12) -> AuthResult:
    """Submit credentials using the configured form fields.

    The default field names are assumptions based on the initial script. Some
    captive portals require a different endpoint, hidden fields, or a challenge.
    """
    config.validate()
    if not username or not password:
        return AuthResult("unknown", "Enter both username and password.")
    try:
        with requests.Session() as session:
            response = session.post(
                config.login_url,
                data={config.username_field: username, config.password_field: password},
                timeout=timeout,
                allow_redirects=True,
            )
            if response.status_code >= 500:
                return AuthResult("unknown", f"Portal returned HTTP {response.status_code}.", response.status_code, response.url)
            outcome = _classify(response.text, config)
            if outcome == "authenticated":
                message = "Login appears successful based on a configured response marker."
            elif outcome == "unauthenticated":
                message = "Login appears to have failed based on a configured response marker."
            else:
                message = (
                    "Request completed, but authentication is unconfirmed. Configure the actual "
                    "portal endpoint/form fields and reliable response markers. HTTP 200 alone is not proof."
                )
            return AuthResult(outcome, message, response.status_code, response.url)
    except requests.RequestException as exc:
        return AuthResult("unknown", f"Network or portal error: {exc}")
