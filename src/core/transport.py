from __future__ import annotations

import asyncio
import json
import logging

from src.core.replica import Replica

logger = logging.getLogger(__name__)


class MeshNode:
    def __init__(self, replica: Replica):
        self.replica = replica
        self._writers: set = set()
        self._server = None

    @property
    def peer_id(self) -> str:
        return self.replica.peer_id

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

    async def publish(self, op: dict) -> None:
        await self._broadcast({"t": "op", "op": op})

    async def apply_local(self, intent: dict) -> dict:
        op = self.replica.apply_local(intent)
        await self.publish(op)
        return op

    async def _handle(self, reader, writer, initiate: bool) -> None:
        self._writers.add(writer)
        if initiate:
            await self._send(writer, {"t": "summary", "data": self.replica.summary()})
        try:
            async for line in reader:
                if not line.strip():
                    continue
                msg = json.loads(line)
                t = msg.get("t")
                if t == "summary":
                    remote_summary = msg.get("data")
                    delta = self.replica.delta_since(remote_summary)
                    await self._send(writer, {"t": "delta", "ops": delta})
                    await self._send(writer, {"t": "summary", "data": self.replica.summary()})
                elif t == "delta":
                    for op in msg.get("ops", []):
                        self.replica.apply_remote(op)
                elif t == "op":
                    op = msg["op"]
                    if self.replica.apply_remote(op):
                        await self._broadcast({"t": "op", "op": op}, exclude=writer)
        except (asyncio.IncompleteReadError, ConnectionResetError, BrokenPipeError,
                OSError, json.JSONDecodeError):
            pass
        finally:
            self._writers.discard(writer)
            writer.close()

    async def start(self, host: str = "127.0.0.1", port: int = 0) -> int:
        self._server = await asyncio.start_server(
            lambda r, w: self._handle(r, w, initiate=False), host, port)
        bound = self._server.sockets[0].getsockname()[1]
        logger.info("peer %s on %s:%d", self.peer_id, host, bound)
        return bound

    async def connect_to(self, host: str, port: int) -> None:
        reader, writer = await asyncio.open_connection(host, port)
        asyncio.create_task(self._handle(reader, writer, initiate=True))

    async def stop(self) -> None:
        for w in list(self._writers):
            w.close()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
