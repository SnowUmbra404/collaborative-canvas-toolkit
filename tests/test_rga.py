import random
import pytest

from src.backends.rga import RGAReplica
from src.core.scene import Stroke


class TestRGABasics:
    def test_stroke_appears_in_scene(self):
        r = RGAReplica("a")
        r.apply_local({"type": "stroke", "points": [[0.1, 0.1], [0.5, 0.5]], "color": "red", "width": 2})
        scene = r.scene()
        assert len(scene.drawables) == 1
        assert isinstance(scene.drawables[0], Stroke)
        assert scene.drawables[0].color == "red"

    def test_erase_removes_stroke(self):
        r = RGAReplica("a")
        op = r.apply_local({"type": "stroke", "points": [[0.0, 0.0], [1.0, 1.0]], "color": "blue", "width": 1})
        r.apply_local({"type": "erase", "id": op["id"]})
        assert len(r.scene().drawables) == 0

    def test_digest_stable(self):
        r = RGAReplica("a")
        r.apply_local({"type": "stroke", "points": [[0.2, 0.3]], "color": "green", "width": 3})
        assert r.digest() == r.digest()

    def test_order_preserved(self):
        r = RGAReplica("a")
        r.apply_local({"type": "stroke", "points": [[0.0, 0.0]], "color": "red", "width": 1})
        r.apply_local({"type": "stroke", "points": [[0.5, 0.5]], "color": "blue", "width": 1})
        scene = r.scene()
        assert scene.drawables[0].color == "red"
        assert scene.drawables[1].color == "blue"


class TestRGAConvergence:
    def _sync(self, replicas):
        all_ops = [op for r in replicas for op in r.delta_since({})]
        rng = random.Random(0)
        for r in replicas:
            delivery = list(all_ops) + list(all_ops)
            rng.shuffle(delivery)
            for op in delivery:
                r.apply_remote(op)

    def test_two_replicas_converge(self):
        a = RGAReplica("a")
        b = RGAReplica("b")
        a.apply_local({"type": "stroke", "points": [[0.1, 0.1], [0.2, 0.2]], "color": "red", "width": 1})
        b.apply_local({"type": "stroke", "points": [[0.8, 0.8], [0.9, 0.9]], "color": "blue", "width": 1})
        self._sync([a, b])
        assert a.digest() == b.digest()
        assert len(a.scene().drawables) == 2

    def test_concurrent_strokes_order_consistent(self):
        a = RGAReplica("a")
        b = RGAReplica("b")
        a.apply_local({"type": "stroke", "points": [[0.0, 0.0]], "color": "red", "width": 1})
        b.apply_local({"type": "stroke", "points": [[0.5, 0.5]], "color": "blue", "width": 1})
        self._sync([a, b])
        assert a.digest() == b.digest()

    def test_erase_propagates(self):
        a = RGAReplica("a")
        b = RGAReplica("b")
        op = a.apply_local({"type": "stroke", "points": [[0.3, 0.3]], "color": "green", "width": 2})
        b.apply_remote(op)
        a.apply_local({"type": "erase", "id": op["id"]})
        self._sync([a, b])
        assert a.digest() == b.digest()
        assert len(a.scene().drawables) == 0

    def test_apply_remote_idempotent(self):
        a = RGAReplica("a")
        b = RGAReplica("b")
        a.apply_local({"type": "stroke", "points": [[0.1, 0.1]], "color": "white", "width": 1})
        ops = a.delta_since({})
        b.apply_remote(ops[0])
        b.apply_remote(ops[0])
        assert len(b.scene().drawables) == 1

    def test_version_vector_delta(self):
        a = RGAReplica("a")
        a.apply_local({"type": "stroke", "points": [[0.0, 0.0]], "color": "red", "width": 1})
        a.apply_local({"type": "stroke", "points": [[0.5, 0.5]], "color": "blue", "width": 1})
        b = RGAReplica("b")
        first_op = a.delta_since({})[0]
        b.apply_remote(first_op)
        delta = a.delta_since(b.summary())
        assert len(delta) >= 1

    def test_fuzz_convergence(self):
        colors = ["red", "green", "blue", "yellow", "cyan"]
        for seed in range(30):
            rng = random.Random(seed)
            peers = [RGAReplica(f"p{i}") for i in range(3)]
            for _ in range(15):
                p = rng.choice(peers)
                scene = p.scene()
                if scene.drawables and rng.random() < 0.3:
                    ids = p.digest()
                    p.apply_local({"type": "erase", "id": list(rng.choice(ids))})
                else:
                    p.apply_local({
                        "type": "stroke",
                        "points": [[round(rng.random(), 2), round(rng.random(), 2)]],
                        "color": rng.choice(colors),
                        "width": rng.randint(1, 4),
                    })
            self._sync(peers)
            digests = [p.digest() for p in peers]
            assert all(d == digests[0] for d in digests), f"seed {seed}"
