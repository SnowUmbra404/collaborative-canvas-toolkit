"""Decentralized Collaborative Canvas — CLI.

  viz-dag           render the DAG growth as a GIF
  demo               convergence proof + live P2P mesh drawing + PNG render
  peer  --port --seeds --id   run a backend-free P2P canvas node
  web   --port       serve the browser canvas UI
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import random


def _cmd_demo(args) -> int:
    from src.demo import main as demo_main
    rc = demo_main()
    if getattr(args, "gif", False):
        from src.demo import live_demo
        from src.render import render_gif
        os.makedirs("out", exist_ok=True)
        board = asyncio.run(live_demo())["replica"]
        nodes = list(board.dag.nodes.values())
        n = render_gif(nodes, "out/converge.gif", peers=3)
        print(f"  saved convergence GIF -> out/converge.gif ({n} frames, "
              f"{len(nodes)} DAG nodes shuffled into place)")
    return rc


def _cmd_viz_dag(args) -> int:
    from src.demo import live_demo
    from src.viz_dag import render_dag
    os.makedirs("out", exist_ok=True)
    board = asyncio.run(live_demo())["replica"]
    nodes = list(board.dag.nodes.values())
    n = render_dag(nodes, "out/dag.gif")
    print(f"  saved DAG growth GIF -> out/dag.gif ({n} frames)")
    return 0


async def _run_peer(port, seeds, peer_id):
    from src.mesh import PeerNode
    node = PeerNode(peer_id)
    bound = await node.start("0.0.0.0", port)
    print(f"Peer {peer_id} listening on :{bound}")
    for seed in seeds:
        host, _, p = seed.partition(":")
        await node.connect_to(host, int(p))
        print(f"  joined {seed}")
    rng = random.Random(hash(peer_id) & 0xffff)
    kind = rng.choice(["rect", "ellipse", "line"])
    color = rng.choice(["red", "green", "blue", "yellow"])
    await node.add_shape(kind, rng.random() * 0.6, rng.random() * 0.6, 0.25, 0.25, color)
    print(f"  drew a {color} {kind}; syncing. Ctrl-C to stop.")
    try:
        while True:
            await asyncio.sleep(2)
            print(f"[{peer_id}] {len(node.replica.shapes())} shapes / "
                  f"{len(node.replica.have())} DAG nodes")
    except (KeyboardInterrupt, asyncio.CancelledError):
        await node.stop()


def _cmd_peer(args) -> int:
    seeds = [s for s in (args.seeds.split(",") if args.seeds else []) if s]
    asyncio.run(_run_peer(args.port, seeds, args.id))
    return 0


def _cmd_web(args) -> int:
    import http.server
    import socketserver
    web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
    os.chdir(web_dir)
    with socketserver.TCPServer((args.host, args.port),
                                http.server.SimpleHTTPRequestHandler) as httpd:
        print(f"Canvas UI at http://localhost:{args.port}/")
        httpd.serve_forever()
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Decentralized Collaborative Canvas")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("demo", help="convergence proof + live mesh + render")
    d.add_argument("--gif", action="store_true",
                   help="also write out/converge.gif (canvas materializing op-by-op)")
    d.set_defaults(func=_cmd_demo)

    vd = sub.add_parser("viz-dag", help="render the DAG growth as a GIF")
    vd.set_defaults(func=_cmd_viz_dag)

    pe = sub.add_parser("peer", help="run a backend-free P2P canvas node")
    pe.add_argument("--port", type=int, default=0)
    pe.add_argument("--seeds", default="", help="comma-separated host:port seeds")
    pe.add_argument("--id", default="peer")
    pe.set_defaults(func=_cmd_peer)

    w = sub.add_parser("web", help="serve the browser canvas UI")
    w.add_argument("--host", default="0.0.0.0")
    w.add_argument("--port", type=int, default=8080)
    w.set_defaults(func=_cmd_web)

    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
