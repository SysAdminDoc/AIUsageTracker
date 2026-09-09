#!/usr/bin/env python3
"""Capture AIUsageTracker on an isolated Windows desktop."""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import traceback
import uuid


DESKTOP_ACCESS = 0x000F01FF
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_UNICODE_ENVIRONMENT = 0x00000400
WAIT_TIMEOUT = 0x00000102
UOI_NAME = 2


class StartupInfo(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.POINTER(wintypes.BYTE)),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class ProcessInformation(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


def configure_api():
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32.CreateProcessW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.BOOL,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.LPCWSTR,
        ctypes.POINTER(StartupInfo),
        ctypes.POINTER(ProcessInformation),
    ]
    kernel32.CreateProcessW.restype = wintypes.BOOL
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    user32.CreateDesktopW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
    ]
    user32.CreateDesktopW.restype = wintypes.HANDLE
    user32.CloseDesktop.argtypes = [wintypes.HANDLE]
    return kernel32, user32


def current_desktop_name() -> str:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    desktop = user32.GetThreadDesktop(kernel32.GetCurrentThreadId())
    required = wintypes.DWORD()
    user32.GetUserObjectInformationW(desktop, UOI_NAME, None, 0, ctypes.byref(required))
    buffer = ctypes.create_unicode_buffer(max(2, required.value // 2 + 1))
    if not user32.GetUserObjectInformationW(
        desktop,
        UOI_NAME,
        buffer,
        ctypes.sizeof(buffer),
        ctypes.byref(required),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return buffer.value


def set_dpi_awareness() -> None:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        user32.SetProcessDPIAware()


def pump(window, milliseconds: int = 850) -> None:
    deadline = time.monotonic() + milliseconds / 1000
    while time.monotonic() < deadline:
        window.update()
        time.sleep(0.015)


def capture_hwnd(hwnd: int, destination: Path) -> None:
    from PIL import Image, ImageStat

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL
    user32.GetWindowDC.argtypes = [wintypes.HWND]
    user32.GetWindowDC.restype = wintypes.HDC
    user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
    user32.PrintWindow.restype = wintypes.BOOL
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user32.ReleaseDC.restype = ctypes.c_int
    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
    gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
    gdi32.SelectObject.restype = wintypes.HANDLE
    gdi32.BitBlt.argtypes = [
        wintypes.HDC,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.HDC,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.DWORD,
    ]
    gdi32.BitBlt.restype = wintypes.BOOL
    gdi32.GetDIBits.restype = ctypes.c_int
    gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise ctypes.WinError(ctypes.get_last_error())
    width = rect.right - rect.left
    height = rect.bottom - rect.top

    class BitmapInfoHeader(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    class BitmapInfo(ctypes.Structure):
        _fields_ = [
            ("bmiHeader", BitmapInfoHeader),
            ("bmiColors", wintypes.DWORD * 3),
        ]

    gdi32.GetDIBits.argtypes = [
        wintypes.HDC,
        wintypes.HBITMAP,
        wintypes.UINT,
        wintypes.UINT,
        wintypes.LPVOID,
        ctypes.POINTER(BitmapInfo),
        wintypes.UINT,
    ]

    window_dc = user32.GetWindowDC(hwnd)
    if not window_dc:
        raise ctypes.WinError(ctypes.get_last_error())
    memory_dc = gdi32.CreateCompatibleDC(window_dc)
    bitmap = gdi32.CreateCompatibleBitmap(window_dc, width, height)
    previous = gdi32.SelectObject(memory_dc, bitmap)
    try:
        rendered = user32.PrintWindow(hwnd, memory_dc, 2)
        if not rendered:
            copied = gdi32.BitBlt(
                memory_dc,
                0,
                0,
                width,
                height,
                window_dc,
                0,
                0,
                0x00CC0020 | 0x40000000,
            )
            if not copied:
                raise ctypes.WinError(ctypes.get_last_error())
        info = BitmapInfo()
        info.bmiHeader.biSize = ctypes.sizeof(BitmapInfoHeader)
        info.bmiHeader.biWidth = width
        info.bmiHeader.biHeight = -height
        info.bmiHeader.biPlanes = 1
        info.bmiHeader.biBitCount = 32
        info.bmiHeader.biCompression = 0
        pixels = ctypes.create_string_buffer(width * height * 4)
        scanlines = gdi32.GetDIBits(
            memory_dc,
            bitmap,
            0,
            height,
            pixels,
            ctypes.byref(info),
            0,
        )
        if scanlines != height:
            raise ctypes.WinError(ctypes.get_last_error())
        image = Image.frombuffer(
            "RGB",
            (width, height),
            pixels,
            "raw",
            "BGRX",
            0,
            1,
        ).copy()
    finally:
        gdi32.SelectObject(memory_dc, previous)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(hwnd, window_dc)
    if image.width < 80 or image.height < 50:
        raise RuntimeError(f"Unexpected capture size {image.width}x{image.height}")
    extrema = ImageStat.Stat(image.convert("RGB")).extrema
    if all(low == high for low, high in extrema):
        raise RuntimeError(f"Blank capture for {destination.name}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, "PNG", optimize=True)


def capture_window(window, destination: Path) -> None:
    pump(window, 900)
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    capture_hwnd(user32.GetAncestor(window.winfo_id(), 2), destination)


def find_process_window(process_id: int | None = None, title_match=None) -> tuple[int, str] | None:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    windows = []
    callback_type = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HWND,
        wintypes.LPARAM,
    )

    def visit(hwnd, _lparam):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if (
            process_id is not None
            and owner.value != process_id
        ) or not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        title = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title, len(title))
        if title_match and title_match not in title.value:
            return True
        windows.append((int(hwnd), title.value))
        return False

    callback = callback_type(visit)
    user32.EnumWindows(callback, 0)
    return windows[0] if windows else None



def run_worker(repo: Path, output: Path, executable: Path | None = None) -> int:
    output.mkdir(parents=True, exist_ok=True)
    report = {"desktop": current_desktop_name(), "captures": [], "assertions": []}
    if not report["desktop"].startswith("AIUsageTrackerReview-"):
        raise RuntimeError("Refusing any desktop not owned by this review")
    set_dpi_awareness()
    os.chdir(repo)
    sys.path.insert(0, str(repo))
    if executable:
        return capture_packaged(executable, output, report)
    from contextlib import ExitStack
    from unittest.mock import patch
    from aiusagetracker.gui import app as product
    from aiusagetracker.models import ResetEvent, now_utc

    def forbidden(*args, **kwargs):
        raise AssertionError("Offline demo attempted a live side effect")

    targets = ["config.load_settings", "config.save_settings", "config.data_dir",
               "token_stats.collect", "Poller.start", "notify", "send_webhook", "preview"]
    errors = []
    with ExitStack() as guards:
        for target in targets:
            guards.enter_context(patch.object(
                product if "." not in target else getattr(product, target.split(".")[0]),
                target.split(".")[-1], side_effect=forbidden))
        guards.enter_context(patch.object(product.App, "_start_tray", side_effect=forbidden))
        app = product.App(demo=True)
        app.report_callback_exception = lambda *exc: errors.append("".join(traceback.format_exception(*exc)))
        app.geometry("1360x840+0+0")
        app.after(700, lambda: None)
        pump(app, 1600)
        assert len(app._rows) == 4
        assert "306K" in app._token_total_label.cget("text")
        capture_window(app, output / "01-dashboard.png")
        report["captures"].append("01-dashboard.png")
        row = app._rows["claude:session"]
        row.alarm_btn.invoke()
        assert app.settings["window_alarms"]["claude:session"] is False
        row.alarm_btn.invoke()
        assert app.settings["window_alarms"]["claude:session"] is True
        app.refresh_btn.invoke()
        pump(app)
        assert app.refresh_btn.cget("state") == "normal"
        report["assertions"] += ["Four sample quota windows render", "Alarm toggle works in memory", "Refresh callback completes"]

        app.show_view("activity")
        pump(app)
        capture_window(app, output / "02-activity.png")
        report["captures"].append("02-activity.png")
        app._activity_filter.set("Claude")
        app._render_activity()
        assert len(app.activity_list.winfo_children()) == 2
        report["assertions"].append("Activity provider filter returns two example events")
        app.show_view("dashboard")
        app.open_settings()
        pump(app)
        dialog = app._settings_dialog
        dialog.geometry("500x850+50+30")
        pump(app)
        capture_window(dialog, output / "03-settings.png")
        report["captures"].append("03-settings.png")
        dialog.poll_entry.delete(0, "end")
        dialog.poll_entry.insert(0, "15")
        dialog._save()
        assert "180" in dialog.poll_error.cget("text")
        dialog.poll_entry.delete(0, "end")
        dialog.poll_entry.insert(0, "180")
        dialog.theme_menu.set("Daylight")
        dialog._save()
        pump(app, 1200)
        assert app.settings["theme"] == "daylight"
        capture_window(app, output / "04-daylight.png")
        report["captures"].append("04-daylight.png")
        report["assertions"] += ["Invalid poll interval rejected", "Settings save applies Daylight without disk writes"]

        app.apply_settings({"theme": "midnight"})
        pump(app, 1000)
        app.toggle_mini()
        app._mini.geometry("+30+30")
        app._recompute_summary()
        pump(app)
        assert app._mini.pct_label.cget("text") == "68%"
        capture_window(app._mini, output / "05-mini.png")
        report["captures"].append("05-mini.png")
        app.toggle_mini()
        event = ResetEvent("claude", "claude:session", "5-Hour Session", now_utc(), None, None, 68)
        app._on_reset([event])
        pump(app, 5500)
        assert "Usage reset" in app.banner_label.cget("text")
        capture_window(app, output / "06-reset-alert.png")
        report["captures"].append("06-reset-alert.png")
        app.acknowledge_alarm()
        assert not app.banner.winfo_ismapped()
        report["assertions"] += ["Mini widget shows highest pressure", "Aggregated reset banner and acknowledgement work without sound or network"]
        assert not errors, errors
        app.quit_app()
    report["callbackErrors"] = errors
    (output / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0


def capture_packaged(executable, output, report):
    with tempfile.TemporaryDirectory(prefix="aiusage-review-") as temporary:
        env = os.environ.copy()
        env.update(APPDATA=temporary, LOCALAPPDATA=str(Path(temporary) / "Local"),
                   USERPROFILE=temporary, HOMEDRIVE=Path(temporary).drive,
                   HOMEPATH=str(Path(temporary))[2:])
        for name, extra in [
            ("01-packaged-dashboard", []),
            ("02-packaged-activity", ["--demo-view", "activity"]),
            ("03-packaged-daylight", ["--demo-theme", "daylight"]),
            ("04-packaged-settings", ["--demo-view", "settings"]),
        ]:
            process = subprocess.Popen([str(executable), "--demo", *extra], env=env)
            try:
                deadline = time.monotonic() + 50
                found = None
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError(f"Packaged app exited {process.returncode}")
                    found = find_process_window()
                    if found and "AIUsageTracker v0.4.1" in found[1]:
                        break
                    found = None
                    time.sleep(.2)
                if not found:
                    raise TimeoutError("Packaged window missing")
                time.sleep(3)
                capture_target = find_process_window(title_match="Settings") if "settings" in name else found
                if capture_target is None:
                    raise AssertionError("Expected Settings window missing")
                capture_hwnd(capture_target[0], output / f"{name}.png")
                report["captures"].append(f"{name}.png")
                # WM_CLOSE targets a window on this private desktop. Demo has no tray.
                ctypes.windll.user32.PostMessageW(found[0], 0x0010, 0, 0)
                process.wait(timeout=15)
                assert process.returncode == 0
            finally:
                if process.poll() is None:
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
        assert not (Path(temporary) / "AIUsageTracker").exists(), "Demo wrote application data"
    report["assertions"] += ["Packaged app renders all four demo states and exits cleanly", "Demo creates no application-data directory"]
    (output / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0


def launch_worker(repo, output, executable=None):
    kernel32, user32 = configure_api()
    name = "AIUsageTrackerReview-" + uuid.uuid4().hex
    desktop = user32.CreateDesktopW(name, None, None, 0, DESKTOP_ACCESS, None)
    if not desktop:
        raise ctypes.WinError(ctypes.get_last_error())
    startup = StartupInfo()
    startup.cb = ctypes.sizeof(startup)
    startup.lpDesktop = "winsta0\\" + name
    process = ProcessInformation()
    args = [sys.executable, str(Path(__file__).resolve()), "--worker", "--repo", str(repo), "--output", str(output)]
    if executable:
        args += ["--executable", str(executable)]
    command = ctypes.create_unicode_buffer(subprocess.list2cmdline(args))
    try:
        if not kernel32.CreateProcessW(sys.executable, command, None, None, False,
                CREATE_NEW_PROCESS_GROUP | CREATE_UNICODE_ENVIRONMENT, None, str(repo),
                ctypes.byref(startup), ctypes.byref(process)):
            raise ctypes.WinError(ctypes.get_last_error())
        kernel32.CloseHandle(process.hThread)
        try:
            for _ in range(180):
                if kernel32.WaitForSingleObject(process.hProcess, 1000) != WAIT_TIMEOUT:
                    break
            else:
                kernel32.TerminateProcess(process.hProcess, 124)
                raise TimeoutError("Private desktop review timed out")
            code = wintypes.DWORD()
            kernel32.GetExitCodeProcess(process.hProcess, ctypes.byref(code))
            return code.value
        finally:
            kernel32.CloseHandle(process.hProcess)
    finally:
        user32.CloseDesktop(desktop)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executable", type=Path)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    try:
        result = run_worker(args.repo, args.output, args.executable) if args.worker else launch_worker(args.repo, args.output, args.executable)
        if result:
            error = args.output / "error.txt"
            if error.exists():
                print(error.read_text(encoding="utf-8"))
        raise SystemExit(result)
    except Exception:
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
