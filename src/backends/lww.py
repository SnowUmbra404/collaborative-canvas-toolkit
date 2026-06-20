from __future__ import annotations

from dataclasses import dataclass, field

from src.core.clock import LamportClock
from src.core.scene import PixelCell, Scene

GRID = 32
BLANK = None


@dataclass(frozen=True)
class PixelOp:
    x: int
    y: int
    color: str
    ts: int
    peer_id: str

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "color": self.color,
                "ts": self.ts, "peer": self.peer_id}

    @classmethod
    def from_dict(cls, d: dict) -> "PixelOp":
        return cls(x=d["x"], y=d["y"], color=d["color"],
                   ts=d["ts"], peer_id=d["peer"])


class LWWReplica:
    def __init__(self, peer_id: str, grid: int = GRID):
        self.peer_id = peer_id
        self._grid = grid
        self._clock = LamportClock()
        self._registers: dict[tuple[int, int], tuple[int, str, str]] = {}

    def _apply_op(self, op: PixelOp) -> bool:
        key = (op.x, op.y)
        incoming = (op.ts, op.peer_id, op.color)
        current = self._registers.get(key)
        if current is None or incoming > current:
            self._registers[key] = incoming
            return True
        return False

    def apply_local(self, intent: dict) -> dict:
        x = int(intent["x"] * (self._grid - 1))
        y = int(intent["y"] * (self._grid - 1))
        color = intent["color"]
        ts = self._clock.tick()
        op = PixelOp(x, y, color, ts, self.peer_id)
        self._apply_op(op)
        return op.to_dict()

    def apply_remote(self, op: dict) -> bool:
        pixel = PixelOp.from_dict(op)
        self._clock.update(pixel.ts)
        return self._apply_op(pixel)

    def digest(self) -> tuple:
        return tuple(sorted(
            (x, y, color)
            for (x, y), (_ts, _peer, color) in self._registers.items()
            if color is not BLANK
        ))

    def summary(self):
        return None

    def delta_since(self, remote_summary) -> list[dict]:
        return [
            PixelOp(x, y, color, ts, peer).to_dict()
            for (x, y), (ts, peer, color) in self._registers.items()
        ]

    def scene(self, canvas_size: int = 400) -> Scene:
        cell = 1.0 / self._grid
        drawables = [
            PixelCell(x=x * cell, y=y * cell, color=color)
            for (x, y), (_ts, _peer, color) in self._registers.items()
            if color is not BLANK
        ]
        return Scene(width=canvas_size, height=canvas_size, drawables=drawables)
