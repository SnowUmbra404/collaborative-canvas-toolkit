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
