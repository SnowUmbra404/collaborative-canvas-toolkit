# collaborative-canvas-toolkit

A pluggable CRDT collaborative canvas with three backends demonstrating the full range of CRDT trade-offs: LWW pixel registers, RGA causal strokes, and OR-Map + Merkle-DAG shapes. All three share two narrow interfaces and one generic transport — the rest is genuinely backend-specific.

## The two interfaces

### 1. Replica protocol (`src/core/replica.py`)

```python
class Replica(Protocol):
    peer_id: str
    def apply_local(intent: dict) -> Op       # local edit -> serializable op
    def apply_remote(op: Op) -> bool          # idempotent; True if state changed
    def digest() -> tuple                     # order-independent convergence fingerprint
    def summary() -> Summary                  # opaque anti-entropy token
    def delta_since(summary) -> list[Op]      # ops the peer is missing
    def scene() -> Scene
```

Anti-entropy strategies per backend:

| Backend | `summary()` | `delta_since(s)` |
|---------|-------------|-----------------|
| LWW     | `None` | all ops (full dump) |
| RGA     | version-vector `{peer: max_seq}` | elements with seq > vv |
| OR-Map  | sorted list of known hashes | topologically-ordered missing nodes |

### 2. Scene / Drawable (`src/core/scene.py`)

Tagged union over normalized [0,1] coordinates consumed by one renderer:

- `PixelCell(x, y, color)` — LWW backend
- `Stroke(points, color, width)` — RGA backend
- `Shape(id, kind, x, y, w, h, color)` — OR-Map backend

## Backends compared

| Backend | Document model | Merge | Anti-entropy | Causality |
|---------|----------------|-------|--------------|-----------|
| LWW `backends/lww.py` | pixel register map | last-writer-wins `(ts, peer_id)` | full dump | Lamport clock |
| RGA `backends/rga.py` | ordered stroke sequence | causal tree, id-descending siblings | version-vector delta | per-peer sequence |
| OR-Map `backends/ormap.py` + `backends/hashdag.py` | shape map | add-wins OR-Set + LWW property registers | Merkle-DAG have/want | DAG Lamport |

## Layout

```
src/
  core/
    scene.py       Drawable union + Scene
    replica.py     Replica protocol
    transport.py   Generic async TCP mesh (summary→delta→op, no backend branches)
    clock.py       Lamport clock
    render.py      Scene → PNG / GIF / ASCII
    harness.py     Parametrized SEC convergence harness
  backends/
    lww.py         LWW pixel backend
    rga.py         RGA stroke backend
    ormap.py       OR-Map fold logic (fold_ops takes list[Node])
    hashdag.py     Merkle-DAG anti-entropy (standalone from OR-Map)
  cli/main.py      --backend {lww,rga,ormap} demo|render
tests/
  test_lww.py      LWW unit + property (9 tests)
  test_rga.py      RGA unit + property (10 tests)
  test_crdt.py     OR-Map unit + property (10 tests)
  test_hashdag.py  Merkle-DAG (13 tests)
  test_harness.py  Cross-backend SEC fuzz — 51 parametrized tests across all 3
  test_mesh.py     OR-Map live P2P mesh integration (7 tests)
  test_render_gif.py  Render tests (3 tests)
```

## Quick start

```bash
uv sync
uv run pytest -q

uv run python -m src.cli.main --backend lww demo
uv run python -m src.cli.main --backend rga demo
uv run python -m src.cli.main --backend ormap demo

uv run python -m src.cli.main --backend lww render
```

## What the three backends demonstrate

The toolkit makes one comparison concrete: the same SEC guarantee reached by three genuinely different designs.

**LWW** is the simplest: no causal structure, just a timestamp tiebreaker per pixel. Anti-entropy is a full state dump — correct but not scalable. Good for small shared pixel maps.

**RGA** preserves insertion *order* across concurrent peers — the property LWW cannot provide. A causal tree gives every stroke a globally-unique id; siblings are ordered by id descending for determinism. Delta sync sends only what a peer is missing (version-vector). Good for sequences where order matters.

**OR-Map + Merkle-DAG** adds tamper-evidence and causal history. Every op becomes a content-addressed DAG node; the OR-Map gives add-wins existence semantics with LWW property registers. Anti-entropy is have/want: announce known hashes, receive only the diff in topological order. Good for structured documents with rich conflict semantics.

## Convergence evidence

- 51 parametrized fuzz tests across all three backends (`test_harness.py`): shuffled + duplicated delivery, 3–5 peers, 15 seeds each
- OR-Map: add-wins test (add concurrent with unobserved remove survives), tamper rejection
- Merkle-DAG: content-hash dedup, topological ordering, tamper detection
- Live P2P mesh: real async TCP peers draw concurrently and converge
