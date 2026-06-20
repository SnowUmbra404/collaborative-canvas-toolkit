# collaborative-canvas-toolkit — specification

## Purpose

Unified toolkit demonstrating three CRDT collaborative canvas designs behind shared interfaces. The goal is an honest abstraction: backends stay genuinely different; the shared layer is only what must be shared.

## The two interfaces

### Replica protocol

Every backend implements:

```
apply_local(intent) -> Op        local edit -> serializable op dict
apply_remote(op) -> bool         idempotent merge; True if state changed
digest() -> tuple                order-independent convergence fingerprint
summary() -> Summary             opaque anti-entropy token (JSON-serializable)
delta_since(summary) -> [Op]     ops the remote peer is missing
scene() -> Scene                 current drawable state for rendering
```

`summary()` / `delta_since()` implement the backend's anti-entropy strategy. The generic transport calls only these methods — no backend-specific branching.

### Scene / Drawable

Normalized [0,1] coordinate space. Backends emit their native drawable type:

```
PixelCell(x, y, color)                  LWW: a single colored grid cell
Stroke(points, color, width)            RGA: an ordered polyline
Shape(id, kind, x, y, w, h, color)     OR-Map: a rect/ellipse/line with an id
```

One renderer (`core/render.py`) handles all three via `isinstance` dispatch.

## Backends

### LWW — Last-Writer-Wins pixel map

**Document model:** `{(x,y) -> (ts, peer_id, color)}` — a pixel register map over a 32×32 grid.

**Merge:** total order `(ts, peer_id, color)` — the highest rank wins per pixel. This is commutative, associative, and idempotent.

**Anti-entropy:** `summary() = None`. `delta_since(None) = all_ops`. Full state dump on every sync — simple and correct, scales with pixel count not op count.

**Causality:** Lamport clock per peer.

**Normalized coords:** `apply_local` takes normalized [0,1] floats, maps to grid cells via `int(x * (grid-1))`. `scene()` maps cells back to `PixelCell` at normalized `x = cell_x / grid`.

### RGA — Replicated Growable Array for strokes

**Document model:** Ordered sequence of strokes (polylines). Each element has a globally-unique id `(seq, peer_id)` and an `origin` (the id of the element it was inserted after, or None for the front). Elements form a tree; the visible sequence is a pre-order traversal with siblings sorted by id descending — deterministic across all peers with the same element set.

**Merge:** `_integrate` inserts an element into the tree. Deletes are tombstones (element stays for ordering structure). Both operations are idempotent.

**Anti-entropy:** `summary() = {peer: max_seq_seen}`. `delta_since(vv) = elements where seq > vv[peer] or deleted`. Version-vector delta — sends only what the peer is missing.

**Causality:** Per-peer monotonically increasing sequence numbers.

### OR-Map + Merkle-DAG — shapes with causal history

**Document model:** Map of shapes. Existence is an OR-Set (add-wins): each `add` op contributes a unique tag (the op's content hash); a `remove` cancels only the tags it observed. A shape is visible iff at least one add-tag is uncancelled. Mutable properties use LWW registers keyed by `(lamport, peer)`.

**Merge:** `fold_ops(nodes: list[Node]) -> list[Shape]` — a pure function over an ordered list of nodes. Commutative and idempotent by construction: the set of nodes, not their arrival order, determines the result.

**Anti-entropy:** `summary() = sorted(dag.have())` — a sorted list of node hashes the peer already has. `delta_since(have_list) = dag.missing_for(set(have_list))` — nodes in topological order (parents before children) that the remote lacks. Content-addressing gives automatic dedup.

**Causality:** Merkle-DAG — each node's id is `sha256(content + sorted(parents))`. Parent links encode causality; tampered nodes are rejected on receive (hash mismatch).

## Transport

`core/transport.py` `MeshNode` wraps any `Replica` and provides async TCP mesh with the protocol:

```
{"t":"summary", "data": summary()}              on connect
{"t":"delta",   "ops": delta_since(data)}        reply with missing ops
{"t":"op",      "op": op}                        flood new local ops
```

No backend-specific code anywhere in `core/`. The anti-entropy strategies are expressed entirely through `summary()` and `delta_since()`.

## Convergence harness

`core/harness.py` `assert_sec(make_replica, make_intents, n_peers, n_rounds, seed)`:

1. Create N replicas
2. Run random intents via `apply_local`
3. Collect all ops via `delta_since(None)` (empty summary = give everything)
4. Deliver to each replica shuffled + duplicated via `apply_remote`
5. Assert all `digest()` are equal

The same harness runs against all three backends. 51 parametrized tests cover 3–5 peers across 15 seeds.

## Original projects (archived)

| Original | Backend | Source |
|----------|---------|--------|
| decentralized-collaborative-canvas (#41) | OR-Map + Merkle-DAG | base project |
| distributed-collaborative-canvas (#37) | LWW pixels | logic ported natively |
| p2p-real-time-collaborative-canvas (#40) | RGA strokes | logic ported natively |
