# AIUsageTracker v0.4.1 visual review

## Selected identity

The existing coral-and-cyan quota-cycle logo is retained, unchanged. It has a recognizable silhouette, two distinct arcs and a clear center point. Adding a shield, extra lettering or a different visual metaphor wouldn't improve this project. Its dark tile is intentional, not a transparent cutout.

No new logo was generated in this pass. The full-size PNG and multi-size ICO are preserved under `originals/assets`, along with the earlier design concept, redesign mockup and implemented screenshot.

## Original work

[originals/manifest.json](originals/manifest.json) records SHA-256 hashes for fourteen files from the pre-edit working state. These include the README, build files and historical research. Original copies are unchanged; dated claims and earlier usage screenshots aren't current release evidence.

## Screenshot selection

The current README uses four actual captures from the application installed by the v0.4.1 installer. All use explicitly labeled offline example data. [selected-captures.json](selected-captures.json) maps each promoted image to its exact source and hash.

- `captures/source-r1`: first source exercise, including the short mini-widget and lower-contrast filter that were rejected.
- `captures/source-r2`: recaptured source after those fixes. Includes Settings, Daylight, mini mode and an example reset banner.
- `captures/packaged-r1`: first executable review. The attempted Settings image captured the main window, so it was rejected.
- `captures/packaged-r2`: corrected executable capture with the real Settings window.
- `captures/installed-r1`: the selected installer-based set. The installed EXE and both notice files matched the release inputs before capture.
- `drafts`: the first README and guide used for layout review.
- `readme-review`: dark, light and narrow Markdown previews plus the logo's small-size review.

No account credentials were used. No product UI was painted over or replaced with a mockup. Earlier captures remain available so selection decisions can be checked.

## Marketing acceptance

The updated page shows the product before a long feature list, offers direct Windows downloads, and explains the CLI requirement before installation. It removes instant-alert guarantees and presents the token summary as approximate. The selected screenshots demonstrate the shipped interface with readable example states. These are concrete improvements over the text-only README.

Live provider acceptance, sound playback and a trusted publisher signature still require separate verification. They aren't implied by the screenshots. See [release verification](../../../docs/VERIFICATION.md).
