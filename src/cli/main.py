from __future__ import annotations

import argparse
import os
import sys


def _run_demo(backend: str, out_dir: str, size: int) -> int:
    from src.demo import demo_lww, demo_rga, demo_ormap
    fn = {"lww": demo_lww, "rga": demo_rga, "ormap": demo_ormap}[backend]
    result = fn(out_dir=out_dir, size=size)
    print(f"[{backend}] converged={result['converged']}")
    for k, v in result.items():
        if k not in ("backend", "converged"):
            print(f"  {k}: {v}")
    return 0 if result["converged"] else 1


def _run_render(backend: str, out_dir: str, size: int) -> int:
    os.makedirs(out_dir, exist_ok=True)
    if backend == "lww":
        from src.backends.lww import LWWReplica
        from src.core.render import render_scene_png
        r = LWWReplica("render")
        import random
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
        import random
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
        from src.replica import Replica
        from src.render import render_png
        r = Replica("render")
        r.add_shape("ellipse", 0.2, 0.2, 0.6, 0.6, "yellow")
        r.add_shape("rect", 0.1, 0.1, 0.8, 0.8, "blue")
        path = os.path.join(out_dir, "render_ormap.png")
        render_png(r, path, size)
    print(f"saved {path}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="canvas-toolkit")
    parser.add_argument("--backend", choices=["lww", "rga", "ormap"], default="ormap")
    parser.add_argument("--out", default="out")
    parser.add_argument("--size", type=int, default=400)
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("demo", help="run convergence demo")
    sub.add_parser("render", help="render a sample canvas to PNG")
    args = parser.parse_args(argv)

    if args.cmd == "demo":
        return _run_demo(args.backend, args.out, args.size)
    elif args.cmd == "render":
        return _run_render(args.backend, args.out, args.size)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
