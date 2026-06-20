from __future__ import annotations

from dataclasses import dataclass, field

from src.core.scene import Stroke, Scene

Id = tuple


@dataclass
class Element:
    id: Id
    origin: Id | None
    value: object
    deleted: bool = False

    def to_dict(self) -> dict:
        return {
            "id": list(self.id),
            "origin": list(self.origin) if self.origin is not None else None,
            "value": self.value,
            "deleted": self.deleted,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Element":
        return cls(
            id=tuple(d["id"]),
            origin=tuple(d["origin"]) if d["origin"] is not None else None,
            value=d["value"],
            deleted=d["deleted"],
        )


class RGAReplica:
    def __init__(self, peer_id: str):
        self.peer_id = peer_id
        self._elements: dict[Id, Element] = {}
        self._children: dict[Id | None, list[Id]] = {None: []}
        self._seq = 0
        self._version: dict[str, int] = {}

    def _next_id(self) -> Id:
        self._seq += 1
        return (self._seq, self.peer_id)

    def _integrate(self, el: Element) -> bool:
        if el.id in self._elements:
            return False
        self._elements[el.id] = el
        self._children.setdefault(el.id, [])
        siblings = self._children.setdefault(el.origin, [])
        siblings.append(el.id)
        siblings.sort(reverse=True)
        seq, peer = el.id
        self._version[peer] = max(self._version.get(peer, 0), seq)
        self._seq = max(self._seq, seq)
        return True

    def _apply_element(self, el: Element) -> bool:
        existing = self._elements.get(el.id)
        if existing is None:
            return self._integrate(el)
        if el.deleted and not existing.deleted:
            existing.deleted = True
            return True
        return False

    def _sequence_ids(self) -> list[Id]:
        out: list[Id] = []

        def walk(node_id: Id | None):
            for child_id in self._children.get(node_id, []):
                el = self._elements[child_id]
                if not el.deleted:
                    out.append(child_id)
                walk(child_id)

        walk(None)
        return out

    def _last_id(self) -> Id | None:
        ids = self._sequence_ids()
        return ids[-1] if ids else None

    def apply_local(self, intent: dict) -> dict:
        t = intent["type"]
        if t == "stroke":
            value = {
                "points": intent["points"],
                "color": intent.get("color", "white"),
                "width": intent.get("width", 2),
            }
            el = Element(id=self._next_id(), origin=self._last_id(), value=value)
            self._integrate(el)
            return el.to_dict()
        elif t == "erase":
            el_id = tuple(intent["id"])
            existing = self._elements.get(el_id)
            if existing and not existing.deleted:
                existing.deleted = True
                return existing.to_dict()
            return {}
        else:
            raise ValueError(f"unknown intent type: {t!r}")

    def apply_remote(self, op: dict) -> bool:
        if not op:
            return False
        el = Element.from_dict(op)
        return self._apply_element(el)

    def digest(self) -> tuple:
        return tuple(self._sequence_ids())

    def summary(self) -> dict:
        return dict(self._version)

    def delta_since(self, remote_summary) -> list[dict]:
        vv = remote_summary if isinstance(remote_summary, dict) else {}
        out = []
        for el in self._elements.values():
            seq, peer = el.id
            if seq > vv.get(peer, 0) or (el.deleted and seq <= vv.get(peer, 0)):
                out.append(el.to_dict())
        return out

    def scene(self, canvas_size: int = 400) -> Scene:
        drawables = []
        for el_id in self._sequence_ids():
            el = self._elements[el_id]
            v = el.value
            drawables.append(Stroke(
                points=tuple(tuple(p) for p in v["points"]),
                color=v.get("color", "white"),
                width=v.get("width", 2),
            ))
        return Scene(width=canvas_size, height=canvas_size, drawables=drawables)
