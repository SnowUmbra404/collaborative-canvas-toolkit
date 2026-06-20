from __future__ import annotations

import asyncio
import os
import random

from src.backends.ormap import ORMapReplica
from src.backends.hashdag import Node
from src.backends.lww import LWWReplica
from src.backends.rga import RGAReplica
from src.core.transport import MeshNode
from src.core.render import render_scene_png, scene_to_ascii, render_convergence_gif, scene_to_image
from src.core.scene import Scene


def convergence_proof(seed: int = 5) -> dict:
    rng = random.Random(seed)
    peers = [ORMapReplica(f"p{i}") for i in range(4)]
    kinds = ["rect", "ellipse", "line"]
    colors = ["red", "green", "blue", "yellow"]
    for _ in range(22):
        p = rng.choice(peers)
        sh = p.shapes()
        r = rng.random()
        if sh and r < 0.25:
            p.remove_shape(rng.choice(sh).id)
        elif sh and r < 0.55:
            p.set_props(rng.choice(sh).id, x=round(rng.random(), 3),
                        color=rng.choice(colors))
        else:
            p.add_shape(rng.choice(kinds), round(rng.random(), 3),
                        round(rng.random(), 3), 0.2, 0.2, rng.choice(colors))
    nodes = [n.to_dict() for p in peers for n in p.dag.nodes.values()]
    for p in peers:
        delivery = list(nodes) + rng.sample(nodes, len(nodes) // 2)
        rng.shuffle(delivery)
        for d in delivery:
            p.receive_node(Node.from_dict(d))
    digests = [p.digest() for p in peers]
    return {
        "peers": len(peers),
        "converged": all(d == digests[0] for d in digests),
        "shapes": len(peers[0].shapes()),
        "dag_nodes": len(peers[0].have()),
    }


def _ormap_face():
    return {
        "alice": [("ellipse", 0.2, 0.2, 0.6, 0.6, "yellow")],
        "bob":   [("ellipse", 0.35, 0.38, 0.08, 0.08, "blue"),
                  ("ellipse", 0.57, 0.38, 0.08, 0.08, "blue")],
        "cara":  [("line", 0.38, 0.62, 0.62, 0.62, "red"),
                  ("rect", 0.1, 0.1, 0.8, 0.8, "black")],
    }


async def live_demo() -> dict:
    face = _ormap_face()
    replicas = {name: ORMapReplica(name) for name in face}
    mesh_nodes = {name: MeshNode(replicas[name]) for name in face}
    names = list(face)
    ports = {name: await mesh_nodes[name].start() for name in names}
    for i, name in enumerate(names):
        for j in range(i):
            await mesh_nodes[name].connect_to("127.0.0.1", ports[names[j]])
    await asyncio.sleep(0.2)

    for name, shapes in face.items():
        for (kind, x, y, w, h, color) in shapes:
            await mesh_nodes[name].apply_local({
                "type": "add", "kind": kind,
                "x": x, "y": y, "w": w, "h": h, "color": color,
            })
    await asyncio.sleep(0.6)

    digest_set = {replicas[name].digest() for name in names}
    converged = len(digest_set) == 1
    board = replicas["alice"]
    result = {
        "converged": converged,
        "shapes": len(board.shapes()),
        "dag_nodes": len(board.have()),
        "replica": board,
    }
    for mn in mesh_nodes.values():
        await mn.stop()
    return result


def demo_lww(out_dir: str = "out", size: int = 400) -> dict:
    rng = random.Random(42)
    colors = ["red", "green", "blue", "yellow", "cyan", "magenta", "white"]
    peers = [LWWReplica(f"p{i}") for i in range(3)]
    scenes = []
    for _ in range(30):
        p = rng.choice(peers)
        p.apply_local({
            "x": round(rng.random(), 2),
            "y": round(rng.random(), 2),
            "color": rng.choice(colors),
        })
        scenes.append(p.scene(size))

    all_ops = [op for p in peers for op in p.delta_since(None)]
    for p in peers:
        delivery = list(all_ops)
        rng.shuffle(delivery)
        for op in delivery:
            p.apply_remote(op)

    digests = [p.digest() for p in peers]
    converged = all(d == digests[0] for d in digests)
    os.makedirs(out_dir, exist_ok=True)
    render_convergence_gif(scenes, os.path.join(out_dir, "lww_convergence.gif"),
                           size=size, label=f"LWW converged: {converged}")
    render_scene_png(peers[0].scene(size), os.path.join(out_dir, "lww_canvas.png"), size)
    return {"backend": "lww", "converged": converged, "pixels": len(peers[0].scene().drawables)}


def demo_rga(out_dir: str = "out", size: int = 400) -> dict:
    rng = random.Random(42)
    colors = ["red", "green", "blue", "yellow", "cyan", "orange", "white"]
    peers = [RGAReplica(f"p{i}") for i in range(3)]
    scenes = []
    for _ in range(20):
        p = rng.choice(peers)
        p.apply_local({
            "type": "stroke",
            "points": [[round(rng.random(), 2), round(rng.random(), 2)],
                       [round(rng.random(), 2), round(rng.random(), 2)]],
            "color": rng.choice(colors),
            "width": rng.randint(1, 5),
        })
        scenes.append(p.scene(size))

    all_ops = [op for p in peers for op in p.delta_since(None)]
    for p in peers:
        delivery = list(all_ops)
        rng.shuffle(delivery)
        for op in delivery:
            p.apply_remote(op)

    digests = [p.digest() for p in peers]
    converged = all(d == digests[0] for d in digests)
    os.makedirs(out_dir, exist_ok=True)
    render_convergence_gif(scenes, os.path.join(out_dir, "rga_convergence.gif"),
                           size=size, label=f"RGA converged: {converged}")
    render_scene_png(peers[0].scene(size), os.path.join(out_dir, "rga_canvas.png"), size)
    return {"backend": "rga", "converged": converged, "strokes": len(peers[0].scene().drawables)}


def demo_ormap(out_dir: str = "out", size: int = 400) -> dict:
    rng = random.Random(5)
    peers = [ORMapReplica(f"p{i}") for i in range(3)]
    kinds = ["rect", "ellipse", "line"]
    colors = ["red", "green", "blue", "yellow", "cyan"]
    scenes = []
    for _ in range(20):
        p = rng.choice(peers)
        sh = p.shapes()
        if sh and rng.random() < 0.2:
            p.remove_shape(rng.choice(sh).id)
        else:
            p.add_shape(rng.choice(kinds), round(rng.random(), 3),
                        round(rng.random(), 3), 0.2, 0.2, rng.choice(colors))
        scenes.append(p.scene(size))

    all_ops = [op for p in peers for op in p.delta_since(None)]
    for p in peers:
        delivery = list(all_ops)
        rng.shuffle(delivery)
        for op in delivery:
            p.apply_remote(op)

    digests = [p.digest() for p in peers]
    converged = all(d == digests[0] for d in digests)
    os.makedirs(out_dir, exist_ok=True)
    render_convergence_gif(scenes, os.path.join(out_dir, "ormap_convergence.gif"),
                           size=size, label=f"OR-Map converged: {converged}")
    render_scene_png(peers[0].scene(size), os.path.join(out_dir, "ormap_canvas.png"), size)
    return {"backend": "ormap", "converged": converged, "shapes": len(peers[0].shapes())}


def main() -> int:
    print("collaborative-canvas-toolkit")
    print("=" * 30)
    proof = convergence_proof()
    print(f"[OR-Map proof] {proof['peers']} peers, shuffled+duplicated delivery")
    print(f"  converged: {proof['converged']}  "
          f"({proof['shapes']} shapes, {proof['dag_nodes']} DAG nodes)")

    live = asyncio.run(live_demo())
    print(f"[OR-Map live mesh] 3 peers draw a face")
    print(f"  converged: {live['converged']}  "
          f"({live['shapes']} shapes from {live['dag_nodes']} ops)")

    board = live["replica"]
    os.makedirs("out", exist_ok=True)
    render_scene_png(board.scene(400), "out/canvas.png", 400)
    print("  saved render to out/canvas.png")
    print("\nCollaborative drawing (ASCII preview):")
    print(scene_to_ascii(board.scene(), 48, 24))
    return 0 if (proof["converged"] and live["converged"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
