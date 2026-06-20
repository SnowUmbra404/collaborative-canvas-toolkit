from __future__ import annotations

from src.backends.hashdag import HashDAG, Node
from src.core.scene import Shape, Scene


def fold_ops(nodes: list[Node]) -> list[Shape]:
    add_tags: dict[str, set] = {}
    removed_tags: dict[str, set] = {}
    props: dict[str, dict] = {}
    base: dict[str, dict] = {}

    for node in nodes:
        op = node.op
        sid = op["shape_id"]
        stamp = (node.lamport, op.get("peer", ""))
        if op["type"] == "add":
            add_tags.setdefault(sid, set()).add(node.id)
            base.setdefault(sid, {
                "kind": op["kind"], "x": op["x"], "y": op["y"],
                "w": op["w"], "h": op["h"], "color": op["color"],
            })
            pr = props.setdefault(sid, {})
            for k in ("x", "y", "w", "h", "color"):
                cur = pr.get(k)
                if cur is None or stamp > cur[0]:
                    pr[k] = (stamp, op[k])
        elif op["type"] == "remove":
            removed_tags.setdefault(sid, set()).update(op.get("observed", []))
        else:
            pr = props.setdefault(sid, {})
            for k, v in op.get("changes", {}).items():
                cur = pr.get(k)
                if cur is None or stamp > cur[0]:
                    pr[k] = (stamp, v)

    out = []
    for sid, tags in add_tags.items():
        if tags - removed_tags.get(sid, set()):
            pr = props.get(sid, {})
            b = base.get(sid, {})
            out.append(Shape(
                id=sid, kind=b.get("kind", "rect"),
                x=pr.get("x", ((0, ""), b.get("x", 0)))[1],
                y=pr.get("y", ((0, ""), b.get("y", 0)))[1],
                w=pr.get("w", ((0, ""), b.get("w", 0)))[1],
                h=pr.get("h", ((0, ""), b.get("h", 0)))[1],
                color=pr.get("color", ((0, ""), b.get("color", "black")))[1],
            ))
    return sorted(out, key=lambda s: s.id)


def shapes_digest(shapes: list[Shape]) -> tuple:
    return tuple((s.id, s.kind, round(s.x, 4), round(s.y, 4),
                  round(s.w, 4), round(s.h, 4), s.color) for s in shapes)


class CanvasState:
    def __init__(self, dag):
        self._dag = dag

    def shapes(self) -> list[Shape]:
        return fold_ops(self._dag.topological())

    def digest(self) -> tuple:
        return shapes_digest(self.shapes())

    def scene(self, canvas_size: int = 400) -> Scene:
        return Scene(width=canvas_size, height=canvas_size, drawables=self.shapes())


class ORMapReplica:
    def __init__(self, peer_id: str):
        self.peer_id = peer_id
        self.dag = HashDAG()
        self.state = CanvasState(self.dag)
        self._shape_seq = 0

    def _new_shape_id(self) -> str:
        self._shape_seq += 1
        return f"{self.peer_id}:{self._shape_seq}"

    def add_shape(self, kind: str, x: float, y: float, w: float, h: float,
                  color: str) -> Node:
        sid = self._new_shape_id()
        return self.dag.add_op({
            "type": "add", "peer": self.peer_id, "shape_id": sid,
            "kind": kind, "x": x, "y": y, "w": w, "h": h, "color": color,
        })

    def set_props(self, shape_id: str, **changes) -> Node:
        return self.dag.add_op({
            "type": "set", "peer": self.peer_id, "shape_id": shape_id,
            "changes": changes,
        })

    def remove_shape(self, shape_id: str) -> Node:
        observed = [n.id for n in self.dag.nodes.values()
                    if n.op.get("type") == "add" and n.op.get("shape_id") == shape_id]
        return self.dag.add_op({
            "type": "remove", "peer": self.peer_id, "shape_id": shape_id,
            "observed": observed,
        })

    def apply_local(self, intent: dict) -> dict:
        t = intent["type"]
        if t == "add":
            node = self.add_shape(
                intent["kind"], intent["x"], intent["y"],
                intent["w"], intent["h"], intent["color"],
            )
        elif t == "set":
            node = self.set_props(intent["shape_id"], **intent.get("changes", {}))
        elif t == "remove":
            node = self.remove_shape(intent["shape_id"])
        else:
            raise ValueError(f"unknown intent type: {t!r}")
        return node.to_dict()

    def apply_remote(self, op: dict) -> bool:
        node = Node.from_dict(op)
        if not self.dag.verify(node):
            return False
        return self.dag.receive(node)

    def receive_node(self, node: Node) -> bool:
        if not self.dag.verify(node):
            return False
        return self.dag.receive(node)

    def summary(self) -> list:
        return sorted(self.dag.have())

    def delta_since(self, remote_summary) -> list[dict]:
        have = set(remote_summary) if remote_summary else set()
        return self.dag.missing_for(have)

    def shapes(self) -> list[Shape]:
        return self.state.shapes()

    def digest(self) -> tuple:
        return self.state.digest()

    def scene(self, canvas_size: int = 400) -> Scene:
        return self.state.scene(canvas_size)

    def have(self):
        return self.dag.have()
