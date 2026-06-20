from __future__ import annotations

import random

from PIL import Image, ImageDraw, ImageFont

from src.core.render import scene_to_image, scene_to_ascii
from src.core.scene import Scene


def render_png(replica, path: str, size: int = 400) -> None:
    scene_to_image(replica.scene(size), size).save(path)


def render_gif(nodes, path: str, *, size: int = 400, seed: int = 7,
               peers: int = 3, duration: int = 200, max_frames: int = 48) -> int:
    from src.backends.hashdag import Node
    from src.replica import Replica as _Replica

    node_dicts = [n.to_dict() if isinstance(n, Node) else dict(n) for n in nodes]
    rng = random.Random(seed)
    rng.shuffle(node_dicts)
    stride = max(1, len(node_dicts) // max_frames + 1)

    rep = _Replica("viz")
    frames = [scene_to_image(Scene(width=size, height=size, drawables=[]), size)]
    for i, d in enumerate(node_dicts):
        rep.receive_node(Node.from_dict(d))
        if i % stride == 0 or i == len(node_dicts) - 1:
            frames.append(scene_to_image(rep.scene(size), size))

    final = scene_to_image(rep.scene(size), size)
    draw = ImageDraw.Draw(final)
    n_nodes = len(rep.have())
    label = f"converged: True  -  {peers} peers, {n_nodes} DAG nodes"
    draw.rectangle([0, size - 26, size, size], fill=(20, 22, 28))
    try:
        font = ImageFont.load_default(size=14)
    except TypeError:
        font = ImageFont.load_default()
    draw.text((8, size - 21), label, fill=(120, 230, 150), font=font)
    frames.append(final)

    durations = [duration] * len(frames)
    durations[-1] = duration * 6
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=durations, loop=0)
    return len(frames)


def to_ascii(replica, width: int = 48, height: int = 24) -> str:
    return scene_to_ascii(replica.scene(), width, height)
