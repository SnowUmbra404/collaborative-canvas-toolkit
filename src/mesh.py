"""P2P mesh with content-addressed have/want anti-entropy.

No central server. On connect, a peer announces the set of node hashes it already
has; the remote replies with exactly the nodes the peer is missing, in topological
order (parents before children). New operations are flooded to all peers. Because
nodes are content-addressed, duplicates are free and every peer ends with the same
DAG — and therefore the same canvas.

Wire protocol (newline-delimited JSON):
  {"t":"have", "have": [hash, ...]}     announce what I already have
  {"t":"nodes", "nodes": [node, ...]}   here are the nodes you were missing
  {"t":"op", "node": {...}}             a single new node (flood)
"""

from __future__ import annotations

import asyncio
import json
import logging

from src.replica import Replica
from src.hashdag import Node

logger = logging.getLogger(__name__)


class PeerNode:
    def __init__(self, peer_id: str):
        self.replica = Replica(peer_id)
        self.peer_id = peer_id
        self._writers: set = set()
        self._server = None

    def _encode(self, obj: dict) -> bytes:
        return (json.dumps(obj) + "\n").encode()

    async def _send(self, writer, obj: dict) -> None:
        try:
            writer.write(self._encode(obj))
            await writer.drain()
        except (ConnectionResetError, BrokenPipeError, OSError, RuntimeError):
            self._writers.discard(writer)

    async def _broadcast(self, obj: dict, exclude=None) -> None:
        for w in list(self._writers):
            if w is not exclude:
                await self._send(w, obj)

    # --- local authoring ----------------------------------------------------

    async def _publish(self, node: Node) -> None:
        await self._broadcast({"t": "op", "node": node.to_dict()})

    async def add_shape(self, *args, **kwargs) -> Node:
        node = self.replica.add_shape(*args, **kwargs)
        await self._publish(node)
        return node

    async def set_props(self, shape_id, **changes) -> Node:
        node = self.replica.set_props(shape_id, **changes)
        await self._publish(node)
        return node

    async def remove_shape(self, shape_id) -> Node:
        node = self.replica.remove_shape(shape_id)
        await self._publish(node)
        return node

    # --- connection handling ------------------------------------------------

    async def _handle(self, reader, writer, initiate: bool) -> None:
        self._writers.add(writer)
        if initiate:
            await self._send(writer, {"t": "have", "have": sorted(self.replica.have())})
        try:
            async for line in reader:
                if not line.strip():
                    continue
                msg = json.loads(line)
                t = msg.get("t")
                if t == "have":
                    remote_have = set(msg.get("have", []))
                    missing = self.replica.dag.missing_for(remote_have)
                    await self._send(writer, {"t": "nodes", "nodes": missing})
                    # Reciprocate so we also pull what we're missing.
                    await self._send(writer, {"t": "have", "have": sorted(self.replica.have())})
                elif t == "nodes":
                    # Apply in given (topological) order so parents precede children.
                    for nd in msg.get("nodes", []):
                        self.replica.receive_node(Node.from_dict(nd))
                elif t == "op":
                    node = Node.from_dict(msg["node"])
                    if self.replica.receive_node(node):
                        await self._broadcast({"t": "op", "node": msg["node"]},
                                              exclude=writer)
        except (asyncio.IncompleteReadError, ConnectionResetError, BrokenPipeError,
                OSError, json.JSONDecodeError):
            pass
        finally:
            self._writers.discard(writer)
            writer.close()

    async def start(self, host="127.0.0.1", port=0) -> int:
        self._server = await asyncio.start_server(
            lambda r, w: self._handle(r, w, initiate=False), host, port)
        bound = self._server.sockets[0].getsockname()[1]
        logger.info("peer %s on %s:%d", self.peer_id, host, bound)
        return bound

    async def connect_to(self, host, port) -> None:
        reader, writer = await asyncio.open_connection(host, port)
        asyncio.create_task(self._handle(reader, writer, initiate=True))

    async def stop(self) -> None:
        for w in list(self._writers):
            w.close()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
