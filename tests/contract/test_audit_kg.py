"""Contract tests for AuditWriter and KGStore."""
from __future__ import annotations

from pathlib import Path

import pytest

from energy_pipeline.audit import AuditWriter
from energy_pipeline.boundary import BOUNDARY_BLOCK, BoundaryViolation
from energy_pipeline.kg import NODE_TYPES, KGStore


def _good_payload(**overrides):
    base = {
        "boundary": BOUNDARY_BLOCK,
        "envelope_id": "sha256:abc",
        "run_id": "r1",
        "sub_vertical": "electrochemistry",
        "layer": "L4",
        "domain": "battery",
        "mode": "engineering_stub",
        "backend": {"license_class": "A", "execution_mode": "local_cpu"},
        "falsification": {
            "gate_status": "pass",
            "scientific_valid": False,
            "boundary_check_passed": True,
        },
    }
    base.update(overrides)
    return base


def test_audit_writes_jsonl_and_duckdb(tmp_path: Path):
    aw = AuditWriter(jsonl_dir=tmp_path / "j", db_path=tmp_path / "a.duckdb")
    sha = aw.write_event("envelope.v0.1", _good_payload())
    assert len(sha) == 64
    assert aw.count() == 1
    rows = aw.query("SELECT envelope_id, layer, mode FROM audit_events")
    assert rows[0][0] == "sha256:abc"
    assert rows[0][1] == "L4"
    aw.close()


def test_audit_refuses_payload_without_boundary(tmp_path: Path):
    aw = AuditWriter(jsonl_dir=tmp_path / "j", db_path=tmp_path / "a.duckdb")
    bad = _good_payload(boundary="NOT THE BOUNDARY")
    with pytest.raises(BoundaryViolation):
        aw.write_event("envelope.v0.1", bad)
    aw.close()


def test_audit_refuses_payload_missing_boundary(tmp_path: Path):
    aw = AuditWriter(jsonl_dir=tmp_path / "j", db_path=tmp_path / "a.duckdb")
    bad = _good_payload()
    bad.pop("boundary")
    with pytest.raises(BoundaryViolation):
        aw.write_event("envelope.v0.1", bad)
    aw.close()


def test_kg_node_types_all_known(tmp_path: Path):
    kg = KGStore(kg_dir=tmp_path)
    # one of each node type, with boundary_required=False since these are metadata
    for nt in NODE_TYPES:
        kg.add_node(nt, f"{nt}-1", {"foo": "bar"}, boundary_required=False)
    assert kg.stats()["nodes"] == len(NODE_TYPES)


def test_kg_unknown_node_kind_rejected(tmp_path: Path):
    kg = KGStore(kg_dir=tmp_path)
    with pytest.raises(ValueError):
        kg.add_node("NotARealKind", "x", {}, boundary_required=False)


def test_kg_unknown_edge_kind_rejected(tmp_path: Path):
    kg = KGStore(kg_dir=tmp_path)
    kg.add_node("ToolAdapter", "a", {}, boundary_required=False)
    kg.add_node("ToolAdapter", "b", {}, boundary_required=False)
    with pytest.raises(ValueError):
        kg.add_edge("NOT_A_REAL_EDGE", "a", "b", {})


def test_kg_node_with_boundary_required_blocks_missing_boundary(tmp_path: Path):
    kg = KGStore(kg_dir=tmp_path)
    with pytest.raises(BoundaryViolation):
        kg.add_node("SimulationRun", "s1", {"foo": "bar"})  # boundary_required default True
