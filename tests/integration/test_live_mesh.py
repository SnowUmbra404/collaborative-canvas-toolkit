import asyncio
import pytest

from src.core.transport import MeshNode
from src.backends.lww import LWWReplica
from src.backends.rga import RGAReplica
from src.backends.ormap import ORMapReplica


async def _two_peer_converge(make_replica):
    ra = make_replica("a")
    rb = make_replica("b")
    na = MeshNode(ra)
    nb = MeshNode(rb)
    pa = await na.start()
    await nb.start()
    try:
        await nb.connect_to("127.0.0.1", pa)
        await asyncio.sleep(0.15)
        return na, nb, ra, rb
    except Exception:
        await na.stop()
        await nb.stop()
        raise


@pytest.mark.asyncio
async def test_lww_two_peers_converge():
    ra = LWWReplica("a")
    rb = LWWReplica("b")
    na = MeshNode(ra)
    nb = MeshNode(rb)
    pa = await na.start()
    await nb.start()
    try:
        await nb.connect_to("127.0.0.1", pa)
        await asyncio.sleep(0.1)
        await na.apply_local({"x": 0.1, "y": 0.1, "color": "red"})
        await nb.apply_local({"x": 0.9, "y": 0.9, "color": "blue"})
        await asyncio.sleep(0.3)
        assert ra.digest() == rb.digest()
        assert len(ra.scene().drawables) == 2
    finally:
        await na.stop()
        await nb.stop()


@pytest.mark.asyncio
async def test_lww_sync_on_connect():
    ra = LWWReplica("a")
    na = MeshNode(ra)
    pa = await na.start()
    await na.apply_local({"x": 0.5, "y": 0.5, "color": "green"})
    rb = LWWReplica("b")
    nb = MeshNode(rb)
    await nb.start()
    try:
        await nb.connect_to("127.0.0.1", pa)
        await asyncio.sleep(0.3)
        assert len(rb.scene().drawables) == 1
        assert rb.scene().drawables[0].color == "green"
    finally:
        await na.stop()
        await nb.stop()


@pytest.mark.asyncio
async def test_rga_two_peers_converge():
    ra = RGAReplica("a")
    rb = RGAReplica("b")
    na = MeshNode(ra)
    nb = MeshNode(rb)
    pa = await na.start()
    await nb.start()
    try:
        await nb.connect_to("127.0.0.1", pa)
        await asyncio.sleep(0.1)
        await na.apply_local({"type": "stroke", "points": [[0.1, 0.1], [0.5, 0.5]],
                              "color": "red", "width": 2})
        await nb.apply_local({"type": "stroke", "points": [[0.8, 0.8], [0.9, 0.9]],
                              "color": "blue", "width": 2})
        await asyncio.sleep(0.3)
        assert ra.digest() == rb.digest()
        assert len(ra.scene().drawables) == 2
    finally:
        await na.stop()
        await nb.stop()


@pytest.mark.asyncio
async def test_rga_sync_on_connect():
    ra = RGAReplica("a")
    na = MeshNode(ra)
    pa = await na.start()
    await na.apply_local({"type": "stroke", "points": [[0.3, 0.3], [0.7, 0.7]],
                          "color": "cyan", "width": 3})
    rb = RGAReplica("b")
    nb = MeshNode(rb)
    await nb.start()
    try:
        await nb.connect_to("127.0.0.1", pa)
        await asyncio.sleep(0.3)
        assert len(rb.scene().drawables) == 1
    finally:
        await na.stop()
        await nb.stop()


@pytest.mark.asyncio
async def test_ormap_two_peers_converge():
    ra = ORMapReplica("a")
    rb = ORMapReplica("b")
    na = MeshNode(ra)
    nb = MeshNode(rb)
    pa = await na.start()
    await nb.start()
    try:
        await nb.connect_to("127.0.0.1", pa)
        await asyncio.sleep(0.1)
        await na.apply_local({"type": "add", "kind": "rect",
                              "x": 0.1, "y": 0.1, "w": 0.3, "h": 0.3, "color": "red"})
        await nb.apply_local({"type": "add", "kind": "ellipse",
                              "x": 0.5, "y": 0.5, "w": 0.2, "h": 0.2, "color": "blue"})
        await asyncio.sleep(0.3)
        assert ra.digest() == rb.digest()
        assert len(ra.shapes()) == 2
    finally:
        await na.stop()
        await nb.stop()


@pytest.mark.asyncio
async def test_three_peer_chain_lww():
    peers = [LWWReplica(f"p{i}") for i in range(3)]
    nodes = [MeshNode(r) for r in peers]
    ports = [await n.start() for n in nodes]
    try:
        await nodes[1].connect_to("127.0.0.1", ports[0])
        await nodes[2].connect_to("127.0.0.1", ports[1])
        await asyncio.sleep(0.15)
        await nodes[2].apply_local({"x": 0.5, "y": 0.5, "color": "yellow"})
        await asyncio.sleep(0.4)
        assert peers[0].digest() == peers[2].digest()
        assert len(peers[0].scene().drawables) == 1
    finally:
        for n in nodes:
            await n.stop()
