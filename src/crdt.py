"""An OR-Map of shapes, derived by folding the operation DAG.

Existence uses **OR-Set add-wins** semantics: each `add` contributes a unique tag
(the op's hash); a `remove` records the tags it observed. A shape is present iff
it has at least one add-tag that no remove has cancelled — so an add concurrent
with a remove (whose tag the remove never saw) *survives*. Mutable properties
(position, colour, size) are **LWW registers** keyed by `(lamport, peer)`, so the
last writer in logical time wins. Both rules are order-independent, which is why
replaying the same DAG node-set on any peer yields identical state.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.hashdag import HashDAG, Node


@dataclass
class Shape:
    id: str
    kind: str            # "rect" | "ellipse" | "line"
    x: float
    y: float
    w: float
    h: float
    color: str

    def to_dict(self) -> dict:
        return self.__dict__.copy()


class CanvasState:
    """Folds a HashDAG into the set of currently-visible shapes."""

    def __init__(self, dag: HashDAG):
        self.dag = dag

    def _fold(self):
        add_tags: dict[str, set] = {}     # shape_id -> set of add tags
        removed_tags: dict[str, set] = {}  # shape_id -> set of cancelled tags
        # Per shape_id, per property: (lamport, peer) -> value (LWW).
        props: dict[str, dict] = {}
        base: dict[str, dict] = {}        # shape_id -> base attributes from add

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
                # The add also seeds LWW registers.
                pr = props.setdefault(sid, {})
                for k in ("x", "y", "w", "h", "color"):
                    cur = pr.get(k)
                    if cur is None or stamp > cur[0]:
                        pr[k] = (stamp, op[k])
            elif op["type"] == "remove":
                removed_tags.setdefault(sid, set()).update(op.get("observed", []))
            else:  # "set" — update a property via LWW
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
            if tags - removed_tags.get(sid, set()):   # add-wins: any live tag
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
        # Stable order for rendering/snapshots: by shape id.
        return sorted(out, key=lambda s: s.id)

    def digest(self) -> tuple:
        return tuple((s.id, s.kind, round(s.x, 4), round(s.y, 4),
                      round(s.w, 4), round(s.h, 4), s.color) for s in self.shapes())
