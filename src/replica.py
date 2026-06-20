from __future__ import annotations

from src.backends.hashdag import HashDAG, Node
from src.backends.ormap import CanvasState
from src.core.scene import Shape, Scene


class Replica:
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
