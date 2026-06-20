import random
import pytest

from src.core.harness import assert_sec
from src.backends.lww import LWWReplica
from src.backends.rga import RGAReplica
from src.backends.ormap import ORMapReplica

COLORS = ["red", "green", "blue", "yellow", "cyan", "magenta", "white"]


def lww_intents(replica, rng: random.Random) -> list[dict]:
    return [{
        "x": round(rng.random(), 2),
        "y": round(rng.random(), 2),
        "color": rng.choice(COLORS),
    }]


def rga_intents(replica, rng: random.Random) -> list[dict]:
    scene = replica.scene()
    if scene.drawables and rng.random() < 0.25:
        ids = replica.digest()
        chosen = rng.choice(ids)
        return [{"type": "erase", "id": list(chosen)}]
    return [{
        "type": "stroke",
        "points": [[round(rng.random(), 2), round(rng.random(), 2)],
                   [round(rng.random(), 2), round(rng.random(), 2)]],
        "color": rng.choice(COLORS),
        "width": rng.randint(1, 4),
    }]


def ormap_intents(replica, rng: random.Random) -> list[dict]:
    shapes = replica.shapes()
    r = rng.random()
    if shapes and r < 0.2:
        return [{"type": "remove", "shape_id": rng.choice(shapes).id}]
    elif shapes and r < 0.45:
        return [{"type": "set", "shape_id": rng.choice(shapes).id,
                 "changes": {"x": round(rng.random(), 3), "color": rng.choice(COLORS)}}]
    else:
        return [{"type": "add", "kind": rng.choice(["rect", "ellipse", "line"]),
                 "x": round(rng.random(), 3), "y": round(rng.random(), 3),
                 "w": 0.2, "h": 0.2, "color": rng.choice(COLORS)}]


@pytest.mark.parametrize("backend,make_replica,make_intents", [
    ("lww",   lambda pid: LWWReplica(pid),    lww_intents),
    ("rga",   lambda pid: RGAReplica(pid),    rga_intents),
    ("ormap", lambda pid: ORMapReplica(pid),  ormap_intents),
])
class TestSEC:
    def test_three_peers_converge(self, backend, make_replica, make_intents):
        result = assert_sec(make_replica, make_intents, n_peers=3, n_rounds=20, seed=42)
        assert result["converged"], f"{backend}: digests={result['digests']}"

    def test_five_peers_converge(self, backend, make_replica, make_intents):
        result = assert_sec(make_replica, make_intents, n_peers=5, n_rounds=30, seed=7)
        assert result["converged"], f"{backend}: digests={result['digests']}"

    @pytest.mark.parametrize("seed", range(15))
    def test_fuzz_seeds(self, backend, make_replica, make_intents, seed):
        result = assert_sec(make_replica, make_intents, n_peers=3, n_rounds=15, seed=seed)
        assert result["converged"], f"{backend} seed={seed}: digests={result['digests']}"
