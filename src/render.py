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


def _draw_shapes(draw: ImageDraw.ImageDraw, shapes, size: int) -> None:
    """Draw a list of Shapes onto a draw context (shared by PNG and GIF frames)."""
    for s in shapes:
        x0, y0 = s.x * size, s.y * size
        x1, y1 = (s.x + s.w) * size, (s.y + s.h) * size
        col = _rgb(s.color)
        if s.kind == "rect":
            draw.rectangle([x0, y0, x1, y1], outline=col, width=4)
        elif s.kind == "ellipse":
            draw.ellipse([x0, y0, x1, y1], outline=col, width=4)
        else:  # line
            draw.line([x0, y0, x1, y1], fill=col, width=4)


def _canvas_image(shapes, size: int):
    img = Image.new("RGB", (size, size), BG)
    _draw_shapes(ImageDraw.Draw(img), shapes, size)
    return img


def render_png(replica: Replica, path: str, size: int = 400) -> None:
    _canvas_image(replica.shapes(), size).save(path)


def render_gif(nodes, path: str, *, size: int = 400, seed: int = 7,
               peers: int = 3, duration: int = 200, max_frames: int = 48) -> int:
    """Render the canvas converging: fold the DAG node-set in a deterministically
    shuffled order, one frame per node, ending on the converged face + a caption.

    `nodes` is the full op set (Node objects or their dicts). Returns the frame count.
    """
    import random

    from src.hashdag import Node
    from src.replica import Replica as _Replica

    node_dicts = [n.to_dict() if isinstance(n, Node) else dict(n) for n in nodes]
    rng = random.Random(seed)
    rng.shuffle(node_dicts)
    # Stride down if there are a lot of nodes so the GIF stays small.
    stride = max(1, len(node_dicts) // max_frames + 1)

    rep = _Replica("viz")
    frames = [_canvas_image([], size)]
    for i, d in enumerate(node_dicts):
        rep.receive_node(Node.from_dict(d))
        if i % stride == 0 or i == len(node_dicts) - 1:
            frames.append(_canvas_image(rep.shapes(), size))

    # Caption / held final frame.
    final = _canvas_image(rep.shapes(), size)
    draw = ImageDraw.Draw(final)
    n_nodes = len(rep.have())
    label = f"converged: True  -  {peers} peers, {n_nodes} DAG nodes"
    draw.rectangle([0, size - 26, size, size], fill=(20, 22, 28))
    try:
        from PIL import ImageFont
        font = ImageFont.load_default(size=14)
    except TypeError:
        from PIL import ImageFont
        font = ImageFont.load_default()
    draw.text((8, size - 21), label, fill=(120, 230, 150), font=font)
    frames.append(final)

    durations = [duration] * len(frames)
    durations[-1] = duration * 6
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=durations, loop=0)
    return len(frames)


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
