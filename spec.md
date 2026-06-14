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

---

## Iteration 4 (2026-06-14)
**Theme:** Save, Share, Merge — Portable Canvas Files

**Why this iteration:** Iterations 1–3 were all in-process *property demos* (convergence, the Merkle-DAG,
partition/heal). Two practical gaps remain that keep this from being a *usable* tool: there's **no
persistence** (close the process and your drawing is gone) and **no way to exchange a canvas between two
people who can't connect**. Both are solved at once by leaning on the thing that makes this project special —
**content addressing**: serialize the Merkle-DAG to a `.canvas` file, and importing one is just `add_op` over
each node, so it **dedupes and merges automatically**. The result is the purest "decentralized" story of all:
**no server, no WebRTC, not even a live connection** — two people email each other a small file and their
drawings merge perfectly. It's a real feature (save/load + offline interchange), not another demo.

**What this adds:**
- **Persistence**: `save <file.canvas>` / `open <file.canvas>` — write the replica's DAG (the
  content-addressed node set) to disk and reload it, reconstructing the exact canvas (state is a pure fold
  over the DAG, so load is deterministic).
- **Offline file-merge**: `merge <a.canvas> <b.canvas> [--out merged.canvas]` — import both node sets into one
  replica; because nodes are content-addressed, **duplicates collapse and the union converges** to one
  canvas regardless of order. Print `imported A=12 nodes, B=10, shared=6, merged=16, shapes=N`.
- A **two-person "sneakernet" demo**: alice and bob each draw offline, `save` their files, swap, `merge`, and
  render — proving two never-connected peers converge by passing a file. Render the merged `out/merged.png`.

**Implementation notes (keep it lean — reuse the DAG serialization):**
- Reuse `HashDAG`/`Node.to_dict`/`from_dict` and `Replica` — `save` dumps `{nodes:[node.to_dict()...]}` as
  JSON; `open`/`merge` calls `add_op`/the node-add path for each, which already verifies hashes (tamper
  rejection from Iteration 2 applies on import) and dedupes. Do NOT change `crdt.py`/`hashdag.py`/`mesh.py`
  semantics — this is serialization + a thin driver.
- Versioned header (`{"format":"dcc-canvas","v":1, ...}`); reject/ignore nodes whose content hash doesn't
  match their id (corrupt/tampered files surface, not silently merge). Reuse `render_png` for the output.
- Add `save`/`open`/`merge` to `main.py`; leave `demo`/`peer`/`web`/Iteration 1–3 commands untouched.

**Testing (deterministic, offline):**
- `test_save_load_roundtrip`: save a replica, load it into a fresh replica → identical shapes and identical
  DAG head set (persistence is faithful).
- `test_file_merge_converges`: two replicas drawing different shapes → merging their files (in either order)
  yields the same canvas, and `merged_nodes == |A ∪ B|` with `shared == |A ∩ B|` (dedup by content hash is
  real); a node tampered on disk is rejected on import.
- `test_merge_is_order_independent`: `merge(a,b) == merge(b,a)` in shapes and heads. Keep the Iteration 1–3
  convergence/DAG/partition tests and all CRDT/mesh tests green.

**Share-worthy angle:** Two people who **never connect** each draw, save a tiny `.canvas` file, email it to
each other, and `merge` — and their doodles fuse into one identical picture, duplicates collapsing for free —
"version control for drawings: no server, no network, just a file," from a content-addressed Merkle-CRDT.

## Iteration 5 (2026-06-13)
**Theme:** Branch & Merge Your Drawing
**Why this iteration:** The project has built the whole git metaphor — a content-addressed Merkle-DAG (Iter 2), partition/heal (Iter 3), portable files (Iter 4) — but you still can't do the *operations* git is famous for. Adding **checkout** (rewind the canvas to any past commit), **branch** (fork from there), and **merge** (fuse two branches via the CRDT) completes the metaphor and turns the drawing into a true version-controlled artifact: "try a risky edit on a branch, keep it or throw it away."
**What this adds:**
- **`checkout <commit>`**: reconstruct the canvas at any node in the Merkle-DAG (a past state) by replaying the ops in that commit's causal ancestry — non-destructive time travel.
- **`branch`/`fork`**: start a new line of edits from any commit; edits on different branches are independent.
- **`merge <branch>`**: combine two branches via the **existing CRDT merge** (op-set union — commutative/idempotent, so it's conflict-free), with the resulting branch graph rendered git-log style (lanes diverging and rejoining).
- A demo: draw a base, branch, add a hat on one branch and a smile on the other, merge → both appear.
**Implementation notes (keep it lean):**
- Reuse the Merkle-DAG from Iteration 2: a **commit** = a DAG node (its ancestry = the op set up to it). `checkout` = build a fresh canvas from that ancestor set (reuse `add_op`); `branch` = a named pointer to a commit; `merge` = union the two branches' op sets (the CRDT already makes this order-independent) and snapshot a merge commit. No new convergence logic — branches are just different frontiers over the same op-DAG.
- Render the branch graph by reusing the Iteration-2 DAG renderer with lane assignment per branch.
- `main.py`: `branch`/`checkout`/`merge` + a demo.
**Testing (deterministic, offline):**
- **Checkout** reconstructs the exact canvas state that existed at a given commit (digest matches the historical state). (2) **Branch isolation:** edits on branch B don't affect branch A's canvas until merged. (3) **Merge = union:** merging two branches yields the canvas containing **both** branches' strokes, identical regardless of merge order (commutativity), with duplicate ops collapsing. (4) The merged commit's ancestry includes both parents (a valid DAG); deterministic.
**Share-worthy angle:** `branch`, draw a wild idea, `merge` it back (or throw it away) — full checkout/branch/merge for a *drawing*, with a git-log graph of lanes splitting and rejoining, all conflict-free on a content-addressed Merkle-CRDT.
