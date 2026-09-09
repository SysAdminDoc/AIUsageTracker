# Changelog

## 0.4.1 (2026-09-08)

### Added

- An offline demo with example quota windows, activity and token counts. Try it without credentials or saved settings.
- A screenshot-led README, setup and privacy guide, and an archive of the original logo files, earlier mockups and review captures.
- Versioned Windows installer and portable ZIP, including third-party notices. The executable now carries its product version in Windows file properties.

### Changed

- Reset-alert wording now describes polling and confirmation delays. It no longer promises instant delivery.
- The local token summary is labeled as approximate recent usage, not an exact 24-hour report.
- Mini mode opens with the current value and has enough room for its reset label. Activity's selected filter uses a readable theme color.
- Builds use a maintained packaging spec, stop on failed tests and find per-user Inno Setup installations. Runtime dependencies are pinned.
- Desktop shortcuts and startup are optional installer tasks. Uninstalling keeps app data.

### Fixed

- The Codex token reader opens its SQLite database read-only instead of changing its journal mode.
- Background token results go through the GUI queue, avoiding Tk calls from a worker thread.
- Frozen entry points and the packaging runtime hook call `freeze_support()` before application imports.

## 0.4.0 (2026-07-18)

Added local token summaries, the Activity heatmap and extra-account configuration. Later source work added the current quota-cycle logo, appearance themes and revised dashboard before those changes reached a downloadable release.

## 0.3.0 (2026-07-18)

Added usage history, forecast hints and configurable reset hooks. Status export and webhook code were also introduced.

## 0.2.0 (2026-07-17)

Added provider tiles, selectable alert sounds and the first packaged interface update.

## 0.1.0 (2026-07-17)

Initial Windows dashboard, provider polling and reset detection.

The [original changelog and roadmap snapshot](assets/concepts/2026-09-08-marketing/originals/CHANGELOG.md) remain in the archive. Historical claims there haven't all been reverified.
