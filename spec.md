# Decentralized Collaborative Canvas Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a real-time, decentralized collaborative whiteboard using CRDTs (Conflict-free Replicated Data Types) that runs entirely in the browser without a central backend.

**Architecture:** Peer-to-peer communication using WebRTC for state synchronization. The canvas state will be managed using Yjs (a popular CRDT library) to ensure eventual consistency across all connected clients.

**Tech Stack:**
- Frontend: React / TypeScript
- Canvas: Konva.js or HTML5 Canvas API
- P2P: PeerJS (WebRTC abstraction)
- Sync: Yjs (CRDT)

---

### Task 1: Initialize Project and WebRTC Setup
**Objective:** Set up the project structure and establish basic P2P connectivity between two browser windows.
**Files:**
- `package.json`
- `src/p2p/connection.ts`
- `tests/p2p/connection.test.ts`

### Task 2: Implement Shared State with Yjs
**Objective:** Integrate Yjs to share a simple counter variable across peers to verify synchronization.
**Files:**
- `src/sync/state.ts`
- `tests/sync/state.test.ts`

### Task 3: Render Basic Canvas Elements
**Objective:** Render simple shapes on an HTML5 canvas and map them to the Yjs shared object.
**Files:**
- `src/components/Canvas.tsx`
- `tests/components/Canvas.test.tsx`

### Task 4: Integrate Canvas with Yjs
**Objective:** Enable bidirectional synchronization where drawing on one canvas updates all others in real-time.
**Files:**
- `src/sync/canvas-adapter.ts`
- `tests/sync/canvas-adapter.test.ts`

### Task 5: Final Integration and UI Polish
**Objective:** Add basic toolbar for tool selection (brush, rectangle, eraser) and clean up the UI.
**Files:**
- `src/App.tsx`
- `src/components/Toolbar.tsx`

## Iteration 1 (2026-06-13)
**Theme:** Watch It Converge (GIF)
**Why this iteration:** The demo only emits a single static `out/canvas.png`. The project's whole magic — DAG nodes arriving *shuffled + duplicated* yet every peer snapping to the same picture — is invisible in one frame. An animated GIF turns the convergence proof into something you can actually *see* (and post).
**What this adds:**
- A new `render_gif(replica_or_nodes, path)` that renders one frame per Merkle-DAG node as it is folded in, so the canvas visibly materializes op-by-op and ends on the converged face.
- A `demo --gif` flag (and a line in the default `demo`) that replays the live-mesh node set in a deterministically shuffled order, writing `out/converge.gif`.
- A short caption frame / held last frame ("converged: True — 3 peers, N DAG nodes") so the GIF is self-explanatory when shared.
**Implementation notes (keep it lean):**
- Reuse `render_png`'s drawing logic: factor the per-shape draw loop into a `_draw_shapes(draw, shapes, size)` helper, call it from both `render_png` and the new frame renderer (no behavior change to existing PNG output).
- Build frames by folding the DAG incrementally: start from an empty `Replica`, `add_op`/apply nodes one at a time in the shuffled delivery order, snapshot `replica.shapes()` → one PIL `Image` per step.
- Write the GIF with Pillow only: `frames[0].save(path, save_all=True, append_images=frames[1:], duration=180, loop=0)`. Hold the final frame ~5× and keep total frames modest (cap/stride if nodes > ~40). No new dependency.
- Use a fixed RNG seed for the shuffle so the GIF is byte-stable / reproducible.
**Testing:** Unit test that `render_gif` writes a non-empty file whose first bytes are the GIF magic (`GIF89a`) and that frame count == expected step count; assert the final folded state equals the existing converged `shapes()` (ties the animation back to the convergence guarantee). All offline, CI-safe, no network/hardware.
**Share-worthy angle:** A looping GIF of three peers' scribbles arriving out-of-order and duplicated, then snapping into one identical face — "CRDT convergence you can watch," backend-free.

---

## Iteration 2 (2026-06-14)
**Theme:** Git Log for Your Drawing (Merkle-DAG)

**Why this iteration:** Iteration 1 shows the **canvas** converging — the *result*. But the project's
genuinely unique idea (vs the portfolio's other two CRDTs) is *how*: a **content-addressed Merkle-DAG**
of operations, where `id = sha256(content + parents)` gives causal ordering, automatic dedup, and
tamper-evidence — the same structure behind Git commits and IPFS. That history is completely invisible;
nothing renders the DAG itself. Drawing it turns an abstract claim ("Merkle-CRDT") into a picture people
immediately recognize as a commit graph — and it pairs with the convergence GIF (canvas vs. its history).

**What this adds:**
- A **Merkle-DAG growth GIF** (`demo --dag` / `viz-dag`, default demo unchanged): render the op-DAG
  as it forms — each op is a node positioned by **causal depth** (topological layer), edges drawn to its
  **parent ops**, nodes **coloured per author** (alice/bob/cara) and **labelled with the first 8 hex of
  their hash**. As nodes arrive in shuffled+duplicated order, the graph grows frame by frame.
- **Dedup made visible:** when a duplicate (same content hash) is delivered, flash it as a no-op against
  the existing node instead of adding one — the "content-addressed ⇒ duplicates are free" insight, on
  screen. A live counter shows `deliveries seen` vs `distinct DAG nodes`.
- **Tamper-evidence accent (final beat):** flip one byte of a node's content, show its recomputed hash
  no longer matching its id, and draw it **rejected in red** — the security property as a single frame.
- Optional side-by-side with the Iteration-1 canvas render so viewers see "this history → that picture."

**Implementation notes (keep it lean — reuse, don't fork):**
- New `render_dag(nodes, path)` in `src/render.py`; reuse the Iteration-1 GIF plumbing (Pillow,
  `frames[0].save(..., save_all=True, ...)`, fixed seed, held final frame). No new dependency.
- Drive the **real** `src/hashdag.py`: read actual node ids, parent links, and topological order from
  the DAG (the module already exposes `topological` / `heads` / `missing_for`). Layout = layer by topo
  depth (x), stack siblings (y); simple straight/curved parent edges. Do NOT change `hashdag.py`,
  `crdt.py`, `replica.py`, or `mesh.py` — visualization only.
- Use the existing 3-peer "draw a face" scenario so canvas and DAG GIFs tell the same story; cap nodes
  (~22 in the demo) so the graph stays legible and the GIF stays ~1MB.

**Testing (deterministic, offline, CI-safe):**
- `test_dag_layout_matches_hashdag`: every node/edge drawn corresponds to a real `(id, parents)` in the
  DAG, edge directions point child→parent (or parent→child, consistently), and node count == distinct
  op count (not delivery count) — proving dedup is reflected.
- `test_dag_dedup_counter`: replaying a node set with duplicates yields `distinct nodes < deliveries`,
  matching the counter shown.
- `test_dag_gif_written`: `viz-dag` writes a valid multi-frame GIF (`GIF89a`, frames > 1). Keep the
  Iteration-1 convergence test and all CRDT/DAG/mesh tests green.

**Share-worthy angle:** A GIF where a **Git-style commit graph builds itself from a drawing** — hash-
labelled nodes linking to their parents, duplicates collapsing for free, and a tampered node rejected in
red — "your doodle has a Merkle history," fully backend-free.

---

## Iteration 3 (2026-06-14)
**Theme:** Split-Brain & Heal (partition tolerance)

**Why this iteration:** Iteration 1 showed shuffled delivery *converging*; Iteration 2 drew the Merkle-DAG
*history*. The one CRDT superpower neither shows — and the most authentic to this project's "no backend /
offline-first" identity — is **partition tolerance**: a network splits, two groups keep drawing in total
isolation (no connectivity), and when the link is restored they **heal into one identical canvas** with no
coordinator and no lost strokes. That's the "draw on a plane, sync when you land" story — the single most
convincing demonstration of *why* you'd build on a content-addressed CRDT instead of a server.

**What this adds:**
- A **`partition` demo** (`uv run python main.py partition --seed 7`): start one mesh, let everyone agree,
  then **sever it into two sub-meshes** (A: alice+bob, B: cara+dave). Each side draws several shapes while
  fully disconnected, so the two canvases **visibly diverge**. Then **reconnect** and run the existing
  content-addressed have/want sync — the sides exchange exactly the ops they each lack (in topological
  order) and converge to one canvas. Prints the proof: `before heal: A=5 shapes, B=4, equal=False` →
  `after heal: A=B=9 shapes, equal=True, DAG nodes=N`.
- A **side-by-side "heal" GIF**: two canvases drifting apart during the partition, a "⛓ RECONNECTED" beat,
  then both snapping to the same picture — the split-brain-heals money shot. Reuse Iteration 1's
  `render_gif` frame plumbing, composed two-up.

**Implementation notes (keep it lean — drive the REAL mesh, don't fake the split):**
- Reuse `src/mesh.py` + `src/replica.py`: model the partition by simply **not delivering** ops across the
  A|B boundary during the split phase (gate the existing have/want exchange), then enabling it at reconnect.
  No new networking — partition is the *absence* of sync, which the mesh already supports. Do NOT change
  `hashdag.py`/`crdt.py`/`replica.py`/`mesh.py` semantics.
- Snapshot each side's `replica.shapes()` per step for the diptych; reuse `render_png`/`render_gif` and the
  Iteration-1 GIF writer. Deterministic for a fixed seed. Cap shapes/frames so the GIF stays ~1MB.
- Add `partition` to `main.py`; leave `demo`/`peer`/`web`/the Iteration 1–2 commands untouched.

**Testing (deterministic, offline, CI-safe):**
- `test_partition_diverges`: after the split phase the two sides' canvases are **not** equal (each has ops
  the other lacks) — the divergence is real.
- `test_heal_converges`: after reconnect + sync, both sides have identical shapes and identical DAG head
  sets, and the union shape count equals A's + B's distinct contributions (nothing lost, nothing duplicated).
- `test_partition_gif`: `partition --gif` writes a valid multi-frame GIF (`GIF89a`, frames > 1). Keep the
  Iteration 1–2 convergence/DAG tests and all CRDT/mesh tests green.

**Share-worthy angle:** A split-screen clip where two halves of a peer network **go offline, draw different
things, then reconnect and heal into the exact same picture** — no server, no lost strokes — captioned
"this is what 'offline-first' actually means," backed by a content-addressed Merkle-CRDT.
