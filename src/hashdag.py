"""A Merkle-DAG of operations: a content-addressed, causal operation history.

Every operation becomes a node identified by the SHA-256 of its content plus the
hashes of its parents (the DAG frontier when it was created) — exactly like Git
commits or IPFS / Merkle-CRDTs. Two peers that create the same operation get the
same hash (automatic dedup), and the parent links record causality, so the whole
history is tamper-evident and can be replayed deterministically.

Sync is content-addressed "have/want" anti-entropy: a peer announces the hashes
it already has; the other side replies with exactly the nodes it's missing, in
topological order (parents before children).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field


def _hash(op: dict, parents: list[str]) -> str:
    payload = json.dumps({"op": op, "parents": sorted(parents)},
                         sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


@dataclass
class Node:
    id: str
    op: dict
    parents: list[str]
    lamport: int

    def to_dict(self) -> dict:
        return {"id": self.id, "op": self.op, "parents": self.parents,
                "lamport": self.lamport}

    @classmethod
    def from_dict(cls, d: dict) -> "Node":
        return cls(id=d["id"], op=d["op"], parents=list(d["parents"]),
                   lamport=d["lamport"])


class HashDAG:
    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self._heads: set[str] = set()    # nodes with no children (the frontier)

    # --- writing ------------------------------------------------------------

    def add_op(self, op: dict) -> Node:
        """Create a new node whose parents are the current frontier."""
        parents = sorted(self._heads)
        lamport = 1 + max((self.nodes[p].lamport for p in parents), default=0)
        node = Node(id=_hash(op, parents), op=op, parents=parents, lamport=lamport)
        self._insert(node)
        return node

    def _insert(self, node: Node) -> bool:
        if node.id in self.nodes:
            return False
        self.nodes[node.id] = node
        # New node becomes a head; its parents are no longer heads.
        self._heads.add(node.id)
        for p in node.parents:
            self._heads.discard(p)
        return True

    def receive(self, node: Node) -> bool:
        """Insert a node received from a peer. Idempotent (content-addressed)."""
        return self._insert(node)

    def verify(self, node: Node) -> bool:
        """Check that a node's id actually matches its content (tamper-evidence)."""
        return node.id == _hash(node.op, node.parents)

    # --- reading ------------------------------------------------------------

    def heads(self) -> list[str]:
        return sorted(self._heads)

    def have(self) -> set[str]:
        return set(self.nodes)

    def topological(self) -> list[Node]:
        """Deterministic causal order: by (lamport, id), parents before children."""
        return sorted(self.nodes.values(), key=lambda n: (n.lamport, n.id))

    # --- sync ---------------------------------------------------------------

    def missing_for(self, remote_have: set[str]) -> list[Node]:
        """Nodes the remote is missing, in topological order (parents first)."""
        return [n.to_dict() for n in self.topological() if n.id not in remote_have]
