"""Network readiness checks that work across operating systems."""
from urllib.parse import urlparse
import socket


def portal_reachable(url: str, timeout: float = 3.0) -> bool:
    parsed = urlparse(url)
    if not parsed.hostname:
        return False
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((parsed.hostname, port), timeout=timeout):
            return True
    except OSError:
        return False
