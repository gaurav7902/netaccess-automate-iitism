# Contributing

Thanks for helping improve NetAccess Desktop.

1. Open an issue before large changes so scope and portal behavior can be discussed.
2. Use Python 3.10+ and keep the authentication protocol isolated in `src/netaccess/auth.py`.
3. Never commit credentials, cookies, session dumps, or unredacted portal traces.
4. Add or update tests for changes, then run `pytest`.
5. Keep cross-platform startup changes in `src/netaccess/autostart/` and test on the target OS.
6. Do not claim login success based only on HTTP status code; document the portal evidence used.

Pull requests should describe the change, operating systems tested, and any limitations.
