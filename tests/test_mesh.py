import asyncio
import os
import pytest

from src.backends.ormap import ORMapReplica
from src.backends.hashdag import Node
from src.core.transport import MeshNode
from src.core.render import render_scene_png, scene_to_ascii
from src.demo import live_demo, convergence_proof


class TestMesh:
    @pytest.mark.asyncio
    async def test_two_peers_converge(self):
        ra = ORMapReplica("a")
        rb = ORMapReplica("b")
        na = MeshNode(ra)
        nb = MeshNode(rb)
        pa = await na.start()
        await nb.start()
        try:
            await nb.connect_to("127.0.0.1", pa)
            await asyncio.sleep(0.15)
            await na.apply_local({"type": "add", "kind": "rect",
                                  "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2, "color": "red"})
            await nb.apply_local({"type": "add", "kind": "ellipse",
                                  "x": 0.5, "y": 0.5, "w": 0.2, "h": 0.2, "color": "blue"})
            await asyncio.sleep(0.3)
            assert ra.digest() == rb.digest()
            assert len(ra.shapes()) == 2
        finally:
            await na.stop()
            await nb.stop()

    @pytest.mark.asyncio
    async def test_have_want_sync_on_connect(self):
        ra = ORMapReplica("a")
        na = MeshNode(ra)
        pa = await na.start()
        await na.apply_local({"type": "add", "kind": "ellipse",
                              "x": 0.3, "y": 0.3, "w": 0.3, "h": 0.3, "color": "green"})
        rb = ORMapReplica("b")
        nb = MeshNode(rb)
        await nb.start()
        try:
            await nb.connect_to("127.0.0.1", pa)
            await asyncio.sleep(0.3)
            assert len(rb.shapes()) == 1
            assert rb.shapes()[0].color == "green"
        finally:
            await na.stop()
            await nb.stop()

    @pytest.mark.asyncio
    async def test_three_peer_chain_floods(self):
        replicas = [ORMapReplica(f"n{i}") for i in range(3)]
        nodes = [MeshNode(r) for r in replicas]
        ports = [await n.start() for n in nodes]
        try:
            await nodes[1].connect_to("127.0.0.1", ports[0])
            await nodes[2].connect_to("127.0.0.1", ports[1])
            await asyncio.sleep(0.2)
            await nodes[2].apply_local({"type": "add", "kind": "line",
                                        "x": 0.1, "y": 0.1, "w": 0.5, "h": 0.5, "color": "yellow"})
            await asyncio.sleep(0.4)
            assert len(replicas[0].shapes()) == 1
            assert replicas[0].digest() == replicas[2].digest()
        finally:
            for n in nodes:
                await n.stop()

    @pytest.mark.asyncio
    async def test_remove_propagates(self):
        ra = ORMapReplica("a")
        rb = ORMapReplica("b")
        na = MeshNode(ra)
        nb = MeshNode(rb)
        pa = await na.start()
        await nb.start()
        try:
            await nb.connect_to("127.0.0.1", pa)
            await asyncio.sleep(0.15)
            op = await na.apply_local({"type": "add", "kind": "rect",
                                       "x": 0.2, "y": 0.2, "w": 0.3, "h": 0.3, "color": "red"})
            sid = Node.from_dict(op).op["shape_id"]
            await asyncio.sleep(0.2)
            await nb.apply_local({"type": "remove", "shape_id": sid})
            await asyncio.sleep(0.2)
            assert len(ra.shapes()) == 0
        finally:
            await na.stop()
            await nb.stop()

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
        r = ORMapReplica("a")
        r.add_shape("rect", 0.1, 0.1, 0.4, 0.4, "blue")
        r.add_shape("ellipse", 0.5, 0.5, 0.3, 0.3, "red")
        path = str(tmp_path / "c.png")
        render_scene_png(r.scene(120), path, 120)
        assert os.path.exists(path) and os.path.getsize(path) > 0

    def test_ascii_render(self):
        r = ORMapReplica("a")
        r.add_shape("rect", 0.1, 0.1, 0.5, 0.5, "blue")
        art = scene_to_ascii(r.scene(), 20, 10)
        assert "R" in art
        assert len(art.split("\n")) == 10
