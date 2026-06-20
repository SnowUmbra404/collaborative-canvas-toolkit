from __future__ import annotations

from src.replica import Replica
from src.backends.hashdag import Node
from src.core.transport import MeshNode


class PeerNode:
    def __init__(self, peer_id: str):
        self.replica = Replica(peer_id)
        self.peer_id = peer_id
        self._mesh = MeshNode(self.replica)

    async def add_shape(self, *args, **kwargs) -> Node:
        op = await self._mesh.apply_local({
            "type": "add",
            "kind": args[0], "x": args[1], "y": args[2],
            "w": args[3], "h": args[4], "color": args[5],
        })
        return Node.from_dict(op)

    async def set_props(self, shape_id: str, **changes) -> Node:
        op = await self._mesh.apply_local({
            "type": "set", "shape_id": shape_id, "changes": changes,
        })
        return Node.from_dict(op)

    async def remove_shape(self, shape_id: str) -> Node:
        op = await self._mesh.apply_local({
            "type": "remove", "shape_id": shape_id,
        })
        return Node.from_dict(op)

    async def start(self, host: str = "127.0.0.1", port: int = 0) -> int:
        return await self._mesh.start(host, port)

    async def connect_to(self, host: str, port: int) -> None:
        await self._mesh.connect_to(host, port)

    async def stop(self) -> None:
        await self._mesh.stop()
