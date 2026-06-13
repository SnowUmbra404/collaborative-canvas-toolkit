"""Render the OR-Map of shapes to a PNG and an ASCII preview."""

from __future__ import annotations

from PIL import Image, ImageDraw

from src.replica import Replica

PALETTE = {
    "red": (220, 60, 60), "green": (70, 190, 90), "blue": (70, 130, 230),
    "yellow": (240, 210, 70), "magenta": (210, 80, 200), "cyan": (70, 200, 210),
    "orange": (240, 150, 50), "black": (30, 30, 36), "white": (235, 235, 235),
}
BG = (248, 249, 252)


def _rgb(c: str):
    return PALETTE.get(c, (60, 60, 60))


def render_png(replica: Replica, path: str, size: int = 400) -> None:
    img = Image.new("RGB", (size, size), BG)
    draw = ImageDraw.Draw(img)
    for s in replica.shapes():
        x0, y0 = s.x * size, s.y * size
        x1, y1 = (s.x + s.w) * size, (s.y + s.h) * size
        col = _rgb(s.color)
        if s.kind == "rect":
            draw.rectangle([x0, y0, x1, y1], outline=col, width=4)
        elif s.kind == "ellipse":
            draw.ellipse([x0, y0, x1, y1], outline=col, width=4)
        else:  # line
            draw.line([x0, y0, x1, y1], fill=col, width=4)
    img.save(path)


def to_ascii(replica: Replica, width: int = 48, height: int = 24) -> str:
    grid = [[" "] * width for _ in range(height)]
    for idx, s in enumerate(replica.shapes()):
        ch = s.kind[0].upper()
        x0 = int(s.x * width); y0 = int(s.y * height)
        x1 = int((s.x + s.w) * width); y1 = int((s.y + s.h) * height)
        x0, x1 = sorted((max(0, x0), min(width - 1, x1)))
        y0, y1 = sorted((max(0, y0), min(height - 1, y1)))
        if s.kind == "line":
            steps = max(2, max(x1 - x0, y1 - y0))
            for k in range(steps + 1):
                t = k / steps
                gx = min(width - 1, int(x0 + (x1 - x0) * t))
                gy = min(height - 1, int(y0 + (y1 - y0) * t))
                grid[gy][gx] = "L"
        else:
            for gx in range(x0, x1 + 1):
                grid[y0][gx] = ch; grid[y1][gx] = ch
            for gy in range(y0, y1 + 1):
                grid[gy][x0] = ch; grid[gy][x1] = ch
    return "\n".join("".join(r) for r in grid)
