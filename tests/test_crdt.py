import random
import pytest

from src.backends.ormap import ORMapReplica
from src.backends.hashdag import Node


class TestBasics:
    def test_add_shape_appears(self):
        r = ORMapReplica("a")
        r.add_shape("rect", 0.1, 0.1, 0.2, 0.2, "red")
        shapes = r.shapes()
        assert len(shapes) == 1
        assert shapes[0].kind == "rect" and shapes[0].color == "red"

    def test_remove_hides_shape(self):
        r = ORMapReplica("a")
        n = r.add_shape("rect", 0.1, 0.1, 0.2, 0.2, "red")
        sid = n.op["shape_id"]
        r.remove_shape(sid)
        assert len(r.shapes()) == 0

    def test_set_props_lww(self):
        r = ORMapReplica("a")
        n = r.add_shape("rect", 0.1, 0.1, 0.2, 0.2, "red")
        sid = n.op["shape_id"]
        r.set_props(sid, x=0.5, color="blue")
        s = r.shapes()[0]
        assert s.x == 0.5 and s.color == "blue"


class TestConvergence:
    def _sync(self, replicas):
        nodes = [n.to_dict() for r in replicas for n in r.dag.nodes.values()]
        rng = random.Random(0)
        for r in replicas:
            delivery = list(nodes) + nodes
            rng.shuffle(delivery)
            for d in delivery:
                r.receive_node(Node.from_dict(d))

    def test_two_replicas_converge(self):
        a = ORMapReplica("a"); b = ORMapReplica("b")
        a.add_shape("rect", 0.1, 0.1, 0.2, 0.2, "red")
        b.add_shape("ellipse", 0.5, 0.5, 0.2, 0.2, "blue")
        self._sync([a, b])
        assert a.digest() == b.digest()
        assert len(a.shapes()) == 2

    def test_concurrent_move_lww_converges(self):
        a = ORMapReplica("a"); b = ORMapReplica("b")
        n = a.add_shape("rect", 0.1, 0.1, 0.2, 0.2, "red")
        sid = n.op["shape_id"]
        b.receive_node(n)
        a.set_props(sid, x=0.3)
        b.set_props(sid, x=0.7)
        self._sync([a, b])
        assert a.digest() == b.digest()

    def test_add_wins_over_concurrent_remove(self):
        a = ORMapReplica("a")
        n = a.add_shape("rect", 0.1, 0.1, 0.2, 0.2, "red")
        sid = n.op["shape_id"]
        b = ORMapReplica("b")
        b.receive_node(n)
        b.remove_shape(sid)
        a.dag.add_op({"type": "add", "peer": "a", "shape_id": sid,
                      "kind": "rect", "x": 0.4, "y": 0.4, "w": 0.2, "h": 0.2,
                      "color": "green"})
        self._sync([a, b])
        assert a.digest() == b.digest()
        assert len(a.shapes()) == 1

    def test_fuzz_convergence(self):
        for seed in range(40):
            rng = random.Random(seed)
            peers = [ORMapReplica(f"p{i}") for i in range(3)]
            for _ in range(15):
                p = rng.choice(peers)
                sh = p.shapes()
                if sh and rng.random() < 0.3:
                    p.remove_shape(rng.choice(sh).id)
                elif sh and rng.random() < 0.6:
                    p.set_props(rng.choice(sh).id, x=round(rng.random(), 3))
                else:
                    p.add_shape("rect", round(rng.random(), 3),
                                round(rng.random(), 3), 0.2, 0.2, "red")
            self._sync(peers)
            digests = [p.digest() for p in peers]
            assert all(d == digests[0] for d in digests), f"seed {seed}"


class TestTamperRejection:
    def test_tampered_node_rejected(self):
        a = ORMapReplica("a")
        n = a.add_shape("rect", 0.1, 0.1, 0.2, 0.2, "red")
        b = ORMapReplica("b")
        tampered = Node(n.id, {**n.op, "color": "HACKED"}, n.parents, n.lamport)
        assert b.receive_node(tampered) is False
        assert len(b.shapes()) == 0
