"""Tests for the convergence GIF renderer (Iteration 1)."""

from __future__ import annotations

from src.render import render_gif
from src.replica import Replica


def _face_nodes():
    """A small recognizable scene authored on one replica (the demo's face)."""
    r = Replica("alice")
    r.add_shape("ellipse", 0.2, 0.2, 0.6, 0.6, "yellow")     # face
    r.add_shape("ellipse", 0.35, 0.38, 0.08, 0.08, "blue")   # left eye
    r.add_shape("ellipse", 0.57, 0.38, 0.08, 0.08, "blue")   # right eye
    r.add_shape("line", 0.38, 0.62, 0.62, 0.62, "red")       # mouth
    r.add_shape("rect", 0.1, 0.1, 0.8, 0.8, "black")         # frame
    return list(r.dag.nodes.values()), r


def test_render_gif_writes_valid_gif(tmp_path):
    nodes, _ = _face_nodes()
    out = tmp_path / "converge.gif"
    n = render_gif(nodes, str(out), size=200, seed=7)
    assert out.exists() and out.stat().st_size > 0
    # GIF magic + multi-frame.
    head = out.read_bytes()[:6]
    assert head in (b"GIF89a", b"GIF87a")
    # blank start + one frame per node + caption.
    assert n == len(nodes) + 2 and n > 1


def test_final_state_equals_converged_shapes(tmp_path):
    nodes, source = _face_nodes()
    render_gif(nodes, str(tmp_path / "c.gif"), size=120, seed=3)
    # Fold the SAME nodes (shuffled) into a fresh replica; it must equal the source.
    import random
    from src.hashdag import Node
    rep = Replica("viz")
    shuffled = [n.to_dict() for n in nodes]
    random.Random(99).shuffle(shuffled)
    for d in shuffled:
        rep.receive_node(Node.from_dict(d))
    assert rep.digest() == source.digest()      # convergence regardless of order
    assert len(rep.shapes()) == 5


def test_render_gif_is_deterministic(tmp_path):
    nodes, _ = _face_nodes()
    a = tmp_path / "a.gif"
    b = tmp_path / "b.gif"
    render_gif(nodes, str(a), size=150, seed=7)
    render_gif(nodes, str(b), size=150, seed=7)
    assert a.read_bytes() == b.read_bytes()
