from __future__ import annotations

from src.backends.hashdag import HashDAG, Node
from src.core.scene import Shape, Scene


class CanvasState:
    def __init__(self, dag: HashDAG):
        self.dag = dag

    def _fold(self):
        add_tags: dict[str, set] = {}
        removed_tags: dict[str, set] = {}
        props: dict[str, dict] = {}
        base: dict[str, dict] = {}

        for node in self.dag.topological():
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
        return add_tags, removed_tags, props, base

    def shapes(self) -> list[Shape]:
        add_tags, removed_tags, props, base = self._fold()
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

    def digest(self) -> tuple:
        return tuple((s.id, s.kind, round(s.x, 4), round(s.y, 4),
                      round(s.w, 4), round(s.h, 4), s.color) for s in self.shapes())

    def scene(self, canvas_size: int = 400) -> Scene:
        return Scene(width=canvas_size, height=canvas_size, drawables=self.shapes())
