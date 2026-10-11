# NetAccess Desktop

A cross-platform desktop helper for IIT (ISM) Dhanbad NetAccess. It provides a PySide6 GUI, OS keyring-backed password storage, per-user launch-at-login integration, and network-aware status checks/retries.

> **Early alpha / portal integration needs validation.** The default login URL and `username` / `password` form fields come from an initial user-provided script. They are assumptions, not verified portal API documentation. The status URL defaults to the same page, and text markers are heuristics. Do not treat HTTP 200 or a marker match as definitive until validated against the live portal. Inspect the browser Network panel after a manual login and configure the real endpoint, form fields, and status markers in Settings.

## Features

- Linux, Windows, and macOS from one Python codebase.
- Password stored in the operating system's keyring via `keyring` (not in app settings or a cookie file).
- No persistent HTTP cookies: each login/status operation uses a temporary `requests.Session`.
- Optional launch at desktop sign-in.
- Startup login attempt and periodic status checks; only an explicit unauthenticated result triggers automatic re-login. Ambiguous responses do not trigger a rapid retry loop.
- User-configurable login/status URLs, form-field names, and response markers.
- GitHub Actions workflow for platform-specific build artifacts and tagged releases.

## Security notes

- Only use with your own campus credentials and in accordance with campus IT/network policy.
- Do not share the app's logs if they include sensitive URLs or query parameters.
- The app never writes the password to its settings file. If keyring is unavailable, it reports the problem rather than falling back to plaintext storage.
- A saved keyring password enables unattended login, so protect your operating-system account.
- HTTP response markers are not a robust authentication API. Configure and test them carefully. A false positive can cause the app to believe it is signed in when it is not.

## Run from source

Python 3.10+ is recommended.

```bash
git clone https://github.com/YOUR-USER/netaccess-desktop.git
cd netaccess-desktop
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
netaccess-desktop
```

Alternatively install dependencies from `requirements.txt` and run `PYTHONPATH=src python -m netaccess.main` (on Windows PowerShell: `$env:PYTHONPATH='src'; python -m netaccess.main`).

## First run

1. Open the app and enter your LDAP username and password.
2. Leave **Save password in system keyring** enabled if you want unattended login.
3. Verify the login URL and form field names against the actual portal request.
4. Configure a status URL and markers that reliably distinguish signed-in and signed-out pages.
5. Test **Check status** and **Connect / Login** manually before enabling startup.
6. Enable automatic login and launch-at-sign-in when the portal integration has been verified.

The application cannot infer the portal's exact authentication state if the server does not expose a reliable page or status endpoint. Some captive portals require additional hidden form fields, a challenge, a redirect, or a different endpoint; this app intentionally does not guess those fields.

## Build locally

```bash
python -m pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --name NetAccessDesktop --paths src src/netaccess/main.py
```

Artifacts are written under `dist/`. Build separately on Linux, Windows, and macOS; PyInstaller is not a universal cross-compiler.

## GitHub Releases

Push this project to a GitHub repository. The workflow in `.github/workflows/build.yml` builds on all three operating systems for every tag matching `v*`, then attaches platform artifacts to a GitHub Release. To publish a release:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Review the workflow and test artifacts before making a public release.

## Tests

```bash
python -m pip install -e '.[dev]'
pytest
```

## License

MIT. This is an independent community project and is not affiliated with or endorsed by IIT (ISM) Dhanbad.
