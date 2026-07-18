# ROADMAP

Single source of truth for open work. Legend: 🤖 = autonomous-codeable, 🔧 = operator/product-gated.

## Considering

- 🔧 **Cookie/session fallback for CLI-less users** — support users who only use the web apps (no Claude Code / Codex CLI) via a manual `sessionKey` paste or Firefox cookie import. Deliberately avoids Chrome v20 app-bound DPAPI decryption.
- 🔧 **Gemini / other providers** — generalize the provider interface to add more quota sources.
- 🔧 **Optional token refresh (opt-in, safe)** — refresh-and-verify-to-a-copy before writing back, to keep polling when the CLIs aren't running. Gated because refresh-token rotation risks the live CLI login.

## Research-Driven Additions (2026-07-18)

- [ ] P2 — **Multiple account/credential support**
  Why: Power users run 2+ Claude/Codex subscriptions to workaround rate limits; need fast switching or simultaneous monitoring.
  Evidence: Medium article "Running Two Claude Code Subs Side by Side"; community discussions on multi-profile workarounds.
  Touches: `auth.py` (accept list of credential paths), `config.py` (accounts[] setting), `gui/app.py` (account selector or multi-card layout)
  Acceptance: User can add multiple credential file paths in Settings; each account appears as a separate provider card.
  Complexity: L


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
