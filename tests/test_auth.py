from netaccess.auth import PortalConfig, _classify


def test_classifies_success_marker():
    config = PortalConfig(success_markers=("logout",), failure_markers=("invalid password",))
    assert _classify("<a>Logout</a>", config) == "authenticated"


def test_classifies_failure_marker():
    config = PortalConfig(success_markers=("logout",), failure_markers=("invalid password",))
    assert _classify("Invalid password", config) == "unauthenticated"


def test_unknown_when_no_marker_matches():
    config = PortalConfig(success_markers=("logout",), failure_markers=("invalid password",))
    assert _classify("Welcome", config) == "unknown"


def test_rejects_non_https_url():
    config = PortalConfig(login_url="http://example.com", status_url="https://example.com")
    try:
        config.validate()
    except ValueError:
        pass
    else:
        raise AssertionError("Expected non-HTTPS URL to be rejected")
