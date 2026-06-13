"""Integration tests for the live P2P mesh + render + demo."""

import asyncio
import pytest

from src.mesh import PeerNode
from src.render import render_png, to_ascii
from src.demo import live_demo, convergence_proof


class TestMesh:
    @pytest.mark.asyncio
    async def test_two_peers_converge(self):
        a = PeerNode("a")
        b = PeerNode("b")
        pa = await a.start()
        await b.start()
        try:
            await b.connect_to("127.0.0.1", pa)
            await asyncio.sleep(0.15)
            await a.add_shape("rect", 0.1, 0.1, 0.2, 0.2, "red")
            await b.add_shape("ellipse", 0.5, 0.5, 0.2, 0.2, "blue")
            await asyncio.sleep(0.3)
            assert a.replica.digest() == b.replica.digest()
            assert len(a.replica.shapes()) == 2
        finally:
            await a.stop()
            await b.stop()

    @pytest.mark.asyncio
    async def test_have_want_sync_on_connect(self):
        """A peer that drew before connecting shares via content-addressed sync."""
        a = PeerNode("a")
        pa = await a.start()
        await a.add_shape("ellipse", 0.3, 0.3, 0.3, 0.3, "green")  # before connect
        b = PeerNode("b")
        await b.start()
        try:
            await b.connect_to("127.0.0.1", pa)
            await asyncio.sleep(0.3)
            assert len(b.replica.shapes()) == 1
            assert b.replica.shapes()[0].color == "green"
        finally:
            await a.stop()
            await b.stop()

    @pytest.mark.asyncio
    async def test_three_peer_chain_floods(self):
        nodes = [PeerNode(f"n{i}") for i in range(3)]
        ports = [await n.start() for n in nodes]
        try:
            await nodes[1].connect_to("127.0.0.1", ports[0])
            await nodes[2].connect_to("127.0.0.1", ports[1])
            await asyncio.sleep(0.2)
            await nodes[2].add_shape("line", 0.1, 0.1, 0.5, 0.5, "yellow")
            await asyncio.sleep(0.4)
            assert len(nodes[0].replica.shapes()) == 1
            assert nodes[0].replica.digest() == nodes[2].replica.digest()
        finally:
            for n in nodes:
                await n.stop()

    @pytest.mark.asyncio
    async def test_remove_propagates(self):
        a = PeerNode("a")
        b = PeerNode("b")
        pa = await a.start()
        await b.start()
        try:
            await b.connect_to("127.0.0.1", pa)
            await asyncio.sleep(0.15)
            node = await a.add_shape("rect", 0.2, 0.2, 0.3, 0.3, "red")
            sid = node.op["shape_id"]
            await asyncio.sleep(0.2)
            await b.remove_shape(sid)
            await asyncio.sleep(0.2)
            assert len(a.replica.shapes()) == 0
        finally:
            await a.stop()
            await b.stop()

    @pytest.mark.asyncio
    async def test_live_demo_converges(self):
        result = await live_demo()
        assert result["converged"] is True
        assert result["shapes"] == 5


class TestProofAndRender:
    def test_convergence_proof(self):
        for seed in (1, 2, 3):
            r = convergence_proof(seed=seed)
            assert r["converged"] is True

    def test_render_png(self, tmp_path):
        from src.replica import Replica
        r = Replica("a")
        r.add_shape("rect", 0.1, 0.1, 0.4, 0.4, "blue")
        r.add_shape("ellipse", 0.5, 0.5, 0.3, 0.3, "red")
        path = str(tmp_path / "c.png")
        render_png(r, path, size=120)
        import os
        assert os.path.exists(path) and os.path.getsize(path) > 0

    def test_ascii_render(self):
        from src.replica import Replica
        r = Replica("a")
        r.add_shape("rect", 0.1, 0.1, 0.5, 0.5, "blue")
        art = to_ascii(r, width=20, height=10)
        assert "R" in art
        assert len(art.split("\n")) == 10
