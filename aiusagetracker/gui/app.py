"""AIUsageTracker dashboard: customtkinter window (sidebar + cards) + system tray."""
from __future__ import annotations

import queue
import threading
from datetime import datetime

import customtkinter as ctk

from .. import __version__, config
from ..alarm import Alarm, notify
from ..models import LimitWindow, ProviderSnapshot, ResetEvent, now_utc
from ..poller import Poller
from ..storage import load_events
from . import icons
from .theme import (FONT, MOCHA, PROVIDER_ACCENT, R_LG, R_MD, R_SM,
                    SEVERITY_COLOR, STATUS_COLOR)

ctk.set_appearance_mode("dark")

PROVIDER_TITLES = {"claude": "Claude", "codex": "Codex"}


def fmt_countdown(secs) -> str:
    if secs is None:
        return "--"
    if secs <= 0:
        return "resetting..."
    secs = int(secs)
    d, rem = divmod(secs, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    if d:
        return f"{d}d {h}h {m}m"
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def fmt_local(dt) -> str:
    if dt is None:
        return "unknown"
    try:
        return dt.astimezone().strftime("%a %d %b, %I:%M %p")
    except Exception:
        return str(dt)


# ---------------------------------------------------------------------------
# Small reusable widgets
# ---------------------------------------------------------------------------
class StatCard(ctk.CTkFrame):
    """A top-row summary metric card."""

    def __init__(self, master, title: str, icon: str, accent: str):
        super().__init__(master, fg_color=MOCHA["mantle"], corner_radius=R_LG)
        self.grid_columnconfigure(1, weight=1)
        badge = ctk.CTkFrame(self, width=40, height=40, fg_color=MOCHA["surface0"],
                             corner_radius=R_MD)
        badge.grid(row=0, column=0, rowspan=2, padx=(14, 10), pady=14)
        badge.grid_propagate(False)
        ctk.CTkLabel(badge, text=icon, font=(FONT, 18), text_color=accent).place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(self, text=title, font=(FONT, 11), text_color=MOCHA["subtext0"],
                     anchor="w").grid(row=0, column=1, sticky="sw", padx=(0, 14), pady=(14, 0))
        self.value = ctk.CTkLabel(self, text="--", font=(FONT, 22, "bold"),
                                  text_color=MOCHA["text"], anchor="w")
        self.value.grid(row=1, column=1, sticky="nw", padx=(0, 14), pady=(0, 2))
        self.sub = ctk.CTkLabel(self, text="", font=(FONT, 11), text_color=MOCHA["subtext0"],
                                anchor="w")
        self.sub.grid(row=2, column=1, sticky="nw", padx=(0, 14), pady=(0, 12))

    def set(self, value: str, sub: str = "", value_color: str = None):
        self.value.configure(text=value, text_color=value_color or MOCHA["text"])
        self.sub.configure(text=sub)


class LimitRow(ctk.CTkFrame):
    """One limit window inside a provider card: bar + countdown + alarm toggle."""

    def __init__(self, master, window: LimitWindow, alarm_on: bool, on_toggle):
        super().__init__(master, fg_color=MOCHA["surface0"], corner_radius=R_MD)
        self.key = window.key
        self.resets_at = window.resets_at
        self.alarm_on = alarm_on
        self.on_toggle = on_toggle
        self.grid_columnconfigure(0, weight=1)
        sev = SEVERITY_COLOR.get(window.severity, MOCHA["green"])
        remaining = max(0.0, 100.0 - window.utilization)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=(9, 2))
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(top, text=window.label, font=(FONT, 12, "bold"),
                     text_color=MOCHA["text"], anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(top, text=f"{remaining:.0f}% left", font=(FONT, 12, "bold"),
                     text_color=sev).grid(row=0, column=1, sticky="e")

        self.bar = ctk.CTkProgressBar(self, height=8, corner_radius=R_SM,
                                      progress_color=sev, fg_color=MOCHA["surface1"])
        self.bar.set(min(1.0, window.utilization / 100))
        self.bar.grid(row=1, column=0, sticky="ew", padx=12, pady=2)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="ew", padx=12, pady=(2, 9))
        bottom.grid_columnconfigure(0, weight=1)
        self.sub = ctk.CTkLabel(bottom, text="", font=(FONT, 10), text_color=MOCHA["subtext0"],
                                anchor="w")
        self.sub.grid(row=0, column=0, sticky="w")
        self.alarm_btn = ctk.CTkButton(bottom, width=74, height=22, corner_radius=R_SM,
                                       font=(FONT, 10), command=self._toggle)
        self.alarm_btn.grid(row=0, column=1, sticky="e")
        self._style_toggle()
        self.refresh_countdown()

    def _style_toggle(self):
        if self.alarm_on:
            self.alarm_btn.configure(text="Alarm On", fg_color=MOCHA["mauve"],
                                     hover_color=MOCHA["lavender"], text_color=MOCHA["crust"])
        else:
            self.alarm_btn.configure(text="Alarm Off", fg_color=MOCHA["surface1"],
                                     hover_color=MOCHA["surface2"], text_color=MOCHA["subtext0"])

    def _toggle(self):
        self.alarm_on = not self.alarm_on
        self._style_toggle()
        if self.on_toggle:
            self.on_toggle(self.key, self.alarm_on)

    def refresh_countdown(self):
        secs = self.resets_at and (self.resets_at - now_utc()).total_seconds()
        self.sub.configure(text=f"resets in {fmt_countdown(secs)}   -   {fmt_local(self.resets_at)}")


class ProviderCard(ctk.CTkFrame):
    """A provider column holding its limit rows."""

    def __init__(self, master, name: str):
        super().__init__(master, fg_color=MOCHA["mantle"], corner_radius=R_LG)
        self.name = name
        self.accent = PROVIDER_ACCENT[name]
        self.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))
        head.grid_columnconfigure(1, weight=1)
        self.dot = ctk.CTkFrame(head, width=12, height=12, fg_color=MOCHA["overlay0"],
                                corner_radius=4)
        self.dot.grid(row=0, column=0, padx=(0, 8))
        self.dot.grid_propagate(False)
        ctk.CTkLabel(head, text=PROVIDER_TITLES[name], font=(FONT, 16, "bold"),
                     text_color=self.accent, anchor="w").grid(row=0, column=1, sticky="w")
        self.badge = ctk.CTkLabel(head, text="", font=(FONT, 11, "bold"),
                                  fg_color=MOCHA["surface0"], corner_radius=R_SM,
                                  text_color=MOCHA["subtext1"], padx=8, pady=2)
        self.badge.grid(row=0, column=2, sticky="e")

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 14))
        self.body.grid_columnconfigure(0, weight=1)

    def update(self, snap: ProviderSnapshot, settings: dict, on_toggle, row_registry: dict):
        for child in self.body.winfo_children():
            child.destroy()
        color = STATUS_COLOR.get(snap.status, MOCHA["overlay0"])
        self.dot.configure(fg_color=color)

        if not snap.ok:
            self.badge.configure(text=snap.status.replace("_", " "), text_color=color)
            ctk.CTkLabel(self.body, text=snap.error or "unavailable", font=(FONT, 11),
                         text_color=MOCHA["subtext0"], wraplength=340, justify="left",
                         anchor="w").grid(sticky="ew", padx=4, pady=8)
            return

        plan = snap.meta.get("plan_type") or snap.meta.get("subscription") or "connected"
        self.badge.configure(text=str(plan).upper(), text_color=self.accent)
        if not snap.windows:
            ctk.CTkLabel(self.body, text="no active limit windows", font=(FONT, 11),
                         text_color=MOCHA["overlay0"], anchor="w").grid(sticky="ew", padx=4, pady=8)
            return
        for i, w in enumerate(snap.windows):
            row = LimitRow(self.body, w, config.window_alarm_enabled(settings, w.key), on_toggle)
            row.grid(row=i, column=0, sticky="ew", pady=4)
            row_registry[w.key] = row


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.settings = config.load_settings()
        self.title(f"AIUsageTracker v{__version__}")
        self.geometry("1060x720")
        self.minsize(900, 600)
        self.configure(fg_color=MOCHA["base"])
        ico = icons.ensure_ico()
        if ico:
            try:
                self.iconbitmap(ico)
            except Exception:
                pass

        self._queue: "queue.Queue" = queue.Queue()
        self._rows: dict[str, LimitRow] = {}
        self._alarm = Alarm()
        self._tray = None
        self._view = "dashboard"

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main()

        self.poller = Poller(self.settings)
        self.poller.on_snapshot = lambda s: self._queue.put(("snapshot", s))
        self.poller.on_reset = lambda e: self._queue.put(("reset", e))
        self.poller.on_warn = lambda w: self._queue.put(("warn", w))
        self.poller.on_log = lambda m: self._queue.put(("log", m))
        self.poller.start()

        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self.after(150, self._drain_queue)
        self.after(1000, self._tick)
        self._start_tray()

    # -- sidebar -------------------------------------------------------------
    def _build_sidebar(self):
        bar = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=MOCHA["crust"])
        bar.grid(row=0, column=0, sticky="nsw")
        bar.grid_propagate(False)
        bar.grid_rowconfigure(3, weight=1)

        brand = ctk.CTkFrame(bar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=18, pady=(20, 24))
        logo = ctk.CTkFrame(brand, width=34, height=34, fg_color=MOCHA["mauve"], corner_radius=R_SM)
        logo.grid(row=0, column=0, rowspan=2, padx=(0, 10))
        logo.grid_propagate(False)
        ctk.CTkLabel(logo, text="AI", font=(FONT, 13, "bold"),
                     text_color=MOCHA["crust"]).place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(brand, text="AI Usage", font=(FONT, 14, "bold"),
                     text_color=MOCHA["text"]).grid(row=0, column=1, sticky="sw")
        ctk.CTkLabel(brand, text="Tracker", font=(FONT, 11),
                     text_color=MOCHA["subtext0"]).grid(row=1, column=1, sticky="nw")

        self.nav_buttons = {}
        for i, (key, label, icon) in enumerate([("dashboard", "Dashboard", "▣"),
                                                ("activity", "Activity", "≡")]):
            btn = ctk.CTkButton(bar, text=f"  {icon}   {label}", anchor="w", height=40,
                                corner_radius=R_SM, font=(FONT, 13),
                                fg_color="transparent", hover_color=MOCHA["surface0"],
                                text_color=MOCHA["subtext1"],
                                command=lambda k=key: self.show_view(k))
            btn.grid(row=1 + i, column=0, sticky="ew", padx=12, pady=2)
            self.nav_buttons[key] = btn

        footer = ctk.CTkFrame(bar, fg_color="transparent")
        footer.grid(row=4, column=0, sticky="ew", padx=18, pady=18)
        self.conn_dot = ctk.CTkFrame(footer, width=10, height=10, fg_color=MOCHA["green"],
                                     corner_radius=4)
        self.conn_dot.grid(row=0, column=0, padx=(0, 8))
        self.conn_dot.grid_propagate(False)
        self.conn_text = ctk.CTkLabel(footer, text="connecting...", font=(FONT, 11),
                                      text_color=MOCHA["subtext0"], anchor="w")
        self.conn_text.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(bar, text=f"v{__version__}", font=(FONT, 10),
                     text_color=MOCHA["overlay0"]).grid(row=5, column=0, sticky="w", padx=20, pady=(0, 14))
        self._highlight_nav()

    def _highlight_nav(self):
        for key, btn in self.nav_buttons.items():
            if key == self._view:
                btn.configure(fg_color=MOCHA["surface0"], text_color=MOCHA["mauve"])
            else:
                btn.configure(fg_color="transparent", text_color=MOCHA["subtext1"])

    # -- main area -----------------------------------------------------------
    def _build_main(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        top = ctk.CTkFrame(main, fg_color="transparent", height=64)
        top.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 4))
        top.grid_columnconfigure(0, weight=1)
        titles = ctk.CTkFrame(top, fg_color="transparent")
        titles.grid(row=0, column=0, sticky="w")
        self.view_title = ctk.CTkLabel(titles, text="Usage Dashboard", font=(FONT, 22, "bold"),
                                       text_color=MOCHA["text"], anchor="w")
        self.view_title.grid(row=0, column=0, sticky="w")
        self.view_sub = ctk.CTkLabel(titles, text="Monitor every limit. Miss no reset.",
                                     font=(FONT, 12), text_color=MOCHA["subtext0"], anchor="w")
        self.view_sub.grid(row=1, column=0, sticky="w")
        self.synced_label = ctk.CTkLabel(top, text="", font=(FONT, 11),
                                         text_color=MOCHA["subtext0"])
        self.synced_label.grid(row=0, column=1, sticky="e", padx=(0, 10))
        ctk.CTkButton(top, text="Refresh", width=96, height=34, corner_radius=R_SM,
                      fg_color=MOCHA["mauve"], hover_color=MOCHA["lavender"],
                      text_color=MOCHA["crust"], font=(FONT, 12, "bold"),
                      command=self.refresh_now).grid(row=0, column=2, sticky="e")
        ctk.CTkButton(top, text="⚙", width=40, height=34, corner_radius=R_SM,
                      fg_color=MOCHA["surface0"], hover_color=MOCHA["surface1"],
                      text_color=MOCHA["text"], font=(FONT, 15),
                      command=self.open_settings).grid(row=0, column=3, sticky="e", padx=(8, 0))

        # Alarm banner (hidden until a reset fires)
        self.banner = ctk.CTkFrame(main, fg_color=MOCHA["red"], corner_radius=R_MD)
        self.banner.grid_columnconfigure(0, weight=1)
        self.banner_label = ctk.CTkLabel(self.banner, text="", font=(FONT, 13, "bold"),
                                         text_color=MOCHA["crust"])
        self.banner_label.grid(row=0, column=0, sticky="w", padx=16, pady=10)
        ctk.CTkButton(self.banner, text="Stop alarm", width=100, height=28, corner_radius=R_SM,
                      fg_color=MOCHA["crust"], hover_color=MOCHA["mantle"],
                      text_color=MOCHA["text"], command=self.acknowledge_alarm).grid(row=0, column=1, padx=10)

        # Scrollable body (holds both views)
        self.body = ctk.CTkScrollableFrame(main, fg_color="transparent")
        self.body.grid(row=2, column=0, sticky="nsew", padx=16, pady=(6, 12))
        self.body.grid_columnconfigure(0, weight=1)

        self._build_dashboard_view()
        self._build_activity_view()
        self.show_view("dashboard")

    def _build_dashboard_view(self):
        self.dash = ctk.CTkFrame(self.body, fg_color="transparent")
        self.dash.grid_columnconfigure(0, weight=1)

        stats = ctk.CTkFrame(self.dash, fg_color="transparent")
        stats.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 10))
        for i in range(3):
            stats.grid_columnconfigure(i, weight=1, uniform="stat")
        self.stat_highest = StatCard(stats, "HIGHEST USAGE", "▲", MOCHA["peach"])
        self.stat_highest.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.stat_next = StatCard(stats, "NEXT RESET", "⏱", MOCHA["blue"])
        self.stat_next.grid(row=0, column=1, sticky="ew", padx=6)
        self.stat_conn = StatCard(stats, "CONNECTIONS", "⚡", MOCHA["green"])
        self.stat_conn.grid(row=0, column=2, sticky="ew", padx=(6, 0))

        providers = ctk.CTkFrame(self.dash, fg_color="transparent")
        providers.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 10))
        providers.grid_columnconfigure(0, weight=1, uniform="prov")
        providers.grid_columnconfigure(1, weight=1, uniform="prov")
        self.provider_cards = {
            "claude": ProviderCard(providers, "claude"),
            "codex": ProviderCard(providers, "codex"),
        }
        self.provider_cards["claude"].grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.provider_cards["codex"].grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        act = ctk.CTkFrame(self.dash, fg_color=MOCHA["mantle"], corner_radius=R_LG)
        act.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        act.grid_columnconfigure(0, weight=1)
        head = ctk.CTkFrame(act, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(head, text="Recent activity", font=(FONT, 14, "bold"),
                     text_color=MOCHA["text"], anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkButton(head, text="View all", width=72, height=26, corner_radius=R_SM,
                      fg_color="transparent", hover_color=MOCHA["surface0"],
                      text_color=MOCHA["mauve"], command=lambda: self.show_view("activity")).grid(row=0, column=1, sticky="e")
        self.recent_list = ctk.CTkFrame(act, fg_color="transparent")
        self.recent_list.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        self.recent_list.grid_columnconfigure(0, weight=1)

    def _build_activity_view(self):
        self.activity = ctk.CTkFrame(self.body, fg_color="transparent")
        self.activity.grid_columnconfigure(0, weight=1)
        self.activity_list = ctk.CTkFrame(self.activity, fg_color=MOCHA["mantle"], corner_radius=R_LG)
        self.activity_list.grid(row=0, column=0, sticky="ew", padx=8, pady=4)
        self.activity_list.grid_columnconfigure(0, weight=1)

    def show_view(self, key: str):
        self._view = key
        self.dash.grid_forget()
        self.activity.grid_forget()
        if key == "dashboard":
            self.view_title.configure(text="Usage Dashboard")
            self.view_sub.configure(text="Monitor every limit. Miss no reset.")
            self.dash.grid(row=0, column=0, sticky="nsew")
        else:
            self.view_title.configure(text="Activity")
            self.view_sub.configure(text="Every detected usage reset.")
            self.activity.grid(row=0, column=0, sticky="nsew")
            self._render_activity()
        self._highlight_nav()

    # -- activity rendering --------------------------------------------------
    def _event_rows(self, parent, events, limit):
        for child in parent.winfo_children():
            child.destroy()
        if not events:
            ctk.CTkLabel(parent, text="No resets recorded yet. You'll be alarmed the moment one happens.",
                         font=(FONT, 11), text_color=MOCHA["overlay0"], anchor="w").grid(sticky="ew", padx=6, pady=10)
            return
        for i, ev in enumerate(reversed(events[-limit:])):
            prov = ev.get("provider", "")
            accent = PROVIDER_ACCENT.get(prov, MOCHA["overlay0"])
            row = ctk.CTkFrame(parent, fg_color=MOCHA["surface0"], corner_radius=R_SM)
            row.grid(row=i, column=0, sticky="ew", pady=3)
            row.grid_columnconfigure(1, weight=1)
            dot = ctk.CTkFrame(row, width=10, height=10, fg_color=accent, corner_radius=4)
            dot.grid(row=0, column=0, padx=(12, 8), pady=10)
            dot.grid_propagate(False)
            ctk.CTkLabel(row, text=f"{PROVIDER_TITLES.get(prov, prov)}  -  {ev.get('label','')} reset",
                         font=(FONT, 12), text_color=MOCHA["text"], anchor="w").grid(row=0, column=1, sticky="w")
            when = ev.get("detected_at", "")
            try:
                when = datetime.fromisoformat(when).astimezone().strftime("%d %b, %I:%M %p")
            except Exception:
                pass
            ctk.CTkLabel(row, text=when, font=(FONT, 11), text_color=MOCHA["subtext0"]).grid(row=0, column=2, sticky="e", padx=14)

    def _render_recent(self):
        self._event_rows(self.recent_list, load_events(200), 5)

    def _render_activity(self):
        self._event_rows(self.activity_list, load_events(200), 100)

    # -- queue / event handling ---------------------------------------------
    def _drain_queue(self):
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "snapshot":
                    self._on_snapshot(payload)
                elif kind == "reset":
                    self._on_reset(payload)
                elif kind == "warn":
                    self._on_warn(payload)
        except queue.Empty:
            pass
        self.after(200, self._drain_queue)

    def _on_snapshot(self, snap: ProviderSnapshot):
        for key in [k for k in self._rows if k.startswith(f"{snap.provider}:")]:
            self._rows.pop(key, None)
        card = self.provider_cards.get(snap.provider)
        if card:
            card.update(snap, self.settings, self._set_window_alarm, self._rows)
        self._recompute_summary()

    def _recompute_summary(self):
        snaps = self.poller.snapshots()
        windows = []
        for s in snaps.values():
            if s.ok:
                windows.extend(s.windows)

        if windows:
            hi = max(windows, key=lambda w: w.utilization)
            self.stat_highest.set(f"{hi.utilization:.0f}%",
                                  f"{hi.label} ({PROVIDER_TITLES.get(hi.provider, hi.provider)})",
                                  SEVERITY_COLOR.get(hi.severity, MOCHA["text"]))
        else:
            self.stat_highest.set("--", "no data")

        # next reset handled in _tick (needs live countdown); seed it now too
        self._update_next_reset(windows)

        enabled = [p for p, on in self.settings.get("providers", {}).items() if on]
        oks = [p for p in enabled if snaps.get(p) and snaps[p].ok]
        if enabled and len(oks) == len(enabled):
            self.stat_conn.set("All good", f"{len(oks)}/{len(enabled)} providers connected", MOCHA["green"])
            self.conn_dot.configure(fg_color=MOCHA["green"])
            self.conn_text.configure(text="All systems connected")
        else:
            bad = [p for p in enabled if p not in oks]
            self.stat_conn.set(f"{len(oks)}/{len(enabled)}", "check " + ", ".join(bad) if bad else "connecting",
                               MOCHA["yellow"] if oks else MOCHA["red"])
            self.conn_dot.configure(fg_color=MOCHA["yellow"] if oks else MOCHA["red"])
            self.conn_text.configure(text=(", ".join(bad) + " offline") if bad else "connecting...")

        times = [s.fetched_at for s in snaps.values() if s.ok]
        if times:
            self.synced_label.configure(text=f"Synced {max(times).astimezone():%I:%M:%S %p}  -  every {self.settings['poll_seconds']}s")
        self._render_recent()

    def _update_next_reset(self, windows=None):
        if windows is None:
            windows = []
            for s in self.poller.snapshots().values():
                if s.ok:
                    windows.extend(s.windows)
        future = [(w, w.seconds_until_reset()) for w in windows]
        future = [(w, s) for w, s in future if s is not None and s > 0]
        if future:
            w, s = min(future, key=lambda t: t[1])
            self.stat_next.set(fmt_countdown(s),
                               f"{w.label} ({PROVIDER_TITLES.get(w.provider, w.provider)})",
                               MOCHA["blue"])
        else:
            self.stat_next.set("--", "no upcoming resets")

    def _on_reset(self, events: list[ResetEvent]):
        alarming = [e for e in events if config.window_alarm_enabled(self.settings, e.key)]
        self._render_recent()
        if self._view == "activity":
            self._render_activity()
        if not alarming:
            return
        labels = ", ".join(f"{PROVIDER_TITLES.get(e.provider, e.provider)} {e.label}" for e in alarming)
        self.banner_label.configure(text=f"USAGE RESET: {labels}")
        self.banner.grid(row=1, column=0, sticky="ew", padx=24, pady=(2, 4))
        if self.settings.get("alarm_sound", True):
            self._alarm.start(loop=self.settings.get("alarm_loop", True))
        if self.settings.get("toast", True):
            notify("AI Usage Reset", f"{labels} has reset.")
        try:
            self.deiconify(); self.lift(); self.focus_force()
        except Exception:
            pass

    def _on_warn(self, w: LimitWindow):
        if self.settings.get("toast", True):
            notify("Usage nearing limit",
                   f"{PROVIDER_TITLES.get(w.provider, w.provider)} {w.label} at {w.utilization:.0f}%")

    # -- periodic tick -------------------------------------------------------
    def _tick(self):
        for row in self._rows.values():
            try:
                row.refresh_countdown()
            except Exception:
                pass
        self._update_next_reset()
        self.after(1000, self._tick)

    # -- actions -------------------------------------------------------------
    def refresh_now(self):
        self.poller.poll_now()

    def acknowledge_alarm(self):
        self._alarm.stop()
        self.banner.grid_forget()

    def _set_window_alarm(self, key: str, on: bool):
        self.settings.setdefault("window_alarms", {})[key] = bool(on)
        config.save_settings(self.settings)

    def open_settings(self):
        SettingsDialog(self)

    def apply_settings(self, new: dict):
        self.settings.update(new)
        config.save_settings(self.settings)
        self.poller.settings = self.settings
        self.poller.poll_now()

    # -- tray ----------------------------------------------------------------
    def _start_tray(self):
        try:
            import pystray
        except Exception:
            return
        image = icons.make_icon(64)
        menu = pystray.Menu(
            pystray.MenuItem("Show", lambda i=None, it=None: self.after(0, self._show_window), default=True),
            pystray.MenuItem("Poll now", lambda i=None, it=None: self.after(0, self.refresh_now)),
            pystray.MenuItem("Settings", lambda i=None, it=None: self.after(0, self.open_settings)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", lambda i=None, it=None: self.after(0, self.quit_app)),
        )
        self._tray = pystray.Icon("AIUsageTracker", image, "AI Usage Tracker", menu)
        threading.Thread(target=self._tray.run, daemon=True).start()

    def _show_window(self):
        self.deiconify(); self.lift(); self.focus_force()

    def hide_to_tray(self):
        if self._tray is not None:
            self.withdraw()
        else:
            self.quit_app()

    def quit_app(self):
        try:
            self._alarm.stop()
            self.poller.stop()
            if self._tray is not None:
                self._tray.stop()
        finally:
            self.destroy()

    def run(self):
        if self.settings.get("start_minimized") and self._tray is not None:
            self.withdraw()
        self.mainloop()


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, app: App):
        super().__init__(app)
        self.app = app
        self.title("Settings")
        self.geometry("380x420")
        self.configure(fg_color=MOCHA["base"])
        self.transient(app)
        s = app.settings
        pad = {"padx": 18, "pady": 6}
        ctk.CTkLabel(self, text="Settings", font=(FONT, 16, "bold"),
                     text_color=MOCHA["text"]).pack(anchor="w", **pad)

        self.var_claude = ctk.BooleanVar(value=s["providers"].get("claude", True))
        self.var_codex = ctk.BooleanVar(value=s["providers"].get("codex", True))
        self.var_alarm = ctk.BooleanVar(value=s.get("alarm_sound", True))
        self.var_loop = ctk.BooleanVar(value=s.get("alarm_loop", True))
        self.var_toast = ctk.BooleanVar(value=s.get("toast", True))
        self.var_min = ctk.BooleanVar(value=s.get("start_minimized", False))
        for text, var in [
            ("Track Claude", self.var_claude),
            ("Track Codex", self.var_codex),
            ("Audible alarm on reset", self.var_alarm),
            ("Loop alarm until acknowledged", self.var_loop),
            ("Toast notifications", self.var_toast),
            ("Start minimized to tray", self.var_min),
        ]:
            ctk.CTkCheckBox(self, text=text, variable=var, text_color=MOCHA["text"],
                            fg_color=MOCHA["mauve"], hover_color=MOCHA["lavender"]).pack(anchor="w", **pad)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(anchor="w", fill="x", **pad)
        ctk.CTkLabel(row, text="Poll interval (s):", text_color=MOCHA["text"]).pack(side="left")
        self.poll_entry = ctk.CTkEntry(row, width=80)
        self.poll_entry.insert(0, str(s.get("poll_seconds", config.DEFAULT_POLL_SECONDS)))
        self.poll_entry.pack(side="left", padx=8)
        ctk.CTkLabel(row, text=f"(min {config.MIN_POLL_SECONDS})", text_color=MOCHA["subtext0"],
                     font=(FONT, 10)).pack(side="left")

        ctk.CTkButton(self, text="Save", corner_radius=R_SM, fg_color=MOCHA["green"],
                      text_color=MOCHA["crust"], hover_color=MOCHA["teal"],
                      command=self._save).pack(pady=18)

    def _save(self):
        try:
            poll = max(config.MIN_POLL_SECONDS, int(self.poll_entry.get()))
        except ValueError:
            poll = config.DEFAULT_POLL_SECONDS
        self.app.apply_settings({
            "providers": {"claude": self.var_claude.get(), "codex": self.var_codex.get()},
            "alarm_sound": self.var_alarm.get(),
            "alarm_loop": self.var_loop.get(),
            "toast": self.var_toast.get(),
            "start_minimized": self.var_min.get(),
            "poll_seconds": poll,
        })
        self.destroy()


def main():
    app = App()
    app.run()


if __name__ == "__main__":
    main()
