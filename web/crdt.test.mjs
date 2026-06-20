import { ORMapReplica } from "./crdt.js";

function shuffle(arr, rng) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function mulberry32(seed) {
  return () => {
    seed |= 0;
    seed = seed + 0x6d2b79f5 | 0;
    let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

async function runSeed(seed, nPeers, nOps) {
  const rng = mulberry32(seed);
  const peers = Array.from({ length: nPeers }, (_, i) => new ORMapReplica(`peer${i}`));

  const allNodes = [];
  const kinds = ["rect", "ellipse", "line"];
  const colors = ["red", "green", "blue", "yellow", "magenta"];

  for (let i = 0; i < nOps; i++) {
    const peer = peers[Math.floor(rng() * nPeers)];
    const action = rng();

    if (action < 0.6) {
      const kind = kinds[Math.floor(rng() * kinds.length)];
      const color = colors[Math.floor(rng() * colors.length)];
      const node = await peer.addShape(kind, rng(), rng(), rng() * 0.5 + 0.05, rng() * 0.5 + 0.05, color);
      allNodes.push(node);
    } else if (action < 0.85) {
      const shapes = peer.shapes();
      if (shapes.length > 0) {
        const s = shapes[Math.floor(rng() * shapes.length)];
        const color = colors[Math.floor(rng() * colors.length)];
        const node = await peer.setProps(s.id, { color, x: rng(), y: rng() });
        allNodes.push(node);
      }
    } else {
      const shapes = peer.shapes();
      if (shapes.length > 0) {
        const s = shapes[Math.floor(rng() * shapes.length)];
        const node = await peer.removeShape(s.id);
        allNodes.push(node);
      }
    }
  }

  const dedupedByIdMap = new Map();
  for (const n of allNodes) dedupedByIdMap.set(n.id, n);
  const uniqueNodes = [...dedupedByIdMap.values()];

  for (const peer of peers) {
    const shuffled = shuffle(uniqueNodes, rng);
    const doubled = [...shuffled, ...shuffle(uniqueNodes, rng)];
    for (const node of doubled) {
      await peer.receive(node);
    }
  }

  const digests = peers.map(p => p.digest());
  const allSame = digests.every(d => d === digests[0]);

  if (!allSame) {
    console.error(`DIVERGENCE at seed=${seed}`);
    for (let i = 0; i < peers.length; i++) {
      console.error(`  peer${i}: ${digests[i]}`);
    }
    return false;
  }

  console.log(`seed=${seed} nPeers=${nPeers} nOps=${nOps} ops=${uniqueNodes.length} shapes=${peers[0].shapes().length} digest=${digests[0].slice(0, 32)}... OK`);
  return true;
}

async function main() {
  const cases = [
    [1, 3, 20],
    [2, 4, 30],
    [42, 5, 40],
    [999, 2, 15],
    [12345, 3, 25],
    [7, 4, 50],
  ];

  let allPassed = true;
  for (const [seed, nPeers, nOps] of cases) {
    const ok = await runSeed(seed, nPeers, nOps);
    if (!ok) allPassed = false;
  }

  if (!allPassed) {
    console.error("FAIL: divergence detected");
    process.exit(1);
  }
  console.log("All convergence tests passed.");
}

main();
