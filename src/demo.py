"""Demos: a deterministic OR-Map + Merkle-DAG convergence proof, and a live
backend-free P2P mesh where peers draw shapes and converge — rendered to PNG.
"""

from __future__ import annotations

import asyncio
import random

from src.replica import Replica
from src.hashdag import Node
from src.mesh import PeerNode
from src.render import render_png, to_ascii


def _scene():
    """Three peers collaboratively draw a simple face out of shapes."""
    return {
        "alice": [("ellipse", 0.2, 0.2, 0.6, 0.6, "yellow")],            # face
        "bob":   [("ellipse", 0.35, 0.38, 0.08, 0.08, "blue"),          # left eye
                  ("ellipse", 0.57, 0.38, 0.08, 0.08, "blue")],          # right eye
        "cara":  [("line", 0.38, 0.62, 0.62, 0.62, "red"),              # mouth
                  ("rect", 0.1, 0.1, 0.8, 0.8, "black")],                # frame
    }


def convergence_proof(seed: int = 5) -> dict:
    rng = random.Random(seed)
    peers = [Replica(f"p{i}") for i in range(4)]
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


async def live_demo() -> dict:
    scene = _scene()
    nodes = {name: PeerNode(name) for name in scene}
    names = list(nodes)
    ports = {name: await nodes[name].start() for name in names}
    for i, name in enumerate(names):
        for j in range(i):
            await nodes[name].connect_to("127.0.0.1", ports[names[j]])
    await asyncio.sleep(0.2)

    for name, shapes in scene.items():
        for (kind, x, y, w, h, color) in shapes:
            await nodes[name].add_shape(kind, x, y, w, h, color)
    await asyncio.sleep(0.6)

    digest_set = {node.replica.digest() for node in nodes.values()}
    converged = len(digest_set) == 1
    board = nodes["alice"].replica
    result = {
        "converged": converged,
        "shapes": len(board.shapes()),
        "dag_nodes": len(board.have()),
        "replica": board,
    }
    for node in nodes.values():
        await node.stop()
    return result


def main() -> int:
    print("Decentralized Collaborative Canvas (OR-Map + Merkle-DAG)")
    print("=" * 56)
    proof = convergence_proof()
    print(f"[CRDT proof] {proof['peers']} peers, DAG nodes delivered "
          f"shuffled+duplicated")
    print(f"  converged: {proof['converged']}  "
          f"({proof['shapes']} shapes, {proof['dag_nodes']} DAG nodes)")

    live = asyncio.run(live_demo())
    print(f"[live P2P mesh] 3 peers draw a face (no backend, content-addressed sync)")
    print(f"  all peers converged: {live['converged']}  "
          f"({live['shapes']} shapes from {live['dag_nodes']} ops)")

    render_png(live["replica"], "out/canvas.png", size=400)
    print("  saved render to out/canvas.png")
    print("\nCollaborative drawing (ASCII preview):")
    print(to_ascii(live["replica"]))
    return 0 if (proof["converged"] and live["converged"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
