"""Generate the app / tray icon at runtime (no binary assets committed)."""
from __future__ import annotations

from PIL import Image, ImageDraw

from .. import config
from .theme import MOCHA


def make_icon(size: int = 64, accent: str = MOCHA["mauve"]) -> Image.Image:
    """A rounded-square gauge glyph."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = int(size * 0.08)
    radius = int(size * 0.22)
    d.rounded_rectangle([pad, pad, size - pad, size - pad], radius=radius,
                        fill=MOCHA["crust"])
    # gauge arc
    box = [int(size * 0.22), int(size * 0.24), int(size * 0.78), int(size * 0.80)]
    d.arc(box, start=150, end=390, fill=MOCHA["surface2"], width=max(3, size // 14))
    d.arc(box, start=150, end=300, fill=accent, width=max(3, size // 14))
    # needle
    cx, cy = size / 2, int(size * 0.52)
    d.ellipse([cx - size * 0.05, cy - size * 0.05, cx + size * 0.05, cy + size * 0.05],
              fill=accent)
    return img


def ensure_ico() -> str:
    """Write a multi-size .ico to the data dir for the window titlebar."""
    path = config.data_dir() / "app.ico"
    if not path.exists():
        try:
            base = make_icon(256)
            base.save(str(path), sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (256, 256)])
        except Exception:
            return ""
    return str(path)
