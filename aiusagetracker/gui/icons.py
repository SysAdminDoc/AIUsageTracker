"""Runtime-generated icons and brand tiles (no binary assets committed).

All marks are drawn with PIL at 4x supersampling and downscaled with LANCZOS for
crisp anti-aliased edges. The provider tiles are original geometric renderings in
each brand's colour and motif (Claude sunburst, OpenAI hexafoil) used to identify
the provider in the UI - not official trademarked asset files.
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw

from .. import config
from .theme import MOCHA

SS = 4  # supersample factor

CLAUDE_ORANGE = (217, 119, 87, 255)   # Claude "clay" orange
CODEX_INK = (13, 13, 15, 255)         # OpenAI monochrome on near-black
WHITE = (255, 255, 255, 255)


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
    """App mark: mauve rounded tile with a white gauge arc + needle."""
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


def _hex(h: str):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


def make_icon(size: int = 64) -> Image.Image:
    """Tray icon (the app mark)."""
    return app_tile(size)


def ensure_ico() -> str:
    path = config.data_dir() / "app.ico"
    if not path.exists():
        try:
            base = app_tile(256)
            base.save(str(path), sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (256, 256)])
        except Exception:
            return ""
    return str(path)
