import random
import pytest

from src.backends.lww import LWWReplica
from src.core.scene import PixelCell


class TestLWWBasics:
    def test_paint_appears_in_scene(self):
        r = LWWReplica("a")
        r.apply_local({"x": 0.5, "y": 0.5, "color": "red"})
        scene = r.scene()
        assert len(scene.drawables) == 1
        assert isinstance(scene.drawables[0], PixelCell)
        assert scene.drawables[0].color == "red"

    def test_overwrite_same_pixel(self):
        r = LWWReplica("a")
        r.apply_local({"x": 0.0, "y": 0.0, "color": "red"})
        r.apply_local({"x": 0.0, "y": 0.0, "color": "blue"})
        scene = r.scene()
        assert len(scene.drawables) == 1
        assert scene.drawables[0].color == "blue"

    def test_digest_stable(self):
        r = LWWReplica("a")
        r.apply_local({"x": 0.1, "y": 0.2, "color": "green"})
        assert r.digest() == r.digest()


class TestLWWConvergence:
    def _sync(self, replicas):
        all_ops = [op for r in replicas for op in r.delta_since(None)]
        rng = random.Random(0)
        for r in replicas:
            delivery = list(all_ops) + list(all_ops)
            rng.shuffle(delivery)
            for op in delivery:
                r.apply_remote(op)

    def test_two_replicas_converge(self):
        a = LWWReplica("a")
        b = LWWReplica("b")
        a.apply_local({"x": 0.1, "y": 0.1, "color": "red"})
        b.apply_local({"x": 0.9, "y": 0.9, "color": "blue"})
        self._sync([a, b])
        assert a.digest() == b.digest()
        assert len(a.scene().drawables) == 2

    def test_concurrent_write_same_pixel_lww(self):
        a = LWWReplica("a")
        b = LWWReplica("b")
        a.apply_local({"x": 0.5, "y": 0.5, "color": "red"})
        b.apply_local({"x": 0.5, "y": 0.5, "color": "blue"})
        self._sync([a, b])
        assert a.digest() == b.digest()
        assert len(a.scene().drawables) == 1

    def test_fuzz_convergence(self):
        colors = ["red", "green", "blue", "yellow", "white"]
        for seed in range(30):
            rng = random.Random(seed)
            peers = [LWWReplica(f"p{i}") for i in range(3)]
            for _ in range(20):
                p = rng.choice(peers)
                p.apply_local({
                    "x": round(rng.random(), 2),
                    "y": round(rng.random(), 2),
                    "color": rng.choice(colors),
                })
            self._sync(peers)
            digests = [p.digest() for p in peers]
            assert all(d == digests[0] for d in digests), f"seed {seed}"

    def test_summary_is_none(self):
        r = LWWReplica("a")
        r.apply_local({"x": 0.5, "y": 0.5, "color": "red"})
        assert r.summary() is None

    def test_delta_since_returns_all_ops(self):
        r = LWWReplica("a")
        r.apply_local({"x": 0.1, "y": 0.1, "color": "red"})
        r.apply_local({"x": 0.5, "y": 0.5, "color": "blue"})
        ops = r.delta_since(None)
        assert len(ops) == 2

    def test_apply_remote_idempotent(self):
        a = LWWReplica("a")
        b = LWWReplica("b")
        a.apply_local({"x": 0.3, "y": 0.3, "color": "green"})
        ops = a.delta_since(None)
        b.apply_remote(ops[0])
        b.apply_remote(ops[0])
        assert len(b.scene().drawables) == 1
