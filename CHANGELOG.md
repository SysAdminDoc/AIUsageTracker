# Changelog

All notable changes to AIUsageTracker are documented here.

## [Unreleased]

### Added
- New AIUsageTracker brand mark: interlocking coral and cyan quota arcs around a
  mint status node, designed to remain legible from the sidebar down to 16px.
- Appearance choices in Settings: Midnight, Graphite, and a high-contrast
  Daylight theme, all applied without restarting the app.

### Changed
- Reimagined the desktop dashboard as a responsive usage command center with a
  compact navigation rail, insight strip, brand-edged provider panels, clearer
  percentage-used quota rows, square bell controls, and a summary/activity band.
- Replaced the previous Catppuccin surface treatment with a higher-contrast
  navy, coral, cyan, and mint palette and matching dark Windows title bar.
- Replaced the old gauge icon across the window, sidebar, taskbar, tray, and
  packaged executable with the new generated app logo.
- Improved everyday usability with refresh-in-progress feedback, tooltips for
  icon-only controls, single-instance Settings, keyboard shortcuts, inline poll
  interval validation, and actionable sign-in/error guidance.

### Fixed
- The dashboard no longer overflows horizontally at its default window size.
- Provider panels now share a consistent height when their window counts differ.
- Repeated live theme changes no longer race delayed Tk callbacks or destroy a
  newly opened Settings window.

## [0.3.0] - 2026-07-18

Intelligence, integration, and reliability pass.

### Added
- **Dynamic tray icon** — shows highest usage % with severity-colored background
  (green/yellow/orange/red) updating every poll cycle.
- **Burn-rate forecast** — estimates time until limit based on rolling utilization
  rate of change, displayed in the Highest Pressure insight.
- **Event hooks** — configurable shell commands fired on reset and threshold events
  with AIU_* environment variables (provider, window, utilization).
- **Usage sparklines** — inline 120x20px trend chart in each LimitRow showing last
  24h of utilization readings from persisted history.
- **Historical usage persistence** — every poll appends to `usage_history.jsonl`
  with 30-day auto-pruning on startup.
- **Alert aggregation** — resets within 5s are grouped into one alarm/toast/banner.
- **Data freshness indicator** — topbar shows live "Synced Xs ago" with STALE
  warning when poll exceeds 2x the configured interval.
- **Status export** — `current_status.json` updated each poll with all window data
  for external agents/scripts to read.
- **Discord/Telegram webhook** — configurable webhook URL for remote reset alerts.
- **Autostart on login** — creates a Windows Startup folder shortcut.
- **Source health check** — logs a warning when an endpoint stops returning
  `resets_at` (schema drift detection).
- **Snooze button** — suppresses alarm for snoozed windows until their next reset.
- **Per-window warn thresholds** — override the global `warn_toast_at` per window.
- **Custom alarm sound** — set `alarm_sound_name` to "Custom" and provide a path.
- **Animated progress bars** — 300ms fill-in animation when usage rows render.

### Changed
- Migrated HTTP client from httpx (abandoned upstream) to httpx2 (Pydantic fork).
- Removed plyer dependency (unmaintained); notifications use windows-toasts only.
- Pinned Pillow >= 12.3.0 (addresses 7 CVEs from 2026).
- Optimized PyInstaller build with aggressive module exclusions for smaller exe.

## [0.2.0] - 2026-07-17

Premium polish pass + brand identity + selectable alarm sounds.

### Added
- **Provider brand tiles** — original geometric Claude (clay sunburst) and Codex
  (OpenAI hexafoil) marks rendered at runtime with 4x supersampling; shown in the
  provider card headers and the activity feed. New app/tray gauge mark.
- **Selectable alarm sounds** — six synthesized, loopable tones (Chime, Alert, Pulse,
  Bell, Siren, Arcade) chosen from a Settings dropdown, with a *Test* preview button.

### Changed
- Full premium visual pass: design-token system (spacing, typography, radius, border
  scales), subtle card borders/elevation, brand-aligned accents, severity edge on each
  usage bar, refined summary cards, and clearer status text.
- Settings redesigned into Providers / Alerts / General sections with per-setting
  hints, a scrollable body, and sticky Save / Cancel actions.
- Microcopy polish across empty, error, and connection states.

### Fixed
- Usage rows no longer stretch to CTkFrame's 200px default height (severity edge given
  a tiny requested height so rows size to their real content).

## [0.1.0] - 2026-07-17

Initial release.

### Added
- Live monitoring of Claude (`api.anthropic.com/api/oauth/usage`) and Codex
  (`chatgpt.com/backend-api/wham/usage`) usage windows via reused local CLI OAuth
  tokens — no scraping, no passwords, no browser automation.
- Timestamp-driven reset detection with a precise one-shot poll scheduled at each
  window's `resets_at` boundary.
- Reset alarm: looping audible tone (synthesized WAV), native Windows toast, and an
  in-app red banner with a *Stop alarm* button.
- Per-bar alarm toggles — enable/disable the alarm independently for each usage
  window, persisted to settings.
- customtkinter GUI (Catppuccin Mocha) with live usage bars, severity coloring,
  countdowns, exact local reset times, and provider plan badges.
- System tray integration (Show / Poll now / Settings / Quit); window hides to tray
  on close.
- Settings dialog: poll interval, provider toggles, alarm/toast options, start
  minimized.
- Headless CLI: `poll` (one-shot) and `monitor` (reset watcher).
- Reset-event history log at `%APPDATA%\AIUsageTracker\reset_events.jsonl`.
- Unit tests for parsing (real endpoint shapes) and reset detection.
- PyInstaller build script producing an unsigned single-file exe.
