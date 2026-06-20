import pytest
from src.backends.hashdag import HashDAG, Node, _hash


class TestHashing:
    def test_same_content_same_hash(self):
        op = {"type": "add", "shape_id": "s1"}
        assert _hash(op, []) == _hash(op, [])

    def test_different_content_different_hash(self):
        assert _hash({"a": 1}, []) != _hash({"a": 2}, [])

    def test_parents_affect_hash(self):
        assert _hash({"a": 1}, ["p1"]) != _hash({"a": 1}, ["p2"])

    def test_parent_order_irrelevant(self):
        assert _hash({"a": 1}, ["p1", "p2"]) == _hash({"a": 1}, ["p2", "p1"])


class TestDAG:
    def test_add_op_links_to_heads(self):
        dag = HashDAG()
        n1 = dag.add_op({"x": 1})
        n2 = dag.add_op({"x": 2})
        assert n1.parents == []
        assert n2.parents == [n1.id]
        assert dag.heads() == [n2.id]

    def test_lamport_increments(self):
        dag = HashDAG()
        n1 = dag.add_op({"x": 1})
        n2 = dag.add_op({"x": 2})
        assert n1.lamport == 1
        assert n2.lamport == 2

    def test_receive_is_idempotent(self):
        dag = HashDAG()
        n = dag.add_op({"x": 1})
        other = HashDAG()
        assert other.receive(n) is True
        assert other.receive(n) is False
        assert len(other.nodes) == 1

    def test_verify_detects_tampering(self):
        dag = HashDAG()
        n = dag.add_op({"x": 1})
        assert dag.verify(n) is True
        tampered = Node(n.id, {"x": 999}, n.parents, n.lamport)
        assert dag.verify(tampered) is False

    def test_topological_parents_before_children(self):
        dag = HashDAG()
        n1 = dag.add_op({"x": 1})
        n2 = dag.add_op({"x": 2})
        n3 = dag.add_op({"x": 3})
        order = [n.id for n in dag.topological()]
        assert order.index(n1.id) < order.index(n2.id) < order.index(n3.id)

    def test_topological_deterministic(self):
        dag = HashDAG()
        for i in range(6):
            dag.add_op({"x": i})
        a = [n.id for n in dag.topological()]
        b = [n.id for n in dag.topological()]
        assert a == b


class TestSync:
    def test_missing_for_returns_unknown_nodes(self):
        dag = HashDAG()
        n1 = dag.add_op({"x": 1})
        n2 = dag.add_op({"x": 2})
        missing = dag.missing_for({n1.id})
        ids = [m["id"] for m in missing]
        assert ids == [n2.id]

    def test_missing_for_topological(self):
        dag = HashDAG()
        ids = [dag.add_op({"x": i}).id for i in range(4)]
        missing = dag.missing_for(set())
        order = [m["id"] for m in missing]
        for i in range(1, 4):
            assert order.index(ids[i - 1]) < order.index(ids[i])

    def test_node_dict_roundtrip(self):
        dag = HashDAG()
        n = dag.add_op({"type": "add", "shape_id": "s"})
        restored = Node.from_dict(n.to_dict())
        assert restored.id == n.id
        assert restored.op == n.op
        assert restored.parents == n.parents
