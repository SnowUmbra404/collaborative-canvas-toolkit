# Decentralized Collaborative Canvas

A backend-free collaborative **shape whiteboard**. There is no server: each peer
holds the full document as an **OR-Map CRDT** and peers synchronize over a P2P
mesh using a **Merkle-DAG of content-addressed operations** — the same idea behind
Git commits and IPFS / Merkle-CRDTs. The history is tamper-evident, deduplicates
automatically, and replays deterministically, so every peer converges.

```
$ uv run python main.py demo
Decentralized Collaborative Canvas (OR-Map + Merkle-DAG)
========================================================
[CRDT proof] 4 peers, DAG nodes delivered shuffled+duplicated
  converged: True  (3 shapes, 22 DAG nodes)
[live P2P mesh] 3 peers draw a face (no backend, content-addressed sync)
  all peers converged: True  (5 shapes from 5 ops)
  saved render to out/canvas.png
```

Three peers — alice (face), bob (eyes), cara (mouth + frame) — draw concurrently
and converge to the same picture (`out/canvas.png`): a yellow face with blue eyes,
a red mouth, and a black frame.

![Three peers' shapes arrive shuffled and the canvas materializes into one converged face](out/converge.gif)

> *CRDT convergence you can watch:* `uv run python main.py demo --gif`. The Merkle-DAG op-set is
> replayed in a deterministically **shuffled** order and folded in one node at a time — the shapes
> pop into place out of order, yet every peer ends on the **exact same face** (the fold uses the DAG's
> topological order, so arrival order can't change the result). No backend, no coordinator.

## What makes it different

This is the third CRDT in the portfolio, and deliberately a *different* kind:

| Project | CRDT | Sync |
|---------|------|------|
| pixel canvas | LWW-Element-Map | full-state gossip |
| vector strokes | sequence CRDT (RGA) | version-vector deltas |
| **this** | **OR-Map (add-wins + LWW)** | **Merkle-DAG content-addressed have/want** |

- **OR-Set add-wins existence**: each `add` contributes a unique tag (the op's
  hash); a `remove` cancels only the tags it *observed*. An add concurrent with a
  remove survives — verified by a dedicated test.
- **LWW property registers**: position/colour/size resolve by `(lamport, peer)`.
- **Merkle-DAG history**: every op is a node `id = sha256(content + parents)`.
  Parent links encode causality; identical ops dedupe; tampering is detectable
  (the id won't match the content). State is a pure fold over the DAG, so the same
  node-set always yields the same canvas.

## Architecture

```
src/
  hashdag.py   content-addressed Merkle-DAG: add_op, heads, topological, missing_for
  crdt.py      OR-Map fold: add-wins existence + LWW properties -> shapes
  replica.py   a peer: DAG + derived state + op authoring + verify-on-receive
  mesh.py      P2P node: have/want anti-entropy + op flood (no server)
  render.py    rasterize shapes to PNG + ASCII + convergence GIF
  demo.py      convergence proof + live mesh drawing a face + render
main.py        CLI: demo [--gif] | peer | web
web/index.html browser canvas (mirrors the shape/OR-Map model)
tests/         32 tests (DAG, CRDT semantics incl. add-wins & tamper, live mesh)
```

## Quick start

```bash
uv sync

# Convergence proof + live 3-peer mesh drawing + PNG render
uv run python main.py demo
#   → out/canvas.png
uv run python main.py demo --gif    # also writes out/converge.gif (canvas materializing)

# Run your own backend-free P2P node and join a mesh
uv run python main.py peer --port 9201 --id alice
uv run python main.py peer --port 9202 --id bob --seeds 127.0.0.1:9201

# Serve the browser canvas UI
uv run python main.py web --port 8080
```

## How sync works (content-addressed have/want)

1. On connect, a peer announces the set of node **hashes** it already has.
2. The remote replies with exactly the nodes the peer is missing, **in
   topological order** (parents before children), so causal dependencies always
   arrive first.
3. New ops are flooded; because nodes are content-addressed, duplicates are
   no-ops and the mesh converges.

## How convergence is proven

1. **OR-Map fuzz** — 40 randomized scenarios (add/move/remove) with every DAG node
   delivered shuffled + duplicated; all replicas converge.
2. **Add-wins test** — an add concurrent with (unobserved by) a remove survives.
3. **Tamper test** — a node whose content doesn't match its hash is rejected.
4. **Live P2P mesh** — real peers draw concurrently and converge, including a
   chain topology (two-hop flood) and delta-sync-on-connect.

## CLI

```
demo  [--gif]                 convergence proof + live mesh + PNG (+ out/converge.gif)
peer  --port --id --seeds     run a backend-free P2P canvas node
web   --host --port           serve the browser canvas UI
```

## Tests

```bash
uv run pytest -q
```

32 tests: the Merkle-DAG (content hashing, parent linking, topological order,
tamper detection, missing-node sync), the OR-Map CRDT (add-wins existence, LWW
properties, **convergence fuzzed over 40 scenarios**, tamper rejection), live
2–3 peer mesh integration (have/want sync, flood, remove propagation), and the
**convergence GIF** (valid `GIF89a`, frame-per-node count, the shuffled fold equals
the converged `shapes()`, and byte-stable output for a fixed seed).

## Why it's interesting

- A genuinely decentralized design — content-addressed Merkle history gives dedup,
  causal ordering, and tamper-evidence for free.
- Real OR-Set add-wins semantics, not just last-writer-wins.
- The convergence and security properties are both verified by tests.
