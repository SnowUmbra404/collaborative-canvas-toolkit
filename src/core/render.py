from __future__ import annotations

import random

from PIL import Image, ImageDraw, ImageFont

from src.core.scene import Scene, Shape, Stroke, PixelCell, Drawable

PALETTE = {
    "red": (220, 60, 60), "green": (70, 190, 90), "blue": (70, 130, 230),
    "yellow": (240, 210, 70), "magenta": (210, 80, 200), "cyan": (70, 200, 210),
    "orange": (240, 150, 50), "black": (30, 30, 36), "white": (235, 235, 235),
    "purple": (150, 80, 220), "pink": (240, 120, 180), "teal": (40, 180, 170),
    "navy": (30, 60, 150), "gold": (220, 180, 40),
}
BG = (248, 249, 252)


def _rgb(c: str) -> tuple:
    return PALETTE.get(c, (60, 60, 60))


def _draw_drawable(draw: ImageDraw.ImageDraw, d: Drawable, size: int) -> None:
    if isinstance(d, Shape):
        x0, y0 = d.x * size, d.y * size
        x1, y1 = (d.x + d.w) * size, (d.y + d.h) * size
        col = _rgb(d.color)
        if d.kind == "rect":
            draw.rectangle([x0, y0, x1, y1], outline=col, width=4)
        elif d.kind == "ellipse":
            draw.ellipse([x0, y0, x1, y1], outline=col, width=4)
        else:
            draw.line([x0, y0, x1, y1], fill=col, width=4)
    elif isinstance(d, Stroke):
        pts = [(p[0] * (size - 1), p[1] * (size - 1)) for p in d.points]
        col = _rgb(d.color)
        if len(pts) >= 2:
            draw.line(pts, fill=col, width=max(1, d.width), joint="curve")
        elif len(pts) == 1:
            x, y = pts[0]
            r = max(1, d.width)
            draw.ellipse([x - r, y - r, x + r, y + r], fill=col)
    elif isinstance(d, PixelCell):
        cell_w = size / 32
        x0, y0 = d.x * size, d.y * size
        x1, y1 = x0 + cell_w, y0 + cell_w
        draw.rectangle([x0, y0, x1, y1], fill=_rgb(d.color))


def scene_to_image(scene: Scene, size: int | None = None) -> Image.Image:
    sz = size or max(scene.width, scene.height, 400)
    img = Image.new("RGB", (sz, sz), BG)
    draw = ImageDraw.Draw(img)
    for d in scene.drawables:
        _draw_drawable(draw, d, sz)
    return img


def render_scene_png(scene: Scene, path: str, size: int = 400) -> None:
    scene_to_image(scene, size).save(path)


def scene_to_ascii(scene: Scene, width: int = 48, height: int = 24) -> str:
    grid = [[" "] * width for _ in range(height)]
    marks = "#*+oxv.@%="
    for i, d in enumerate(scene.drawables):
        if isinstance(d, Shape):
            ch = d.kind[0].upper()
            x0 = int(d.x * width); y0 = int(d.y * height)
            x1 = int((d.x + d.w) * width); y1 = int((d.y + d.h) * height)
            x0, x1 = sorted((max(0, x0), min(width - 1, x1)))
            y0, y1 = sorted((max(0, y0), min(height - 1, y1)))
            if d.kind == "line":
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
        elif isinstance(d, Stroke):
            ch = marks[i % len(marks)]
            pts = d.points
            for j in range(len(pts) - 1):
                sx0, sy0 = pts[j]
                sx1, sy1 = pts[j + 1]
                steps = max(2, int(max(abs(sx1 - sx0), abs(sy1 - sy0)) * width))
                for s in range(steps + 1):
                    t = s / steps
                    gx = min(width - 1, int((sx0 + (sx1 - sx0) * t) * width))
                    gy = min(height - 1, int((sy0 + (sy1 - sy0) * t) * height))
                    grid[gy][gx] = ch
        elif isinstance(d, PixelCell):
            gx = min(width - 1, int(d.x * width))
            gy = min(height - 1, int(d.y * height))
            grid[gy][gx] = "P"
    return "\n".join("".join(r) for r in grid)


def render_convergence_gif(
    frames_scenes: list[Scene],
    path: str,
    size: int = 400,
    duration: int = 200,
    label: str = "",
) -> int:
    frames = [scene_to_image(s, size) for s in frames_scenes]
    if not frames:
        return 0
    final = frames[-1].copy()
    draw = ImageDraw.Draw(final)
    draw.rectangle([0, size - 26, size, size], fill=(20, 22, 28))
    try:
        font = ImageFont.load_default(size=14)
    except TypeError:
        font = ImageFont.load_default()
    draw.text((8, size - 21), label or "converged", fill=(120, 230, 150), font=font)
    frames.append(final)
    durations = [duration] * len(frames)
    durations[-1] = duration * 6
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=durations, loop=0)
    return len(frames)
