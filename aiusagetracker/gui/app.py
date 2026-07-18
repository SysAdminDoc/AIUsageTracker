"""AIUsageTracker dashboard: customtkinter window (sidebar + cards) + system tray."""
from __future__ import annotations

import queue
import threading
from collections import deque
from datetime import datetime

import customtkinter as ctk

from .. import __version__, config
from ..alarm import (DEFAULT_SOUND, SOUND_NAMES, Alarm, notify, preview, send_webhook)
from ..models import LimitWindow, ProviderSnapshot, ResetEvent, now_utc
from ..poller import Poller
from ..storage import load_events, load_history
from . import icons, theme as ui_theme
from .theme import (FONT, FS_BODY, FS_DISPLAY, FS_H1, FS_H2,
                    FS_SMALL, FS_TINY, FS_TITLE, MOCHA, PROVIDER_ACCENT, R_LG,
                    R_MD, R_SM, R_XS, SEVERITY_COLOR, SP_LG, SP_MD, SP_SM, SP_XL,
                    SP_XS, STATUS_COLOR)

ctk.set_appearance_mode("dark")

PROVIDER_TITLES = {"claude": "Claude", "codex": "Codex"}
STATUS_TEXT = {"ok": "Connected", "auth_expired": "Login expired",
               "no_credentials": "Not signed in", "error": "Unavailable"}

_IMG_CACHE: dict = {}


def tile_image(kind: str, size: int):
    key = (kind, size)
    if key not in _IMG_CACHE:
        if kind == "claude":
            pil = icons.claude_tile(size * 3)
        elif kind == "codex":
            pil = icons.codex_tile(size * 3)
        else:
            pil = icons.app_tile(size * 3)
        _IMG_CACHE[key] = ctk.CTkImage(light_image=pil, dark_image=pil, size=(size, size))
    return _IMG_CACHE[key]


def bell_image(enabled: bool, size: int = 18):
    key = ("bell", enabled, size)
    if key not in _IMG_CACHE:
        color = MOCHA["blue"] if enabled else MOCHA["subtext0"]
        pil = icons.bell_icon(size * 3, color, enabled)
        _IMG_CACHE[key] = ctk.CTkImage(light_image=pil, dark_image=pil, size=(size, size))
    return _IMG_CACHE[key]


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


def set_windows_chrome(window, theme_key: str):
    """Match a Tk window's native caption to the selected application theme."""
    try:
        import ctypes
        from ctypes import byref, c_int, sizeof

        def colorref(value: str) -> int:
            value = value.lstrip("#")
            red, green, blue = (int(value[i:i + 2], 16) for i in (0, 2, 4))
            return red | (green << 8) | (blue << 16)

        hwnd = ctypes.windll.user32.GetParent(window.winfo_id()) or window.winfo_id()
        enabled = c_int(1 if ui_theme.appearance_for(theme_key) == "dark" else 0)
        for attribute in (20, 19):
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attribute, byref(enabled), sizeof(enabled))
        caption = c_int(colorref(MOCHA["crust"]))
        text = c_int(colorref(MOCHA["text"]))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, byref(caption), sizeof(caption))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 36, byref(text), sizeof(text))
    except Exception:
        pass


class ToolTip:
    """Small delayed helper for icon-only controls."""

    def __init__(self, widget, text, delay: int = 450):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._after_id = None
        self._tip = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None):
        self._hide()
        self._after_id = self.widget.after(self.delay, self._show)

    def _show(self):
        self._after_id = None
        try:
            exists = self.widget.winfo_exists()
        except Exception:
            return
        if not exists:
            return
        message = self.text() if callable(self.text) else self.text
        tip = ctk.CTkToplevel(self.widget)
        tip.overrideredirect(True)
        tip.attributes("-topmost", True)
        ctk.CTkLabel(tip, text=message, font=(FONT, FS_TINY),
                     fg_color=MOCHA["surface1"], text_color=MOCHA["text"],
                     corner_radius=R_SM, padx=SP_SM, pady=SP_XS).pack()
        tip.update_idletasks()
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2 - tip.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        tip.geometry(f"+{max(4, x)}+{max(4, y)}")
        self._tip = tip

    def _hide(self, _event=None):
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        if self._tip is not None:
            try:
                self._tip.destroy()
            except Exception:
                pass
            self._tip = None


# ---------------------------------------------------------------------------
# Reusable widgets
# ---------------------------------------------------------------------------
class StatCard(ctk.CTkFrame):
    """Compact summary metric used in the dashboard's lower band."""

    def __init__(self, master, title: str, icon: str, accent: str):
        super().__init__(master, fg_color=MOCHA["mantle"], corner_radius=R_LG,
                         border_width=1, border_color=MOCHA["surface1"])
        self.grid_columnconfigure(0, weight=1)
        badge = ctk.CTkFrame(self, width=34, height=34, fg_color=MOCHA["surface0"],
                             corner_radius=R_SM, border_width=1, border_color=accent)
        badge.grid(row=0, column=0, pady=(SP_LG, SP_SM))
        badge.grid_propagate(False)
        ctk.CTkLabel(badge, text=icon, font=(FONT, 16, "bold"), text_color=accent).place(
            relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(self, text=title, font=(FONT, FS_SMALL), text_color=MOCHA["subtext1"]
                     ).grid(row=1, column=0)
        self.value = ctk.CTkLabel(self, text="--", font=(FONT, FS_DISPLAY, "bold"),
                                  text_color=MOCHA["text"])
        self.value.grid(row=2, column=0, pady=(2, 0))
        self.sub = ctk.CTkLabel(self, text="", font=(FONT, FS_SMALL), text_color=MOCHA["subtext0"],
                                wraplength=155, justify="center")
        self.sub.grid(row=3, column=0, padx=SP_SM, pady=(0, SP_LG))

    def set(self, value: str, sub: str = "", value_color: str = None):
        self.value.configure(text=value, text_color=value_color or MOCHA["text"])
        self.sub.configure(text=sub)


class InsightMetric(ctk.CTkFrame):
    """One half of the prominent dashboard insight strip."""

    def __init__(self, master, title: str, icon: str, accent: str):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(1, weight=1)
        badge = ctk.CTkFrame(self, width=48, height=48, fg_color=MOCHA["surface0"],
                             corner_radius=R_LG, border_width=1, border_color=accent)
        badge.grid(row=0, column=0, rowspan=2, padx=(0, SP_LG), pady=SP_MD)
        badge.grid_propagate(False)
        ctk.CTkLabel(badge, text=icon, font=(FONT, 22, "bold"), text_color=accent).place(
            relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(self, text=title, font=(FONT, FS_SMALL), text_color=MOCHA["subtext1"],
                     anchor="w").grid(row=0, column=1, sticky="sw", pady=(SP_MD, 0))
        self.value = ctk.CTkLabel(self, text="--", font=(FONT, FS_DISPLAY, "bold"),
                                  text_color=accent, anchor="w")
        self.value.grid(row=1, column=1, sticky="nw", pady=(0, SP_MD))
        self.sub = ctk.CTkLabel(self, text="Waiting for data", font=(FONT, FS_BODY),
                                text_color=MOCHA["subtext0"], anchor="w", justify="left")
        self.sub.grid(row=0, column=2, rowspan=2, sticky="w", padx=(SP_LG, SP_SM))

    def set(self, value: str, sub: str = "", value_color: str = None):
        self.value.configure(text=value, text_color=value_color or MOCHA["text"])
        self.sub.configure(text=sub)


class _Sparkline(ctk.CTkCanvas):
    """Tiny inline line chart showing last 24h of utilization for one window."""

    WIDTH = 120
    HEIGHT = 20

    def __init__(self, master, window_key: str, color: str):
        super().__init__(master, width=self.WIDTH, height=self.HEIGHT,
                         bg=MOCHA["surface0"], highlightthickness=0)
        self._color = color
        self._draw(window_key)

    def _draw(self, key: str):
        history = load_history(since_hours=24.0)
        points = []
        for rec in history:
            for w in rec.get("windows", []):
                if w.get("key") == key:
                    points.append(w.get("pct", 0))
        if len(points) < 2:
            return
        w, h = self.WIDTH, self.HEIGHT
        pad = 2
        step = (w - 2 * pad) / (len(points) - 1)
        coords = []
        for i, pct in enumerate(points):
            x = pad + i * step
            y = pad + (h - 2 * pad) * (1.0 - pct / 100.0)
            coords.extend([x, y])
        self.create_line(*coords, fill=self._color, width=1.5, smooth=True)


class LimitRow(ctk.CTkFrame):
    """One quota window with a strong usage value and compact alarm control."""

    def __init__(self, master, window: LimitWindow, alarm_on: bool, on_toggle):
        super().__init__(master, fg_color=MOCHA["surface0"], corner_radius=R_MD)
        self.key = window.key
        self.resets_at = window.resets_at
        self.alarm_on = alarm_on
        self.on_toggle = on_toggle
        self.grid_columnconfigure(1, weight=1)
        sev = SEVERITY_COLOR.get(window.severity, MOCHA["green"])

        edge = ctk.CTkFrame(self, width=3, height=6, fg_color=sev, corner_radius=R_XS)
        edge.grid(row=0, column=0, rowspan=3, sticky="ns", padx=(7, 0), pady=9)

        ctk.CTkLabel(self, text=window.label, font=(FONT, FS_TITLE, "bold"),
                     text_color=MOCHA["text"], anchor="w", wraplength=250,
                     justify="left").grid(row=0, column=1, sticky="w",
                                           padx=(SP_MD, SP_SM), pady=(SP_MD, 0))

        usage = ctk.CTkFrame(self, fg_color="transparent")
        usage.grid(row=0, column=2, sticky="e", pady=(SP_SM, 0))
        ctk.CTkLabel(usage, text=f"{window.utilization:.0f}%", font=(FONT, FS_H2, "bold"),
                     text_color=sev).pack(side="left")
        ctk.CTkLabel(usage, text=" used", font=(FONT, FS_TINY),
                     text_color=MOCHA["subtext0"]).pack(side="left", pady=(5, 0))

        self.alarm_btn = ctk.CTkButton(self, width=38, height=38, corner_radius=R_SM,
                                       border_width=1, font=(FONT, 15, "bold"),
                                       command=self._toggle)
        self.alarm_btn.grid(row=0, column=3, rowspan=3, sticky="e",
                            padx=(SP_MD, SP_MD), pady=SP_MD)
        self.alarm_tip = ToolTip(
            self.alarm_btn,
            lambda: "Disable reset alarm" if self.alarm_on else "Enable reset alarm",
        )
        self._style_toggle()

        self.sub = ctk.CTkLabel(self, text="", font=(FONT, FS_TINY), text_color=MOCHA["subtext0"],
                                anchor="w")
        self.sub.grid(row=1, column=1, columnspan=2, sticky="w",
                      padx=(SP_MD, SP_SM), pady=(1, 5))

        self.bar = ctk.CTkProgressBar(self, height=8, corner_radius=R_XS,
                                      progress_color=sev, fg_color=MOCHA["surface2"])
        self._bar_target = min(1.0, window.utilization / 100)
        self.bar.set(0)
        self.bar.grid(row=2, column=1, columnspan=2, sticky="ew",
                      padx=(SP_MD, SP_SM), pady=(0, 4))
        self._animate_bar(0, self._bar_target, 0)

        self.sparkline = _Sparkline(self, window.key, sev)
        self.sparkline.grid(row=3, column=1, columnspan=2, sticky="ew",
                            padx=(SP_MD, SP_SM), pady=(0, SP_MD))
        self.refresh_countdown()

    def _style_toggle(self):
        if self.alarm_on:
            self.alarm_btn.configure(text="", image=bell_image(True), fg_color=MOCHA["surface1"],
                                     hover_color=MOCHA["surface2"], border_color=MOCHA["blue"],
                                     text_color=MOCHA["blue"])
        else:
            self.alarm_btn.configure(text="", image=bell_image(False), fg_color=MOCHA["surface0"],
                                     hover_color=MOCHA["surface1"], border_color=MOCHA["surface2"],
                                     text_color=MOCHA["subtext0"])

    def _toggle(self):
        self.alarm_on = not self.alarm_on
        self._style_toggle()
        if self.on_toggle:
            self.on_toggle(self.key, self.alarm_on)

    def _animate_bar(self, current: float, target: float, step: int):
        total_steps = 12
        if step >= total_steps:
            self.bar.set(target)
            return
        progress = (step + 1) / total_steps
        value = current + (target - current) * progress
        self.bar.set(value)
        self.after(25, self._animate_bar, current, target, step + 1)

    def refresh_countdown(self):
        secs = self.resets_at and (self.resets_at - now_utc()).total_seconds()
        self.sub.configure(text=f"Resets in {fmt_countdown(secs)}   ·   {fmt_local(self.resets_at)}")


class ProviderCard(ctk.CTkFrame):
    """A provider column: brand tile header + limit rows."""

    def __init__(self, master, name: str):
        super().__init__(master, fg_color=MOCHA["mantle"], corner_radius=R_LG,
                         border_width=1, border_color=MOCHA["surface1"])
        self.name = name
        self.accent = PROVIDER_ACCENT[name]
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkFrame(self, height=4, fg_color=self.accent, corner_radius=R_XS).grid(
            row=0, column=0, sticky="ew", padx=1, pady=(1, 0))

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=1, column=0, sticky="ew", padx=SP_LG, pady=(SP_LG, SP_MD))
        head.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(head, text="", image=tile_image(name, 38)).grid(row=0, column=0, rowspan=2, padx=(0, SP_MD))
        ctk.CTkLabel(head, text=PROVIDER_TITLES[name], font=(FONT, FS_H2, "bold"),
                     text_color=MOCHA["text"], anchor="w").grid(row=0, column=1, sticky="sw")
        self.status = ctk.CTkLabel(head, text="Connecting...", font=(FONT, FS_TINY),
                                   text_color=MOCHA["subtext0"], anchor="w")
        self.status.grid(row=1, column=1, sticky="nw", padx=(15, 0))
        self.dot = ctk.CTkFrame(head, width=9, height=9, fg_color=MOCHA["overlay0"], corner_radius=4)
        self.dot.place(x=52, rely=0.78, anchor="center")
        self.dot.grid_propagate(False)
        self.badge = ctk.CTkLabel(head, text="", font=(FONT, FS_TINY, "bold"),
                                  fg_color=MOCHA["surface0"], corner_radius=R_SM,
                                  text_color=MOCHA["subtext1"], padx=9, pady=3)
        self.badge.grid(row=0, column=2, rowspan=2, sticky="e")

        ctk.CTkFrame(self, height=1, fg_color=MOCHA["surface1"]).grid(row=2, column=0, sticky="ew", padx=SP_LG)

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=3, column=0, sticky="nsew", padx=SP_MD, pady=(SP_SM, SP_LG))
        self.body.grid_columnconfigure(0, weight=1)

    def update(self, snap: ProviderSnapshot, settings: dict, on_toggle, row_registry: dict):
        for child in self.body.winfo_children():
            child.destroy()
        color = STATUS_COLOR.get(snap.status, MOCHA["overlay0"])
        self.dot.configure(fg_color=color)
        self.status.configure(text=STATUS_TEXT.get(snap.status, snap.status.replace("_", " ")),
                              text_color=(MOCHA["subtext0"] if snap.ok else color))

        if not snap.ok:
            self.badge.configure(text="", fg_color="transparent")
            if snap.status == "no_credentials":
                hint = ("Open Claude Code and sign in, then refresh usage."
                        if self.name == "claude"
                        else "Run Codex and sign in, then refresh usage.")
                self._empty("Not signed in", MOCHA["subtext1"], hint)
            elif snap.status == "auth_expired":
                hint = ("Re-open Claude Code to renew your login."
                        if self.name == "claude"
                        else "Run Codex again to renew your login.")
                self._empty("Your login has expired", color, hint)
            else:
                message = snap.error or "Usage is temporarily unavailable."
                if "429" in message or "rate limit" in message.casefold():
                    hint = "The provider asked us to pause. AIUsageTracker will retry automatically."
                else:
                    hint = "Check your connection, then try Refresh usage."
                self._empty(message, color, hint)
            return

        plan = snap.meta.get("plan_type") or snap.meta.get("subscription") or ""
        self.badge.configure(text=str(plan).upper(), text_color=self.accent,
                             fg_color=MOCHA["surface0"] if plan else "transparent")
        if not snap.windows:
            self._empty("No active limit windows right now.", MOCHA["overlay0"])
            return
        for i, w in enumerate(snap.windows):
            row = LimitRow(self.body, w, config.window_alarm_enabled(settings, w.key), on_toggle)
            row.grid(row=i, column=0, sticky="ew", pady=SP_XS)
            row_registry[w.key] = row

    def _empty(self, text, color, hint=""):
        ctk.CTkLabel(self.body, text=text, font=(FONT, FS_SMALL), text_color=color,
                     wraplength=340, justify="left", anchor="w").grid(
                         row=0, column=0, sticky="ew", padx=6,
                         pady=(SP_MD, SP_XS if hint else SP_MD))
        if hint:
            ctk.CTkLabel(self.body, text=hint, font=(FONT, FS_TINY),
                         text_color=MOCHA["subtext0"], wraplength=340,
                         justify="left", anchor="w").grid(
                             row=1, column=0, sticky="ew", padx=6, pady=(0, SP_MD))


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------
class App(ctk.CTk):
    def __init__(self):
        settings = config.load_settings()
        settings["theme"] = ui_theme.apply_theme(settings.get("theme"))
        ctk.set_appearance_mode(ui_theme.appearance_for(settings["theme"]))
        super().__init__()
        self.settings = settings
        self.title(f"AIUsageTracker v{__version__}")
        self.geometry("1280x800")
        self.minsize(1000, 680)
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
        self._burn_samples: dict[str, deque] = {}  # key -> deque of (timestamp, pct)
        self._pending_resets: list[ResetEvent] = []
        self._reset_debounce_id = None
        self._last_sync_ts: float | None = None
        self._snoozed: set[str] = set()
        self._last_alarming_keys: list[str] = []
        self._view = "dashboard"
        self._settings_dialog = None
        self._refresh_pending: set[str] = set()
        self._refresh_timeout_id = None
        self._theme_rebuild_id = None
        self._drain_after_id = None
        self._tick_after_id = None
        self._chrome_after_id = None
        self._closing = False

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
        self._chrome_after_id = self.after(80, self._apply_windows_chrome)
        self._drain_after_id = self.after(150, self._drain_queue)
        self._tick_after_id = self.after(1000, self._tick)
        self._start_tray()

    def _apply_windows_chrome(self):
        """Ask DWM for caption colors that match the active theme."""
        set_windows_chrome(self, self.settings.get("theme", ui_theme.DEFAULT_THEME))

    # -- sidebar -------------------------------------------------------------
    def _build_sidebar(self):
        bar = ctk.CTkFrame(self, width=188, corner_radius=0, fg_color=MOCHA["crust"],
                           border_width=0)
        self.sidebar = bar
        bar.grid(row=0, column=0, sticky="nsw")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(0, weight=1)
        bar.grid_rowconfigure(3, weight=1)

        brand = ctk.CTkFrame(bar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=SP_LG, pady=(SP_XL, 34))
        ctk.CTkLabel(brand, text="", image=tile_image("app", 38)).grid(
            row=0, column=0, rowspan=2, padx=(0, SP_MD))
        ctk.CTkLabel(brand, text="AIUsageTracker", font=(FONT, FS_TITLE, "bold"),
                     text_color=MOCHA["text"]).grid(row=0, column=1, sticky="sw")
        ctk.CTkLabel(brand, text=f"v{__version__}", font=(FONT, FS_TINY),
                     text_color=MOCHA["subtext0"]).grid(row=1, column=1, sticky="nw")

        self.nav_buttons = {}
        for i, (key, label, icon) in enumerate([("dashboard", "Dashboard", "▦"),
                                                ("activity", "Activity", "☷")]):
            btn = ctk.CTkButton(bar, text=f"  {icon}     {label}", anchor="w", height=46,
                                corner_radius=R_SM, font=(FONT, FS_TITLE),
                                fg_color="transparent", hover_color=MOCHA["surface0"],
                                text_color=MOCHA["subtext1"],
                                command=lambda k=key: self.show_view(k))
            btn.grid(row=1 + i, column=0, sticky="ew", padx=SP_MD, pady=3)
            self.nav_buttons[key] = btn

        footer = ctk.CTkFrame(bar, fg_color=MOCHA["mantle"], corner_radius=R_MD,
                              border_width=1, border_color=MOCHA["surface1"])
        footer.grid(row=4, column=0, sticky="ew", padx=SP_MD, pady=SP_MD)
        footer.grid_columnconfigure(0, weight=1)
        inner = ctk.CTkFrame(footer, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="ew", padx=SP_MD, pady=(SP_MD, SP_XS))
        self.conn_dot = ctk.CTkFrame(inner, width=9, height=9, fg_color=MOCHA["green"], corner_radius=4)
        self.conn_dot.grid(row=0, column=0, padx=(0, SP_SM))
        self.conn_dot.grid_propagate(False)
        self.conn_text = ctk.CTkLabel(inner, text="Connecting...", font=(FONT, FS_SMALL),
                                      text_color=MOCHA["subtext1"], anchor="w")
        self.conn_text.grid(row=0, column=1, sticky="w")
        self.conn_detail = ctk.CTkLabel(footer, text="Waiting for first sync", font=(FONT, FS_TINY),
                                        text_color=MOCHA["subtext0"], anchor="w")
        self.conn_detail.grid(row=1, column=0, sticky="ew", padx=SP_MD, pady=(0, SP_MD))
        self._highlight_nav()

    def _highlight_nav(self):
        for key, btn in self.nav_buttons.items():
            if key == self._view:
                btn.configure(fg_color=MOCHA["surface0"], text_color=MOCHA["text"],
                              border_width=1, border_color=MOCHA["mauve"])
            else:
                btn.configure(fg_color="transparent", text_color=MOCHA["subtext1"],
                              border_width=0)

    # -- main area -----------------------------------------------------------
    def _build_main(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        self.main = main
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        top = ctk.CTkFrame(main, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=SP_XL, pady=(SP_XL, SP_SM))
        top.grid_columnconfigure(0, weight=1)
        titles = ctk.CTkFrame(top, fg_color="transparent")
        titles.grid(row=0, column=0, sticky="w")
        hour = datetime.now().hour
        greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
        self.eyebrow = ctk.CTkLabel(titles, text=greeting, font=(FONT, FS_BODY, "bold"),
                                    text_color=MOCHA["blue"], anchor="w")
        self.eyebrow.grid(row=0, column=0, sticky="w")
        self.view_title = ctk.CTkLabel(titles, text="Usage overview", font=(FONT, FS_H1, "bold"),
                                       text_color=MOCHA["text"], anchor="w")
        self.view_title.grid(row=1, column=0, sticky="w", pady=(0, 2))
        self.view_sub = ctk.CTkLabel(titles, text="Monitor every limit. Never miss a reset.",
                                     font=(FONT, FS_BODY), text_color=MOCHA["subtext0"], anchor="w")
        self.view_sub.grid(row=2, column=0, sticky="w")
        self.synced_label = ctk.CTkLabel(top, text="", font=(FONT, FS_SMALL),
                                         text_color=MOCHA["subtext0"])
        self.synced_label.grid(row=0, column=1, sticky="e", padx=(SP_SM, SP_MD))
        self.refresh_btn = ctk.CTkButton(
            top, text="↻  Refresh usage", width=132, height=40, corner_radius=R_SM,
            fg_color=MOCHA["mauve"], hover_color=MOCHA["lavender"],
            text_color=MOCHA["crust"], font=(FONT, FS_BODY, "bold"),
            command=self.refresh_now,
        )
        self.refresh_btn.grid(row=0, column=2, sticky="e")
        settings_btn = ctk.CTkButton(
            top, text="⚙", width=40, height=40, corner_radius=R_SM,
            fg_color=MOCHA["surface0"], hover_color=MOCHA["surface1"],
            text_color=MOCHA["text"], font=(FONT, 16), command=self.open_settings,
        )
        settings_btn.grid(row=0, column=3, sticky="e", padx=(SP_SM, 0))
        self.settings_tip = ToolTip(settings_btn, "Open settings")

        # Alarm banner (hidden until a reset fires)
        self.banner = ctk.CTkFrame(main, fg_color=MOCHA["red"], corner_radius=R_MD)
        self.banner.grid_columnconfigure(0, weight=1)
        self.banner_label = ctk.CTkLabel(self.banner, text="", font=(FONT, FS_TITLE, "bold"),
                                         text_color=MOCHA["crust"], anchor="w")
        self.banner_label.grid(row=0, column=0, sticky="w", padx=SP_LG, pady=SP_MD)
        ctk.CTkButton(self.banner, text="Snooze", width=80, height=30, corner_radius=R_SM,
                      fg_color=MOCHA["surface0"], hover_color=MOCHA["surface1"], font=(FONT, FS_BODY),
                      text_color=MOCHA["text"], command=self._snooze_alarm).grid(row=0, column=1, padx=(0, SP_XS), pady=SP_MD)
        ctk.CTkButton(self.banner, text="Stop alarm", width=104, height=30, corner_radius=R_SM,
                      fg_color=MOCHA["crust"], hover_color=MOCHA["mantle"], font=(FONT, FS_BODY, "bold"),
                      text_color=MOCHA["text"], command=self.acknowledge_alarm).grid(row=0, column=2, padx=SP_MD, pady=SP_MD)

        self.body = ctk.CTkScrollableFrame(main, fg_color="transparent")
        self.body.grid(row=2, column=0, sticky="nsew", padx=SP_LG, pady=(0, SP_MD))
        self.body.grid_columnconfigure(0, weight=1)

        self._build_dashboard_view()
        self._build_activity_view()
        self.show_view("dashboard")

    def _build_dashboard_view(self):
        self.dash = ctk.CTkFrame(self.body, fg_color="transparent")
        self.dash.grid_columnconfigure(0, weight=1)

        insights = ctk.CTkFrame(self.dash, fg_color=MOCHA["mantle"], corner_radius=R_LG,
                                border_width=1, border_color=MOCHA["surface1"])
        insights.grid(row=0, column=0, sticky="ew", padx=SP_SM, pady=(SP_XS, SP_MD))
        insights.grid_columnconfigure(0, weight=1, uniform="insight")
        insights.grid_columnconfigure(2, weight=1, uniform="insight")
        self.stat_next = InsightMetric(insights, "Next reset in", "⏱", MOCHA["blue"])
        self.stat_next.grid(row=0, column=0, sticky="ew", padx=SP_LG)
        ctk.CTkFrame(insights, width=1, height=56, fg_color=MOCHA["surface1"]).grid(
            row=0, column=1, pady=SP_MD)
        self.stat_highest = InsightMetric(insights, "Highest pressure", "↗", MOCHA["red"])
        self.stat_highest.grid(row=0, column=2, sticky="ew", padx=SP_LG)

        providers = ctk.CTkFrame(self.dash, fg_color="transparent")
        providers.grid(row=1, column=0, sticky="ew", padx=SP_SM, pady=(0, SP_MD))
        providers.grid_columnconfigure(0, weight=1, uniform="prov")
        providers.grid_columnconfigure(1, weight=1, uniform="prov")
        self.provider_cards = {
            "claude": ProviderCard(providers, "claude"),
            "codex": ProviderCard(providers, "codex"),
        }
        providers.grid_rowconfigure(0, weight=1)
        self.provider_cards["claude"].grid(row=0, column=0, sticky="nsew", padx=(0, SP_SM))
        self.provider_cards["codex"].grid(row=0, column=1, sticky="nsew", padx=(SP_SM, 0))

        lower = ctk.CTkFrame(self.dash, fg_color="transparent")
        lower.grid(row=2, column=0, sticky="ew", padx=SP_SM, pady=(0, SP_SM))
        lower.grid_columnconfigure(0, weight=5, uniform="lower")
        lower.grid_columnconfigure(1, weight=4, uniform="lower")

        metrics = ctk.CTkFrame(lower, fg_color="transparent")
        metrics.grid(row=0, column=0, sticky="nsew", padx=(0, SP_SM))
        for i in range(3):
            metrics.grid_columnconfigure(i, weight=1, uniform="metric")
        self.stat_active = StatCard(metrics, "Active windows", "↻", MOCHA["blue"])
        self.stat_active.grid(row=0, column=0, sticky="nsew", padx=(0, SP_XS))
        self.stat_healthy = StatCard(metrics, "Healthy windows", "✓", MOCHA["green"])
        self.stat_healthy.grid(row=0, column=1, sticky="nsew", padx=SP_XS)
        self.stat_pressure = StatCard(metrics, "High pressure", "!", MOCHA["yellow"])
        self.stat_pressure.grid(row=0, column=2, sticky="nsew", padx=(SP_XS, 0))

        act = ctk.CTkFrame(lower, fg_color=MOCHA["mantle"], corner_radius=R_LG,
                           border_width=1, border_color=MOCHA["surface1"])
        act.grid(row=0, column=1, sticky="nsew", padx=(SP_SM, 0))
        act.grid_columnconfigure(0, weight=1)
        head = ctk.CTkFrame(act, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=SP_LG, pady=(SP_MD, SP_XS))
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(head, text="↻  Recent reset activity", font=(FONT, FS_TITLE, "bold"),
                     text_color=MOCHA["text"], anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkButton(head, text="View all", width=76, height=28, corner_radius=R_SM,
                      fg_color="transparent", hover_color=MOCHA["surface0"],
                      text_color=MOCHA["mauve"], font=(FONT, FS_SMALL),
                      command=lambda: self.show_view("activity")).grid(row=0, column=1, sticky="e")
        self.recent_list = ctk.CTkFrame(act, fg_color="transparent")
        self.recent_list.grid(row=1, column=0, sticky="ew", padx=SP_MD, pady=(0, SP_MD))
        self.recent_list.grid_columnconfigure(0, weight=1)

    def _build_activity_view(self):
        self.activity = ctk.CTkFrame(self.body, fg_color="transparent")
        self.activity.grid_columnconfigure(0, weight=1)
        self.activity_list = ctk.CTkFrame(self.activity, fg_color=MOCHA["mantle"], corner_radius=R_LG,
                                          border_width=1, border_color=MOCHA["surface1"])
        self.activity_list.grid(row=0, column=0, sticky="ew", padx=SP_SM, pady=SP_XS)
        self.activity_list.grid_columnconfigure(0, weight=1)

    def show_view(self, key: str):
        self._view = key
        self.dash.grid_forget()
        self.activity.grid_forget()
        if key == "dashboard":
            self.eyebrow.grid()
            self.view_title.configure(text="Usage overview")
            self.view_sub.configure(text="Monitor every limit. Never miss a reset.")
            self.dash.grid(row=0, column=0, sticky="nsew")
        else:
            self.eyebrow.grid_remove()
            self.view_title.configure(text="Activity")
            self.view_sub.configure(text="Every usage reset AIUsageTracker has detected.")
            self.activity.grid(row=0, column=0, sticky="nsew")
            self._render_activity()
        self._highlight_nav()

    # -- activity rendering --------------------------------------------------
    def _event_rows(self, parent, events, limit, pad=SP_MD):
        for child in parent.winfo_children():
            child.destroy()
        if not events:
            ctk.CTkLabel(parent, text="No resets yet - you'll be alarmed the moment a window rolls over.",
                         font=(FONT, FS_SMALL), text_color=MOCHA["overlay0"], anchor="w").grid(sticky="ew", padx=SP_SM, pady=pad)
            return
        for i, ev in enumerate(reversed(events[-limit:])):
            prov = ev.get("provider", "")
            row = ctk.CTkFrame(parent, fg_color=MOCHA["surface0"], corner_radius=R_SM)
            row.grid(row=i, column=0, sticky="ew", pady=3)
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(row, text="", image=tile_image(prov, 22)).grid(row=0, column=0, padx=(SP_MD, SP_SM), pady=SP_SM)
            ctk.CTkLabel(row, text=f"{PROVIDER_TITLES.get(prov, prov)}  ·  {ev.get('label','')} reset",
                         font=(FONT, FS_BODY), text_color=MOCHA["text"], anchor="w").grid(row=0, column=1, sticky="w")
            when = ev.get("detected_at", "")
            try:
                when = datetime.fromisoformat(when).astimezone().strftime("%d %b, %I:%M %p")
            except Exception:
                pass
            ctk.CTkLabel(row, text=when, font=(FONT, FS_SMALL), text_color=MOCHA["subtext0"]).grid(row=0, column=2, sticky="e", padx=SP_LG)

    def _render_recent(self):
        self._event_rows(self.recent_list, load_events(200), 5)

    def _render_activity(self):
        self._event_rows(self.activity_list, load_events(200), 100, pad=SP_XL)

    # -- queue / event handling ---------------------------------------------
    def _drain_queue(self):
        if self._closing:
            return
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
        self._drain_after_id = self.after(200, self._drain_queue)

    def _on_snapshot(self, snap: ProviderSnapshot):
        for key in [k for k in self._rows if k.startswith(f"{snap.provider}:")]:
            self._rows.pop(key, None)
        card = self.provider_cards.get(snap.provider)
        if card:
            card.update(snap, self.settings, self._set_window_alarm, self._rows)
        if snap.ok:
            ts = snap.fetched_at.timestamp()
            for w in snap.windows:
                samples = self._burn_samples.setdefault(w.key, deque(maxlen=20))
                samples.append((ts, w.utilization))
        self._recompute_summary()
        if snap.provider in self._refresh_pending:
            self._refresh_pending.discard(snap.provider)
            if not self._refresh_pending:
                self._finish_refresh()

    def _recompute_summary(self):
        snaps = self.poller.snapshots()
        windows = []
        for s in snaps.values():
            if s.ok:
                windows.extend(s.windows)

        if windows:
            hi = max(windows, key=lambda w: w.utilization)
            eta_str = self._burn_eta(hi.key)
            subtitle = f"{hi.label} · {PROVIDER_TITLES.get(hi.provider, hi.provider)}"
            if eta_str:
                subtitle += f" · {eta_str}"
            self.stat_highest.set(f"{hi.utilization:.0f}%", subtitle,
                                  SEVERITY_COLOR.get(hi.severity, MOCHA["text"]))
            self._update_tray_icon(hi.utilization)
            healthy = sum(w.utilization <= 50 for w in windows)
            pressure = sum(w.utilization >= 70 for w in windows)
            self.stat_active.set(str(len(windows)), "Across both providers", MOCHA["text"])
            self.stat_healthy.set(str(healthy), "At or below 50%", MOCHA["green"])
            self.stat_pressure.set(str(pressure), "Above 70% usage",
                                   MOCHA["yellow"] if pressure else MOCHA["green"])
        else:
            self.stat_highest.set("--", "waiting for data")
            self.stat_active.set("--", "Waiting for data")
            self.stat_healthy.set("--", "Waiting for data")
            self.stat_pressure.set("--", "Waiting for data")

        self._update_next_reset(windows)

        enabled = [p for p, on in self.settings.get("providers", {}).items() if on]
        oks = [p for p in enabled if snaps.get(p) and snaps[p].ok]
        if enabled and len(oks) == len(enabled):
            self.conn_dot.configure(fg_color=MOCHA["green"])
            self.conn_text.configure(text="Connected", text_color=MOCHA["green"])
            self.conn_detail.configure(text="All systems operational")
        else:
            bad = [PROVIDER_TITLES.get(p, p) for p in enabled if p not in oks]
            col = MOCHA["yellow"] if oks else MOCHA["red"]
            self.conn_dot.configure(fg_color=col)
            self.conn_text.configure(text="Needs attention" if bad else "Connecting...",
                                     text_color=col)
            self.conn_detail.configure(text=(", ".join(bad) + " offline") if bad else "Waiting for first sync")

        times = [s.fetched_at for s in snaps.values() if s.ok]
        if times:
            self._last_sync_ts = max(t.timestamp() for t in times)
            self._update_freshness()
            latest = max(times).astimezone()
            self.conn_detail.configure(text=f"Synced {latest:%I:%M:%S %p}")
        self._render_recent()

    def _burn_eta(self, key: str) -> str:
        """Estimate time until 100% based on recent utilization rate of change."""
        samples = self._burn_samples.get(key)
        if not samples or len(samples) < 2:
            return ""
        oldest_ts, oldest_pct = samples[0]
        newest_ts, newest_pct = samples[-1]
        dt = newest_ts - oldest_ts
        if dt < 30:
            return ""
        rate = (newest_pct - oldest_pct) / dt  # % per second
        if rate <= 0.0001:
            return ""
        remaining = 100.0 - newest_pct
        if remaining <= 0:
            return "at limit"
        secs = remaining / rate
        if secs > 86400:
            return ""
        h, rem = divmod(int(secs), 3600)
        m = rem // 60
        if h:
            return f"~{h}h {m}m to limit"
        return f"~{m}m to limit"

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
                               f"{w.label} · {PROVIDER_TITLES.get(w.provider, w.provider)}",
                               MOCHA["blue"])
        else:
            self.stat_next.set("--", "no upcoming resets")

    def _on_reset(self, events: list[ResetEvent]):
        for e in events:
            self._snoozed.discard(e.key)
        alarming = [e for e in events
                    if config.window_alarm_enabled(self.settings, e.key)
                    and e.key not in self._snoozed]
        self._render_recent()
        if self._view == "activity":
            self._render_activity()
        if not alarming:
            return
        self._last_alarming_keys = [e.key for e in alarming]
        self._pending_resets.extend(alarming)
        if self._reset_debounce_id is not None:
            try:
                self.after_cancel(self._reset_debounce_id)
            except Exception:
                pass
        self._reset_debounce_id = self.after(5000, self._fire_aggregated_reset)

    def _fire_aggregated_reset(self):
        self._reset_debounce_id = None
        if not self._pending_resets:
            return
        events = list(self._pending_resets)
        self._pending_resets.clear()
        labels = ", ".join(f"{PROVIDER_TITLES.get(e.provider, e.provider)} {e.label}" for e in events)
        self.banner_label.configure(text=f"Usage reset: {labels}")
        self.banner.grid(row=1, column=0, sticky="ew", padx=SP_XL, pady=(SP_XS, SP_XS))
        if self.settings.get("alarm_sound", True):
            self._alarm.start(loop=self.settings.get("alarm_loop", True),
                              sound=self.settings.get("alarm_sound_name", DEFAULT_SOUND))
        if self.settings.get("toast", True):
            notify("AI Usage Reset", f"{labels} has reset.")
        webhook_url = self.settings.get("webhook_url", "")
        if webhook_url:
            send_webhook(webhook_url, "AI Usage Reset", f"{labels} has reset.")
        try:
            self.deiconify(); self.lift(); self.focus_force()
        except Exception:
            pass

    def _on_warn(self, w: LimitWindow):
        if self.settings.get("toast", True):
            notify("Usage nearing limit",
                   f"{PROVIDER_TITLES.get(w.provider, w.provider)} {w.label} at {w.utilization:.0f}%")

    def _update_freshness(self):
        if self._last_sync_ts is None:
            return
        import time
        ago = int(time.time() - self._last_sync_ts)
        poll_interval = int(self.settings.get("poll_seconds", 180))
        stale = ago > poll_interval * 2
        if ago < 60:
            txt = f"Synced {ago}s ago"
        elif ago < 3600:
            txt = f"Synced {ago // 60}m {ago % 60}s ago"
        else:
            txt = f"Synced {ago // 3600}h ago"
        if stale:
            txt += "  ·  STALE"
            color = MOCHA["yellow"]
        else:
            color = MOCHA["subtext0"]
        self.synced_label.configure(text=txt, text_color=color)

    # -- periodic tick -------------------------------------------------------
    def _tick(self):
        if self._closing:
            return
        for row in self._rows.values():
            try:
                row.refresh_countdown()
            except Exception:
                pass
        self._update_next_reset()
        self._update_freshness()
        self._tick_after_id = self.after(1000, self._tick)

    # -- actions -------------------------------------------------------------
    def refresh_now(self):
        self._refresh_pending = {
            provider for provider, enabled in self.settings.get("providers", {}).items()
            if enabled
        }
        if hasattr(self, "refresh_btn") and self.refresh_btn.winfo_exists():
            self.refresh_btn.configure(text="Refreshing…", state="disabled")
        self.poller.poll_now()
        if self._refresh_timeout_id is not None:
            try:
                self.after_cancel(self._refresh_timeout_id)
            except Exception:
                pass
        self._refresh_timeout_id = self.after(15000, self._finish_refresh)
        if not self._refresh_pending:
            self._finish_refresh()

    def _finish_refresh(self):
        self._refresh_pending.clear()
        if self._refresh_timeout_id is not None:
            try:
                self.after_cancel(self._refresh_timeout_id)
            except Exception:
                pass
            self._refresh_timeout_id = None
        if hasattr(self, "refresh_btn") and self.refresh_btn.winfo_exists():
            self.refresh_btn.configure(text="↻  Refresh usage", state="normal")

    def acknowledge_alarm(self):
        self._alarm.stop()
        self.banner.grid_forget()

    def _snooze_alarm(self):
        self._snoozed.update(self._last_alarming_keys)
        self._alarm.stop()
        self.banner.grid_forget()

    def _set_window_alarm(self, key: str, on: bool):
        self.settings.setdefault("window_alarms", {})[key] = bool(on)
        config.save_settings(self.settings)

    def open_settings(self):
        try:
            dialog_open = self._settings_dialog is not None and self._settings_dialog.winfo_exists()
        except Exception:
            dialog_open = False
            self._settings_dialog = None
        if dialog_open:
            self._settings_dialog.deiconify()
            self._settings_dialog.lift()
            self._settings_dialog.focus_force()
            return
        self._settings_dialog = SettingsDialog(self)

    def apply_settings(self, new: dict):
        previous_theme = ui_theme.normalize_theme(self.settings.get("theme"))
        new["theme"] = ui_theme.normalize_theme(new.get("theme", previous_theme))
        self.settings.update(new)
        config.save_settings(self.settings)
        self.poller.settings = self.settings
        self.poller.poll_now()
        if new["theme"] != previous_theme:
            if self._theme_rebuild_id is not None:
                try:
                    self.after_cancel(self._theme_rebuild_id)
                except Exception:
                    pass
            self._theme_rebuild_id = self.after(200, self._rebuild_for_theme)

    def _rebuild_for_theme(self):
        """Recreate the widget tree so a newly selected theme applies live."""
        self._theme_rebuild_id = None
        active_view = self._view
        if hasattr(self, "settings_tip"):
            self.settings_tip._hide()
        for row in self._rows.values():
            if hasattr(row, "alarm_tip"):
                row.alarm_tip._hide()
        for child in (getattr(self, "sidebar", None), getattr(self, "main", None)):
            if child is not None:
                try:
                    child.destroy()
                except Exception:
                    pass
        self.settings["theme"] = ui_theme.apply_theme(self.settings.get("theme"))
        ctk.set_appearance_mode(ui_theme.appearance_for(self.settings["theme"]))
        _IMG_CACHE.clear()
        self.configure(fg_color=MOCHA["base"])
        self._rows.clear()
        self._build_sidebar()
        self._build_main()
        self.show_view(active_view)
        for snap in self.poller.snapshots().values():
            self._on_snapshot(snap)
        self._recompute_summary()
        self._chrome_after_id = self.after(30, self._apply_windows_chrome)

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

    def _update_tray_icon(self, utilization_pct: float):
        if self._tray is not None:
            try:
                self._tray.icon = icons.tray_status_icon(64, utilization_pct)
                self._tray.title = f"AI Usage: {utilization_pct:.0f}%"
            except Exception:
                pass

    def _show_window(self):
        self.deiconify(); self.lift(); self.focus_force()

    def hide_to_tray(self):
        if self._tray is not None:
            self.withdraw()
        else:
            self.quit_app()

    def quit_app(self):
        self._closing = True
        try:
            for after_id in (self._theme_rebuild_id, self._refresh_timeout_id,
                             self._drain_after_id, self._tick_after_id,
                             self._chrome_after_id, self._reset_debounce_id):
                if after_id is not None:
                    try:
                        self.after_cancel(after_id)
                    except Exception:
                        pass
            if hasattr(self, "settings_tip"):
                self.settings_tip._hide()
            for row in self._rows.values():
                if hasattr(row, "alarm_tip"):
                    row.alarm_tip._hide()
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


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, app: App):
        super().__init__(app)
        self.app = app
        self.title("Settings")
        self.geometry("470x700")
        self.minsize(440, 620)
        self.configure(fg_color=MOCHA["base"])
        self.transient(app)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Escape>", lambda _event: self._close())
        self.bind("<Control-s>", lambda _event: self._save())
        try:
            self.after(60, self.grab_set)
        except Exception:
            pass
        self._chrome_after_id = self.after(
            100, lambda: set_windows_chrome(self, app.settings.get("theme", ui_theme.DEFAULT_THEME)))
        s = app.settings

        wrap = ctk.CTkScrollableFrame(self, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=SP_SM, pady=SP_SM)

        ctk.CTkLabel(wrap, text="Settings", font=(FONT, FS_H1, "bold"),
                     text_color=MOCHA["text"]).pack(anchor="w", padx=SP_MD, pady=(SP_SM, 0))
        ctk.CTkLabel(wrap, text="Make AIUsageTracker work the way you do.",
                     font=(FONT, FS_BODY), text_color=MOCHA["subtext0"]).pack(
                         anchor="w", padx=SP_MD, pady=(0, SP_MD))

        self.var_claude = ctk.BooleanVar(value=s["providers"].get("claude", True))
        self.var_codex = ctk.BooleanVar(value=s["providers"].get("codex", True))
        self.var_alarm = ctk.BooleanVar(value=s.get("alarm_sound", True))
        self.var_loop = ctk.BooleanVar(value=s.get("alarm_loop", True))
        self.var_toast = ctk.BooleanVar(value=s.get("toast", True))
        self.var_min = ctk.BooleanVar(value=s.get("start_minimized", False))

        # Appearance ------------------------------------------------------
        card = self._section(wrap, "Appearance")
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=SP_MD, pady=(SP_MD, SP_SM))
        ctk.CTkLabel(row, text="Theme", font=(FONT, FS_BODY, "bold"),
                     text_color=MOCHA["text"]).pack(side="left")
        self.theme_menu = ctk.CTkOptionMenu(
            row, values=list(ui_theme.THEME_CHOICES), width=150, corner_radius=R_SM,
            fg_color=MOCHA["surface0"], button_color=MOCHA["surface1"],
            button_hover_color=MOCHA["surface2"], text_color=MOCHA["text"],
            command=self._update_theme_preview,
        )
        self.theme_menu.set(ui_theme.theme_label(s.get("theme")))
        self.theme_menu.pack(side="right")
        preview_row = ctk.CTkFrame(card, fg_color="transparent")
        preview_row.pack(fill="x", padx=SP_MD)
        self.theme_swatches = []
        for _ in range(5):
            swatch = ctk.CTkFrame(preview_row, width=28, height=28, corner_radius=R_SM)
            swatch.pack(side="left", padx=(0, SP_XS))
            swatch.pack_propagate(False)
            self.theme_swatches.append(swatch)
        self.theme_desc = ctk.CTkLabel(card, text="", font=(FONT, FS_TINY),
                                       text_color=MOCHA["subtext0"], anchor="w")
        self.theme_desc.pack(fill="x", padx=SP_MD, pady=(SP_SM, SP_MD))
        self._update_theme_preview(self.theme_menu.get())

        # Providers -------------------------------------------------------
        card = self._section(wrap, "Providers")
        self._check(card, "Track Claude", self.var_claude, "Read Claude usage from your Claude Code login.")
        self._check(card, "Track Codex", self.var_codex, "Read Codex usage from your Codex CLI login.")

        # Alerts ----------------------------------------------------------
        card = self._section(wrap, "Alerts")
        self._check(card, "Audible alarm on reset", self.var_alarm, "Play a sound the moment a tracked window resets.")
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(anchor="w", fill="x", padx=SP_MD, pady=(SP_XS, 2))
        ctk.CTkLabel(row, text="Alarm sound", font=(FONT, FS_BODY), text_color=MOCHA["text"]).pack(side="left")
        self.sound_menu = ctk.CTkOptionMenu(row, values=SOUND_NAMES, width=130, corner_radius=R_SM,
                                            fg_color=MOCHA["surface0"], button_color=MOCHA["surface1"],
                                            button_hover_color=MOCHA["surface2"], text_color=MOCHA["text"],
                                            command=lambda _v: None)
        self.sound_menu.set(s.get("alarm_sound_name", DEFAULT_SOUND))
        self.sound_menu.pack(side="left", padx=SP_SM)
        ctk.CTkButton(row, text="▶ Test", width=64, height=28, corner_radius=R_SM,
                      fg_color=MOCHA["surface1"], hover_color=MOCHA["surface2"], text_color=MOCHA["text"],
                      font=(FONT, FS_SMALL), command=lambda: preview(self.sound_menu.get())).pack(side="left")
        ctk.CTkLabel(card, text="Pick a tone, then Test to hear it.", font=(FONT, FS_TINY),
                     text_color=MOCHA["subtext0"], anchor="w").pack(anchor="w", padx=SP_MD, pady=(0, SP_XS))
        self._check(card, "Loop until acknowledged", self.var_loop, "Repeat the alarm until you click Stop alarm.")
        self._check(card, "Toast notifications", self.var_toast, "Also show a native Windows toast on reset.")

        # General ---------------------------------------------------------
        card = self._section(wrap, "General")
        self._check(card, "Start minimized to tray", self.var_min, "Launch straight to the system tray.")
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(anchor="w", fill="x", padx=SP_MD, pady=SP_XS)
        ctk.CTkLabel(row, text="Poll interval", font=(FONT, FS_BODY), text_color=MOCHA["text"]).pack(side="left")
        self.poll_entry = ctk.CTkEntry(row, width=72, corner_radius=R_SM)
        self.poll_entry.insert(0, str(s.get("poll_seconds", config.DEFAULT_POLL_SECONDS)))
        self.poll_entry.pack(side="left", padx=SP_SM)
        ctk.CTkLabel(row, text=f"seconds (min {config.MIN_POLL_SECONDS})", font=(FONT, FS_SMALL),
                     text_color=MOCHA["subtext0"]).pack(side="left")
        ctk.CTkLabel(card, text="Claude rate-limits faster polling; 180s is the safe floor.",
                     font=(FONT, FS_TINY), text_color=MOCHA["subtext0"], anchor="w").pack(anchor="w", padx=SP_MD, pady=(0, SP_XS))
        self.poll_error = ctk.CTkLabel(card, text="", font=(FONT, FS_TINY, "bold"),
                                       text_color=MOCHA["red"], anchor="w")
        self.poll_error.pack(anchor="w", padx=SP_MD, pady=(0, SP_SM))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=SP_LG, pady=SP_MD)
        ctk.CTkButton(btns, text="Cancel", width=90, height=34, corner_radius=R_SM,
                      fg_color=MOCHA["surface0"], hover_color=MOCHA["surface1"], text_color=MOCHA["text"],
                      command=self._close).pack(side="right", padx=(SP_SM, 0))
        ctk.CTkButton(btns, text="Save changes", width=130, height=34, corner_radius=R_SM,
                      fg_color=MOCHA["green"], text_color=MOCHA["crust"], hover_color=MOCHA["teal"],
                      font=(FONT, FS_BODY, "bold"), command=self._save).pack(side="right")

    def _section(self, parent, title):
        ctk.CTkLabel(parent, text=title.upper(), font=(FONT, FS_TINY, "bold"),
                     text_color=MOCHA["subtext0"]).pack(anchor="w", padx=SP_MD, pady=(SP_MD, SP_XS))
        card = ctk.CTkFrame(parent, fg_color=MOCHA["mantle"], corner_radius=R_MD,
                            border_width=1, border_color=MOCHA["surface1"])
        card.pack(fill="x", padx=SP_SM, pady=(0, SP_XS))
        return card

    def _check(self, parent, text, var, hint):
        ctk.CTkCheckBox(parent, text=text, variable=var, text_color=MOCHA["text"],
                        font=(FONT, FS_BODY), fg_color=MOCHA["mauve"], hover_color=MOCHA["lavender"],
                        corner_radius=R_XS).pack(anchor="w", padx=SP_MD, pady=(SP_MD, 0))
        ctk.CTkLabel(parent, text=hint, font=(FONT, FS_TINY), text_color=MOCHA["subtext0"],
                     anchor="w", justify="left", wraplength=360).pack(anchor="w", padx=(SP_XL + 4, SP_MD), pady=(0, SP_XS))

    def _update_theme_preview(self, label):
        key = ui_theme.theme_key_from_label(label)
        palette = ui_theme.palette_for(key)
        colors = [palette["crust"], palette["surface0"], palette["mauve"],
                  palette["blue"], palette["green"]]
        for swatch, color in zip(self.theme_swatches, colors):
            swatch.configure(fg_color=color, border_width=1,
                             border_color=palette["surface2"])
        self.theme_desc.configure(text=ui_theme.description_for(key))

    def _close(self):
        if self.app._settings_dialog is self:
            self.app._settings_dialog = None
        if self._chrome_after_id is not None:
            try:
                self.after_cancel(self._chrome_after_id)
            except Exception:
                pass
            self._chrome_after_id = None
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _save(self):
        try:
            poll = int(self.poll_entry.get().strip())
        except ValueError:
            self.poll_error.configure(text="Enter a whole number of seconds.")
            self.poll_entry.focus_set()
            return
        if poll < config.MIN_POLL_SECONDS:
            self.poll_error.configure(text=f"Use {config.MIN_POLL_SECONDS} seconds or more to avoid rate limits.")
            self.poll_entry.focus_set()
            return
        self.poll_error.configure(text="")
        new_settings = {
            "theme": ui_theme.theme_key_from_label(self.theme_menu.get()),
            "providers": {"claude": self.var_claude.get(), "codex": self.var_codex.get()},
            "alarm_sound": self.var_alarm.get(),
            "alarm_sound_name": self.sound_menu.get(),
            "alarm_loop": self.var_loop.get(),
            "toast": self.var_toast.get(),
            "start_minimized": self.var_min.get(),
            "poll_seconds": poll,
        }
        app = self.app
        self._close()
        app.apply_settings(new_settings)


def main():
    app = App()
    app.run()


if __name__ == "__main__":
    main()
