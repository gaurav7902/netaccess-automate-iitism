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


def test_classifies_by_url_when_marker_is_absent():
    config = PortalConfig(
        success_markers=("logout",),
        failure_markers=("invalid password",),
        success_url_tokens=("/portal/home",),
        failure_url_tokens=("/login",),
    )
    assert _classify("Welcome", config, "https://example.com/portal/home") == "authenticated"
    assert _classify("Welcome", config, "https://example.com/login?error=1") == "unauthenticated"


def test_rejects_non_https_url():
    config = PortalConfig(login_url="http://example.com", status_url="https://example.com")
    try:
        config.validate()
    except ValueError:
        pass
    else:
        raise AssertionError("Expected non-HTTPS URL to be rejected")
