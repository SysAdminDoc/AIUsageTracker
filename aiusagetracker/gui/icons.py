"""Application logo plus runtime-generated provider and control icons.

The app logo is loaded from the packaged brand asset. Supporting marks are drawn
with PIL at 4x supersampling and downscaled with LANCZOS for crisp anti-aliased
edges. Provider tiles are original geometric renderings used to identify each
source in the UI, not official trademarked asset files.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from .. import config
from .theme import MOCHA

SS = 4  # supersample factor

CLAUDE_ORANGE = (217, 119, 87, 255)   # Claude "clay" orange
CODEX_INK = (13, 13, 15, 255)         # OpenAI monochrome on near-black
WHITE = (255, 255, 255, 255)
APP_LOGO_PNG = "app-logo.png"
APP_LOGO_ICO = "app-logo.ico"
_APP_LOGO_MASTER: Image.Image | None = None


def _asset_path(name: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return root / "assets" / name


def _canvas(size: int):
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img), s


def _rounded_tile(d, s, fill):
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.26), fill=fill)


def claude_tile(size: int = 128) -> Image.Image:
    """Rounded clay-orange tile with a white sunburst (Claude)."""
    img, d, s = _canvas(size)
    _rounded_tile(d, s, CLAUDE_ORANGE)
    cx = cy = s / 2
    r_out, r_in, halfw = s * 0.33, s * 0.05, s * 0.028
    n = 12
    for i in range(n):
        a = 2 * math.pi * i / n
        dx, dy = math.cos(a), math.sin(a)
        px, py = -dy, dx
        tip = (cx + r_out * dx, cy + r_out * dy)
        bl = (cx + r_in * dx + halfw * px, cy + r_in * dy + halfw * py)
        br = (cx + r_in * dx - halfw * px, cy + r_in * dy - halfw * py)
        d.polygon([tip, bl, br], fill=WHITE)
    d.ellipse([cx - s * 0.055, cy - s * 0.055, cx + s * 0.055, cy + s * 0.055], fill=WHITE)
    return img.resize((size, size), Image.LANCZOS)


def codex_tile(size: int = 128) -> Image.Image:
    """Rounded near-black tile with a white hexafoil knot (OpenAI / Codex)."""
    img, d, s = _canvas(size)
    _rounded_tile(d, s, CODEX_INK)
    cx = cy = s / 2
    stroke = max(2, int(s * 0.05))
    petal_w, petal_h = s * 0.30, s * 0.40
    inner_gap = s * 0.10  # leaves the central hexagon hole
    for i in range(6):
        layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        x0, y0 = cx - petal_w / 2, cy - inner_gap - petal_h
        x1, y1 = cx + petal_w / 2, cy - inner_gap
        ld.ellipse([x0, y0, x1, y1], outline=WHITE, width=stroke)
        layer = layer.rotate(i * 60, center=(cx, cy), resample=Image.BICUBIC)
        img = Image.alpha_composite(img, layer)
    return img.resize((size, size), Image.LANCZOS)


def app_tile(size: int = 128) -> Image.Image:
    """Return the generated AIUsageTracker brand mark at the requested size."""
    global _APP_LOGO_MASTER
    if _APP_LOGO_MASTER is None:
        path = _asset_path(APP_LOGO_PNG)
        if path.exists():
            with Image.open(path) as source:
                _APP_LOGO_MASTER = source.convert("RGBA").copy()
    if _APP_LOGO_MASTER is not None:
        return _APP_LOGO_MASTER.resize((size, size), Image.LANCZOS)

    # Development fallback if the packaged asset is unavailable.
    img, d, s = _canvas(size)
    _rounded_tile(d, s, _hex(MOCHA["mauve"]))
    box = [s * 0.24, s * 0.26, s * 0.76, s * 0.78]
    d.arc(box, start=150, end=390, fill=(255, 255, 255, 90), width=max(3, s // 16))
    d.arc(box, start=150, end=312, fill=WHITE, width=max(3, s // 16))
    cx, cy = s / 2, s * 0.54
    ang = math.radians(312)
    tip = (cx + s * 0.20 * math.cos(ang), cy + s * 0.20 * math.sin(ang))
    d.line([(cx, cy), tip], fill=WHITE, width=max(3, s // 18))
    d.ellipse([cx - s * 0.05, cy - s * 0.05, cx + s * 0.05, cy + s * 0.05], fill=WHITE)
    return img.resize((size, size), Image.LANCZOS)


def bell_icon(size: int = 32, color: str = "#66d9e8", enabled: bool = True) -> Image.Image:
    """Small outlined bell for the per-window alarm control."""
    img, d, s = _canvas(size)
    rgba = _hex(color)
    stroke = max(4, int(s * 0.07))
    pts = [
        (s * 0.50, s * 0.18), (s * 0.40, s * 0.21),
        (s * 0.32, s * 0.34), (s * 0.32, s * 0.56),
        (s * 0.23, s * 0.70), (s * 0.77, s * 0.70),
        (s * 0.68, s * 0.56), (s * 0.68, s * 0.34),
        (s * 0.60, s * 0.21), (s * 0.50, s * 0.18),
    ]
    d.line(pts, fill=rgba, width=stroke, joint="curve")
    d.line([(s * 0.28, s * 0.70), (s * 0.72, s * 0.70)], fill=rgba, width=stroke)
    d.arc([s * 0.43, s * 0.68, s * 0.57, s * 0.83], start=0, end=180,
          fill=rgba, width=stroke)
    if not enabled:
        d.line([(s * 0.20, s * 0.20), (s * 0.80, s * 0.80)], fill=rgba,
               width=stroke + 1)
    return img.resize((size, size), Image.LANCZOS)


def _hex(h: str):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


def make_icon(size: int = 64) -> Image.Image:
    """Tray icon (the app mark)."""
    return app_tile(size)


_SEVERITY_COLORS = {
    "green": (76, 175, 80, 255),
    "yellow": (251, 192, 45, 255),
    "orange": (255, 152, 0, 255),
    "red": (244, 67, 54, 255),
}


def _severity_for_pct(pct: float) -> str:
    if pct >= 90:
        return "red"
    if pct >= 75:
        return "orange"
    if pct >= 50:
        return "yellow"
    return "green"


def tray_status_icon(size: int = 64, utilization_pct: float | None = None) -> Image.Image:
    """Render a tray icon colored by severity with usage % overlay text."""
    if utilization_pct is None:
        return app_tile(size)

    img, d, s = _canvas(size)
    severity = _severity_for_pct(utilization_pct)
    fill = _SEVERITY_COLORS[severity]
    _rounded_tile(d, s, fill)

    label = str(int(utilization_pct))
    try:
        from PIL import ImageFont
        font_size = int(s * 0.55) if len(label) <= 2 else int(s * 0.42)
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageDraw.Draw(img).getfont()

    bbox = d.textbbox((0, 0), label, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (s - tw) / 2 - bbox[0]
    y = (s - th) / 2 - bbox[1]
    d.text((x, y), label, fill=WHITE, font=font)

    return img.resize((size, size), Image.LANCZOS)


def ensure_ico() -> str:
    packaged = _asset_path(APP_LOGO_ICO)
    if packaged.exists():
        return str(packaged)

    path = config.data_dir() / "app-logo-v1.ico"
    if not path.exists():
        try:
            base = app_tile(256)
            base.save(str(path), sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (256, 256)])
        except Exception:
            return ""
    return str(path)
