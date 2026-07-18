# AIUsageTracker

[![version](https://img.shields.io/badge/version-0.3.0-cba6f7)](https://github.com/SysAdminDoc/AIUsageTracker/releases)
[![license](https://img.shields.io/badge/license-MIT-a6e3a1)](LICENSE)
[![platform](https://img.shields.io/badge/platform-Windows-89b4fa)](https://github.com/SysAdminDoc/AIUsageTracker)
[![python](https://img.shields.io/badge/python-3.10%2B-fab387)](https://www.python.org/)

A Windows desktop widget that tracks your **Claude** (claude.ai / Claude Code) and
**OpenAI Codex** usage windows in real time — and fires an **alarm the instant a
usage window resets**, so you never have to sit refreshing the usage pages again.

A dark, dashboard-style desktop app: a sidebar (Dashboard / Activity), summary cards
(highest usage, next reset, connections), side-by-side Claude and Codex cards with
per-window usage bars and alarm toggles, and a recent-activity feed.

## Why

Claude and Codex both cap you with rolling usage windows (a ~5-hour session limit,
weekly limits, per-model limits). Those windows reset at times that drift and are
easy to miss — the only way to check is to keep opening:

- `https://claude.ai/new#settings/usage`
- `https://chatgpt.com/codex/cloud/settings/analytics`

AIUsageTracker reads the same numbers those pages show, in the background, and
**alarms you the moment a window rolls over** so you can jump back to work
immediately.

## How it works (no scraping, no passwords)

Both providers expose an authenticated JSON usage endpoint that returns explicit
reset timestamps. AIUsageTracker reuses the OAuth tokens the official CLIs already
store on your machine — it **never** asks for your password and **never** drives a
browser:

| Provider | Source | Token file (read fresh each poll) |
|----------|--------|-----------------------------------|
| Claude   | `GET api.anthropic.com/api/oauth/usage` | `~/.claude/.credentials.json` |
| Codex    | `GET chatgpt.com/backend-api/wham/usage` | `~/.codex/auth.json` |

Reset detection is **timestamp-driven**: each window reports a `resets_at`, and the
app fires when that timestamp rolls forward (with a precise one-shot poll scheduled
right at each boundary so the alarm is near-instant, not up to a poll-interval late).

> **Token safety:** Claude/Codex refresh tokens rotate. AIUsageTracker deliberately
> **does not** refresh them itself — doing so could invalidate the token the CLIs are
> actively using. It reads the files fresh each poll (the CLIs keep them current) and
> just shows a *"login expired — open Claude Code / run codex"* status if a token goes
> stale. Your credentials are never modified or transmitted anywhere except the
> provider's own usage endpoint.

## Requirements

- Windows 10/11
- **Claude Code** and/or **Codex CLI** installed and logged in (that's where the
  tokens come from). If you only use one, the other simply shows *no credentials*.
- For running from source: Python 3.10+

## Install / Run

### Prebuilt exe
Download `AIUsageTracker.exe` from the [Releases](https://github.com/SysAdminDoc/AIUsageTracker/releases)
page and run it. It lives in the system tray; closing the window hides it there.

### From source
```powershell
git clone https://github.com/SysAdminDoc/AIUsageTracker
cd AIUsageTracker
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

### Headless (no GUI)
```powershell
python -m aiusagetracker.cli poll      # print current usage once
python -m aiusagetracker.cli monitor   # run the reset watcher in the terminal
```

## Features

- **Live usage bars** for every Claude & Codex limit window (5-hour session, weekly,
  per-model), colored by severity (green / yellow / red).
- **Reset alarm** — audible alarm + native Windows toast + a red in-app banner the
  moment a window resets. Choose from six built-in alarm tones (Chime, Alert, Pulse,
  Bell, Siren, Arcade) and preview them from Settings.
- **Per-bar alarm toggles** — enable/disable the alarm independently for each usage
  window. Only the windows you care about will wake you.
- **Brand-aware dashboard** — Claude and Codex provider cards, summary metrics
  (highest usage, next reset, connections), and a recent-activity feed.
- **Distinct app identity** — a purpose-built quota-cycle mark shared by the
  window, taskbar, system tray, and packaged executable.
- **Live countdowns** to each reset, plus the exact local reset time.
- **System tray** — runs quietly in the background; Show / Poll now / Settings / Quit.
- **Reset history** — every detected reset is logged to
  `%APPDATA%\AIUsageTracker\reset_events.jsonl`.
- **Three appearance themes** — Midnight, Graphite, and Daylight, applied live
  after saving Settings.

## Settings

Gear → **Settings**. Stored in `%APPDATA%\AIUsageTracker\settings.json`.

| Setting | Default | Notes |
|---------|---------|-------|
| Poll interval | 180s | Minimum 180s (Claude's endpoint rate-limits faster polling). |
| Track Claude / Codex | on | Disable a provider you don't use. |
| Audible alarm on reset | on | Master switch for the sound. |
| Alarm sound | Chime | Pick from Chime / Alert / Pulse / Bell / Siren / Arcade; *Test* previews it. |
| Loop alarm until acknowledged | on | Repeat the tone until you click *Stop alarm*. |
| Toast notifications | on | Native Windows toasts. |
| Start minimized to tray | off | Launch straight to the tray. |
| Per-window alarm | on | Toggled from the button on each usage bar. |
| Theme | Midnight | Choose Midnight, Graphite, or Daylight; applies immediately. |

## Build the exe

```powershell
.\build.ps1
```
Produces an unsigned `dist\AIUsageTracker.exe` (single-file, windowed).

## Notes & caveats

- The usage endpoints are **undocumented**. If a provider changes them, a source
  will stop returning data and its section will show an error — open an issue.
- This is an unofficial tool, not affiliated with Anthropic or OpenAI.

## License

MIT — see [LICENSE](LICENSE).
