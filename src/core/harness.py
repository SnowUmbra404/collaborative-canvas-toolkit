from __future__ import annotations

import random
from typing import Callable


def assert_sec(
    make_replica: Callable[[str], object],
    make_intents: Callable[[object, random.Random], list[dict]],
    n_peers: int = 3,
    n_rounds: int = 20,
    seed: int = 0,
) -> dict:
    rng = random.Random(seed)
    replicas = [make_replica(f"p{i}") for i in range(n_peers)]

    for _ in range(n_rounds):
        r = rng.choice(replicas)
        for intent in make_intents(r, rng):
            r.apply_local(intent)

    all_ops = [op for r in replicas for op in r.delta_since(None)]

    for r in replicas:
        delivery = list(all_ops) + list(all_ops)
        rng.shuffle(delivery)
        for op in delivery:
            r.apply_remote(op)

    digests = [r.digest() for r in replicas]
    converged = all(d == digests[0] for d in digests)
    return {"converged": converged, "peers": n_peers, "digests": digests}
