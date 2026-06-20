from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.core.scene import Scene

Summary = object
Op = dict


@runtime_checkable
class Replica(Protocol):
    peer_id: str

    def apply_local(self, intent: dict) -> Op: ...

    def apply_remote(self, op: Op) -> bool: ...

    def digest(self) -> tuple: ...

    def summary(self) -> Summary: ...

    def delta_since(self, remote_summary: Summary) -> list[Op]: ...

    def scene(self) -> Scene: ...
