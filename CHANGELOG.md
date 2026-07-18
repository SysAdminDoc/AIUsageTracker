# Changelog

All notable changes to AIUsageTracker are documented here.

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
