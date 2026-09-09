# AIUsageTracker v0.4.1 verification

Reviewed on Windows 11 with Python 3.13.15, CustomTkinter 6.0.0 and PyInstaller 6.22.2. Downloads are unsigned.

## Local checks

- 27 tests pass. Coverage includes response parsing, reset detection, themes, icons, demo isolation, release metadata and a read-only SQLite regression.
- Dependency checking found no known advisories in the 19-package pinned runtime set. This is a point-in-time check, not a security guarantee.
- Both provider clients completed real HTTP requests against a loopback test server using synthetic tokens. Missing and expired tokens made no request.
- Source GUI checks ran on a private Windows desktop. Refresh, quota alarm toggles, Activity filtering, invalid interval feedback, theme changes, mini mode and reset-banner acknowledgement passed.
- The source demo was exercised with live settings/storage, token scanning, tray startup and notification paths replaced by fail-fast guards. No guard was reached and no Tk callback error was recorded.
- The packaged EXE launched in four demo states and closed cleanly. The test used an isolated profile and created no application-data directory.
- The actual installer was installed silently into a new review directory with no existing installation present. The installed executable and both notice files matched the release inputs. Its four demo states were captured, then the test installation was uninstalled and its registration checked for removal.

The README uses the installed application's dashboard, Activity, Daylight and Settings captures. Every earlier capture is retained in the [concept archive](../assets/concepts/2026-09-08-marketing/README.md).

Local document checks found no broken file links. The README was rendered at desktop and narrow widths in dark and light review themes. Original-file and selected-image hashes match their archive records. The retained logo was checked at sizes from 16 to 256 pixels on dark and light surfaces.

## Reproduce the GUI check

Install development requirements first. Run on Windows from the source checkout:

```powershell
.\.venv\Scripts\python.exe tools/capture_demo.py --output C:/Temp/AIUsageTracker-review
.\.venv\Scripts\python.exe tools/capture_demo.py --output C:/Temp/AIUsageTracker-package-review --executable dist/AIUsageTracker.exe
```

The helper creates a separate desktop and refuses the interactive desktop. It captures the application's own window with DPI awareness, not the user's monitor. Output includes screenshots and a result record. Use a new output folder to preserve previous attempts.

## Not verified here

This release check didn't access live Claude or Codex accounts. Current provider endpoint availability, account entitlement behavior and token rotation weren't exercised. Neither were real audio playback, Windows toasts, live tray interaction, webhooks, event commands, autostart or additional live accounts.

The executable's file-version resource is 0.4.1. It isn't Authenticode signed, and no claim is made that Windows reputation warnings will be absent. GitHub's separate social-preview setting wasn't changed.

The token summary remains approximate. Current source limitations and data access are documented in the [guide](../GUIDE.md), not hidden by the demo.
