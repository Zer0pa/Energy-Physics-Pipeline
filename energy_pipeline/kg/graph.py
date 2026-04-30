"""Knowledge-graph store — JSONL nodes/edges + GraphML/JSON export.

Per PRD minimums:

Nodes: CandidateMaterial, DeviceResponseObject, FusionScenario, PulseWindow,
       SourceManifest, ToolAdapter, ModelCheckpoint, SimulationRun,
       FalsifierResult, DisagreementRecord, LicenseFinding, RightsPolicy,
       GroundTruthObservation, ReasonerTuple

Edges: DERIVED_FROM, USED_TOOL, USED_MODEL, USED_SOURCE, PRODUCED,
       VALIDATED_BY, FAILED_BY, DISAGREES_WITH, FEEDS_L4, FEEDS_L5,
       OWNED_BY, RIGHTS_CONSTRAINED_BY
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import networkx as nx

from energy_pipeline.boundary import verify_boundary, BoundaryViolation
from energy_pipeline.schemas.canonical import canonical_json, sha256_of

NODE_TYPES = (
    "CandidateMaterial",
    "DeviceResponseObject",
    "FusionScenario",
    "PulseWindow",
    "SourceManifest",
    "ToolAdapter",
    "ModelCheckpoint",
    "SimulationRun",
    "FalsifierResult",
    "DisagreementRecord",
    "LicenseFinding",
    "RightsPolicy",
    "GroundTruthObservation",
    "ReasonerTuple",
)

EDGE_TYPES = (
    "DERIVED_FROM",
    "USED_TOOL",
    "USED_MODEL",
    "USED_SOURCE",
    "PRODUCED",
    "VALIDATED_BY",
    "FAILED_BY",
    "DISAGREES_WITH",
    "FEEDS_L4",
    "FEEDS_L5",
    "OWNED_BY",
    "RIGHTS_CONSTRAINED_BY",
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_kg_dir() -> Path:
    """KG JSONL directory. Reads `ENERGY_KG_DIR` env for parallel-safe runtime per
    worktree/subagent (Wave 4 §3)."""
    import os as _os

    override = _os.environ.get("ENERGY_KG_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return _project_root() / "kg_store"


class KGStore:
    """Append-only JSONL store; in-memory NetworkX graph for traversal/export.

    Boundary: nodes representing artifacts must carry the boundary block; pure-metadata
    nodes (e.g. ToolAdapter) may omit it but must record `boundary_required=False`.
    """

    def __init__(self, kg_dir: Path | None = None) -> None:
        self.kg_dir = Path(kg_dir or default_kg_dir())
        self.kg_dir.mkdir(parents=True, exist_ok=True)
        self.nodes_path = self.kg_dir / "nodes.jsonl"
        self.edges_path = self.kg_dir / "edges.jsonl"
        self._lock = threading.RLock()
        self._g: nx.MultiDiGraph = nx.MultiDiGraph()
        self._load()

    def _load(self) -> None:
        if self.nodes_path.exists():
            with self.nodes_path.open("rb") as fp:
                for line in fp:
                    if not line.strip():
                        continue
                    n = json.loads(line)
                    self._g.add_node(n["id"], **n)
        if self.edges_path.exists():
            with self.edges_path.open("rb") as fp:
                for line in fp:
                    if not line.strip():
                        continue
                    e = json.loads(line)
                    self._g.add_edge(e["src"], e["dst"], key=e.get("kind"), **e)

    def add_node(
        self,
        kind: str,
        node_id: str,
        attrs: Mapping[str, Any],
        *,
        boundary_required: bool = True,
    ) -> str:
        if kind not in NODE_TYPES:
            raise ValueError(f"unknown node kind: {kind} not in {NODE_TYPES}")
        if boundary_required and not verify_boundary(attrs):
            raise BoundaryViolation(f"KG node {kind}/{node_id} missing boundary block")
        ts = datetime.now(timezone.utc).isoformat()
        record = {
            "id": node_id,
            "kind": kind,
            "ts": ts,
            "attrs": dict(attrs),
            "boundary_required": boundary_required,
        }
        sha = sha256_of(record)
        record["sha256"] = sha
        with self._lock:
            with self.nodes_path.open("ab") as fp:
                fp.write(canonical_json(record))
                fp.write(b"\n")
            self._g.add_node(node_id, **record)
        return sha

    def add_edge(
        self,
        kind: str,
        src: str,
        dst: str,
        attrs: Mapping[str, Any] | None = None,
    ) -> str:
        if kind not in EDGE_TYPES:
            raise ValueError(f"unknown edge kind: {kind} not in {EDGE_TYPES}")
        ts = datetime.now(timezone.utc).isoformat()
        record = {
            "kind": kind,
            "src": src,
            "dst": dst,
            "ts": ts,
            "attrs": dict(attrs or {}),
        }
        sha = sha256_of(record)
        record["sha256"] = sha
        with self._lock:
            with self.edges_path.open("ab") as fp:
                fp.write(canonical_json(record))
                fp.write(b"\n")
            self._g.add_edge(src, dst, key=kind, **record)
        return sha

    def export_graphml(self, dst: Path) -> Path:
        # GraphML can't store nested dicts; flatten attrs.
        flat = nx.MultiDiGraph()
        for n, data in self._g.nodes(data=True):
            flat.add_node(n, **{k: json.dumps(v, default=str) for k, v in data.items()})
        for u, v, k, data in self._g.edges(keys=True, data=True):
            flat.add_edge(u, v, key=k, **{kk: json.dumps(vv, default=str) for kk, vv in data.items()})
        nx.write_graphml(flat, str(dst))
        return Path(dst)

    def stats(self) -> dict[str, int]:
        return {
            "nodes": self._g.number_of_nodes(),
            "edges": self._g.number_of_edges(),
        }

    def neighbours(self, node_id: str) -> list[tuple[str, str]]:
        if node_id not in self._g:
            return []
        return [(v, d.get("kind", "")) for _, v, d in self._g.out_edges(node_id, data=True)]
