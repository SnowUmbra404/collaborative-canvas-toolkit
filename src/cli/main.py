from __future__ import annotations

import argparse
import asyncio
import logging
import os
import random
import sys


def _run_demo(backend: str, out_dir: str, size: int, gif: bool) -> int:
    from src.demo import demo_lww, demo_rga, demo_ormap
    fn = {"lww": demo_lww, "rga": demo_rga, "ormap": demo_ormap}[backend]
    result = fn(out_dir=out_dir, size=size)
    print(f"[{backend}] converged={result['converged']}")
    for k, v in result.items():
        if k not in ("backend", "converged"):
            print(f"  {k}: {v}")
    if gif:
        from src.demo import live_demo
        from src.core.render import render_gif
        os.makedirs(out_dir, exist_ok=True)
        board = asyncio.run(live_demo())["replica"]
        nodes = list(board.dag.nodes.values())
        gif_path = os.path.join(out_dir, "converge.gif")
        n = render_gif(nodes, gif_path, peers=3)
        print(f"  saved convergence GIF -> {gif_path} ({n} frames, "
              f"{len(nodes)} DAG nodes shuffled into place)")
    return 0 if result["converged"] else 1


def _run_render(backend: str, out_dir: str, size: int) -> int:
    os.makedirs(out_dir, exist_ok=True)
    if backend == "lww":
        from src.backends.lww import LWWReplica
        from src.core.render import render_scene_png
        r = LWWReplica("render")
        rng = random.Random(1)
        for _ in range(50):
            r.apply_local({"x": round(rng.random(), 2), "y": round(rng.random(), 2),
                           "color": rng.choice(["red", "blue", "green", "yellow"])})
        path = os.path.join(out_dir, "render_lww.png")
        render_scene_png(r.scene(size), path, size)
    elif backend == "rga":
        from src.backends.rga import RGAReplica
        from src.core.render import render_scene_png
        r = RGAReplica("render")
        rng = random.Random(1)
        for _ in range(10):
            r.apply_local({"type": "stroke",
                           "points": [[round(rng.random(), 2), round(rng.random(), 2)],
                                      [round(rng.random(), 2), round(rng.random(), 2)]],
                           "color": rng.choice(["red", "blue", "green", "cyan"]),
                           "width": rng.randint(2, 6)})
        path = os.path.join(out_dir, "render_rga.png")
        render_scene_png(r.scene(size), path, size)
    else:
        from src.backends.ormap import ORMapReplica
        from src.core.render import render_scene_png
        r = ORMapReplica("render")
        r.add_shape("ellipse", 0.2, 0.2, 0.6, 0.6, "yellow")
        r.add_shape("rect", 0.1, 0.1, 0.8, 0.8, "blue")
        path = os.path.join(out_dir, "render_ormap.png")
        render_scene_png(r.scene(size), path, size)
    print(f"saved {path}")
    return 0


def _cmd_viz_dag(args) -> int:
    from src.demo import live_demo
    from src.backends.dag_viz import render_dag
    out_dir = args.out
    os.makedirs(out_dir, exist_ok=True)
    board = asyncio.run(live_demo())["replica"]
    nodes = list(board.dag.nodes.values())
    gif_path = os.path.join(out_dir, "dag.gif")
    n = render_dag(nodes, gif_path)
    print(f"  saved DAG growth GIF -> {gif_path} ({n} frames)")
    return 0


async def _run_peer(port, seeds, peer_id):
    from src.backends.ormap import ORMapReplica
    from src.core.transport import MeshNode
    replica = ORMapReplica(peer_id)
    node = MeshNode(replica)
    bound = await node.start()
    print(f"Peer {peer_id} listening on :{bound}")
    for seed in seeds:
        host, _, p = seed.partition(":")
        await node.connect_to(host, int(p))
        print(f"  joined {seed}")
    rng = random.Random(hash(peer_id) & 0xffff)
    kind = rng.choice(["rect", "ellipse", "line"])
    color = rng.choice(["red", "green", "blue", "yellow"])
    await node.apply_local({"type": "add", "kind": kind,
                            "x": rng.random() * 0.6, "y": rng.random() * 0.6,
                            "w": 0.25, "h": 0.25, "color": color})
    print(f"  drew a {color} {kind}; syncing. Ctrl-C to stop.")
    try:
        while True:
            await asyncio.sleep(2)
            print(f"[{peer_id}] {len(replica.shapes())} shapes / "
                  f"{len(replica.have())} DAG nodes")
    except (KeyboardInterrupt, asyncio.CancelledError):
        await node.stop()


def _cmd_peer(args) -> int:
    seeds = [s for s in (args.seeds.split(",") if args.seeds else []) if s]
    asyncio.run(_run_peer(args.port, seeds, args.id))
    return 0


def _cmd_web(args) -> int:
    import http.server
    import socketserver
    web_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "web"
    )
    web_dir = os.path.normpath(web_dir)
    os.chdir(web_dir)
    with socketserver.TCPServer((args.host, args.port),
                                http.server.SimpleHTTPRequestHandler) as httpd:
        print(f"Canvas UI at http://localhost:{args.port}/")
        httpd.serve_forever()
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="canvas-toolkit")
    parser.add_argument("--backend", choices=["lww", "rga", "ormap"], default="ormap")
    parser.add_argument("--out", default="out")
    parser.add_argument("--size", type=int, default=400)
    sub = parser.add_subparsers(dest="cmd")

    demo_p = sub.add_parser("demo", help="run convergence demo")
    demo_p.add_argument("--gif", action="store_true",
                        help="write out/<out>/converge.gif (OR-Map only)")

    sub.add_parser("render", help="render a sample canvas to PNG")

    vd = sub.add_parser("viz-dag", help="render OR-Map DAG growth as a GIF")
    vd.add_argument("--out", default="out", dest="out")

    pe = sub.add_parser("peer", help="run a P2P canvas node")
    pe.add_argument("--port", type=int, default=0)
    pe.add_argument("--seeds", default="", help="comma-separated host:port seeds")
    pe.add_argument("--id", default="peer")

    w = sub.add_parser("web", help="serve the browser canvas UI")
    w.add_argument("--host", default="0.0.0.0")
    w.add_argument("--port", type=int, default=8080)

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    if args.cmd == "demo":
        return _run_demo(args.backend, args.out, args.size, getattr(args, "gif", False))
    elif args.cmd == "render":
        return _run_render(args.backend, args.out, args.size)
    elif args.cmd == "viz-dag":
        return _cmd_viz_dag(args)
    elif args.cmd == "peer":
        return _cmd_peer(args)
    elif args.cmd == "web":
        return _cmd_web(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
