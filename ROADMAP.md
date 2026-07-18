# ROADMAP

Single source of truth for open work. Legend: 🤖 = autonomous-codeable, 🔧 = operator/product-gated.

## Next

- 🤖 **Reset history view** — in-app panel/tab listing past resets from `reset_events.jsonl` with per-window filtering.
- 🤖 **Frameless always-on-top widget mode** — compact desktop widget variant (drag-to-move, opacity, remembers position) in addition to the full window.
- 🤖 **Per-window warn thresholds** — currently a single global `warn_toast_at`; allow a custom threshold per usage bar next to its alarm toggle.
- 🤖 **Custom alarm sound file** — let users point at their own `.wav` in addition to the six built-in tones.
- 🤖 **Autostart on login** — optional Startup-folder / HKCU Run entry toggle in Settings.
- 🤖 **Light theme (Catppuccin Latte)** — the polish pass added a full token system; a light variant is now a small step.
- 🤖 **Focus rings / keyboard-nav pass** — CTk focus visibility is minimal; add visible focus states and verify tab order for accessibility.
- 🤖 **Snooze / one-window acknowledge** — acknowledge a single window's alarm without silencing others.
- 🤖 **Source health check** — surface a warning when an endpoint stops returning a valid `resets_at` (schema drift early-warning), per the research note.
- 🤖 **ccusage-style token/cost view** — read local `~/.claude/projects/**/*.jsonl` and `~/.codex/state_5.sqlite` for token/cost totals to complement the account-window view.

## Considering

- 🔧 **Cookie/session fallback for CLI-less users** — support users who only use the web apps (no Claude Code / Codex CLI) via a manual `sessionKey` paste or Firefox cookie import. Deliberately avoids Chrome v20 app-bound DPAPI decryption.
- 🔧 **Gemini / other providers** — generalize the provider interface to add more quota sources.
- 🔧 **Light theme option** — Catppuccin Latte variant.
- 🔧 **Optional token refresh (opt-in, safe)** — refresh-and-verify-to-a-copy before writing back, to keep polling when the CLIs aren't running. Gated because refresh-token rotation risks the live CLI login.

## Done

### v0.2.0
- Brand tiles for Claude (sunburst) and Codex (hexafoil) + new app mark.
- Six selectable, synthesized alarm sounds with a Settings picker + Test preview.
- Premium polish pass: design tokens, card borders/elevation, severity edges,
  refined Settings (sections + hints), microcopy across states, row-height fix.

### v0.1.0
- Claude + Codex usage polling via local OAuth tokens.
- Timestamp-driven reset detection + boundary-scheduled polling.
- Audible alarm + toast + in-app banner on reset.
- Per-bar alarm toggles.
- customtkinter GUI, tray, settings, headless CLI, tests, PyInstaller build.
