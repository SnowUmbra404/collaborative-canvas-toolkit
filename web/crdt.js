const isBrowser = typeof window !== "undefined" && typeof window.crypto !== "undefined";

function jsonMinify(obj) {
  if (Array.isArray(obj)) {
    return "[" + obj.map(jsonMinify).join(",") + "]";
  }
  if (obj !== null && typeof obj === "object") {
    const keys = Object.keys(obj).sort();
    return "{" + keys.map(k => JSON.stringify(k) + ":" + jsonMinify(obj[k])).join(",") + "}";
  }
  return JSON.stringify(obj);
}

async function computeNodeId(op, parents) {
  const canonical = { op, parents: [...parents].sort() };
  const payload = jsonMinify(canonical);
  if (isBrowser) {
    const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(payload));
    return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, "0")).join("");
  } else {
    const { createHash } = await import("node:crypto");
    return createHash("sha256").update(payload).digest("hex");
  }
}

async function verifyNode(node) {
  const id = await computeNodeId(node.op, node.parents);
  return id === node.id;
}

function topological(nodes) {
  return Object.values(nodes).sort((a, b) => {
    if (a.lamport !== b.lamport) return a.lamport - b.lamport;
    return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
  });
}

function stampGt(a, b) {
  if (a[0] !== b[0]) return a[0] > b[0];
  return a[1] > b[1];
}

function setDiff(a, b) {
  const result = new Set();
  for (const v of a) if (!b.has(v)) result.add(v);
  return result;
}

function foldOps(nodeList) {
  const addTags = {};
  const removedTags = {};
  const props = {};
  const base = {};

  for (const node of nodeList) {
    const op = node.op;
    const sid = op.shape_id;
    const stamp = [node.lamport, op.peer || ""];

    if (op.type === "add") {
      if (!addTags[sid]) addTags[sid] = new Set();
      addTags[sid].add(node.id);
      if (!base[sid]) {
        base[sid] = { kind: op.kind, x: op.x, y: op.y, w: op.w, h: op.h, color: op.color };
      }
      if (!props[sid]) props[sid] = {};
      for (const k of ["x", "y", "w", "h", "color"]) {
        const cur = props[sid][k];
        if (cur === undefined || stampGt(stamp, cur[0])) {
          props[sid][k] = [stamp, op[k]];
        }
      }
    } else if (op.type === "remove") {
      if (!removedTags[sid]) removedTags[sid] = new Set();
      for (const t of (op.observed || [])) removedTags[sid].add(t);
    } else {
      if (!props[sid]) props[sid] = {};
      for (const [k, v] of Object.entries(op.changes || {})) {
        const cur = props[sid][k];
        if (cur === undefined || stampGt(stamp, cur[0])) {
          props[sid][k] = [stamp, v];
        }
      }
    }
  }

  const out = [];
  for (const [sid, tags] of Object.entries(addTags)) {
    const surviving = setDiff(tags, removedTags[sid] || new Set());
    if (surviving.size === 0) continue;
    const pr = props[sid] || {};
    const b = base[sid] || {};
    out.push({
      id: sid,
      kind: b.kind || "rect",
      x: pr.x !== undefined ? pr.x[1] : (b.x || 0),
      y: pr.y !== undefined ? pr.y[1] : (b.y || 0),
      w: pr.w !== undefined ? pr.w[1] : (b.w || 0),
      h: pr.h !== undefined ? pr.h[1] : (b.h || 0),
      color: pr.color !== undefined ? pr.color[1] : (b.color || "black"),
    });
  }
  return out.sort((a, b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
}

function shapesDigest(shapes) {
  return shapes.map(s => [
    s.id, s.kind,
    Math.round(s.x * 10000) / 10000,
    Math.round(s.y * 10000) / 10000,
    Math.round(s.w * 10000) / 10000,
    Math.round(s.h * 10000) / 10000,
    s.color,
  ]);
}

export class ORMapReplica {
  constructor(peerId) {
    this.peerId = peerId;
    this.nodes = {};
    this.heads = new Set();
    this._shapeSeq = 0;
  }

  _newShapeId() {
    this._shapeSeq += 1;
    return `${this.peerId}:${this._shapeSeq}`;
  }

  async _addOp(op) {
    const parents = [...this.heads].sort();
    const lamport = parents.length === 0
      ? 1
      : 1 + parents.reduce((max, p) => Math.max(max, this.nodes[p].lamport), 0);
    const id = await computeNodeId(op, parents);
    const node = { id, op, parents, lamport };
    this._insert(node);
    return node;
  }

  _insert(node) {
    if (this.nodes[node.id]) return false;
    this.nodes[node.id] = node;
    this.heads.add(node.id);
    for (const p of node.parents) this.heads.delete(p);
    return true;
  }

  async addShape(kind, x, y, w, h, color) {
    const sid = this._newShapeId();
    return this._addOp({
      type: "add", peer: this.peerId, shape_id: sid,
      kind, x, y, w, h, color,
    });
  }

  async setProps(shapeId, changes) {
    return this._addOp({
      type: "set", peer: this.peerId, shape_id: shapeId, changes,
    });
  }

  async removeShape(shapeId) {
    const observed = Object.values(this.nodes)
      .filter(n => n.op.type === "add" && n.op.shape_id === shapeId)
      .map(n => n.id);
    return this._addOp({
      type: "remove", peer: this.peerId, shape_id: shapeId, observed,
    });
  }

  async receive(node) {
    const valid = await verifyNode(node);
    if (!valid) return false;
    return this._insert(node);
  }

  shapes() {
    return foldOps(topological(this.nodes));
  }

  digest() {
    return JSON.stringify(shapesDigest(this.shapes()));
  }

  have() {
    return new Set(Object.keys(this.nodes));
  }

  summary() {
    return [...this.have()].sort();
  }

  missingFor(remoteHave) {
    const have = remoteHave instanceof Set ? remoteHave : new Set(remoteHave);
    return topological(this.nodes)
      .filter(n => !have.has(n.id))
      .map(n => ({ id: n.id, op: n.op, parents: n.parents, lamport: n.lamport }));
  }
}
