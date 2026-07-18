"""Headless command-line interface (useful for testing and cron/log use)."""
from __future__ import annotations

import argparse
import sys
import time

from . import __version__, config
from .models import LimitWindow, now_utc
from .poller import Poller
from .providers import ClaudeProvider, CodexProvider


def _fmt_reset(w: LimitWindow) -> str:
    secs = w.seconds_until_reset()
    if secs is None:
        return "unknown"
    if secs < 0:
        return "due"
    h, rem = divmod(int(secs), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def _bar(pct: float, width: int = 20) -> str:
    filled = int(round(pct / 100 * width))
    return "#" * filled + "-" * (width - filled)


def _print_windows(windows: list[LimitWindow]) -> None:
    if not windows:
        print("   (no windows)")
        return
    for w in windows:
        flag = {"critical": "!!", "warning": " *", "normal": "  "}.get(w.severity, "  ")
        print(f"  {flag} {w.label:<34} [{_bar(w.utilization)}] {w.utilization:5.1f}%  resets in {_fmt_reset(w)}")


def cmd_poll(_args) -> int:
    for provider in (ClaudeProvider(), CodexProvider()):
        snap = provider.fetch()
        head = f"== {provider.name.upper()} =="
        if snap.ok:
            extra = snap.meta.get("plan_type") or snap.meta.get("subscription") or ""
            print(f"{head} {extra}")
            _print_windows(snap.windows)
        else:
            print(f"{head} [{snap.status}] {snap.error}")
        print()
    return 0


def cmd_monitor(args) -> int:
    settings = config.load_settings()
    poller = Poller(settings)
    poller.on_log = lambda m: print(f"[{now_utc():%H:%M:%S}] {m}")
    poller.on_reset = lambda evs: [
        print(f"*** RESET DETECTED: {e.provider} {e.label} @ {e.detected_at:%H:%M:%S} ***") for e in evs
    ]
    poller.on_warn = lambda w: print(f"~~ WARN: {w.provider} {w.label} at {w.utilization:.0f}% ~~")
    print(f"Monitoring every {settings['poll_seconds']}s. Ctrl+C to stop.")
    poller.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        poller.stop()
        print("\nstopped.")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="aiusagetracker",
                                description="Monitor Claude & Codex usage windows.")
    p.add_argument("--version", action="version", version=f"AIUsageTracker {__version__}")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("poll", help="Fetch and print current usage once")
    sub.add_parser("monitor", help="Run the headless monitor loop")
    args = p.parse_args(argv)

    if args.cmd == "poll":
        return cmd_poll(args)
    if args.cmd == "monitor":
        return cmd_monitor(args)
    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
