"""Wave 4 §2 — every accepted output MUST emit audit + KG evidence.

Probes:
  REST   → /v1/electrochem/l4/pybamm under audit_required=true increases counts
  Parser → StructureParserAdapter.parse_cif increases counts (now writes audit)
  Adapter → PyBaMMBatteryAdapter().run + accept_envelope_and_dro increases counts
  MCP    → pybamm_mcp.simulate_discharge tool call increases counts
"""
from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

from energy_pipeline.audit import AuditWriter
from energy_pipeline.kg import KGStore
from energy_pipeline.l6 import reload as cfg_reload
from energy_pipeline.l6.enforcement import reset_default_audit_kg


@pytest.fixture()
def tmp_audit_kg(tmp_path, monkeypatch):
    audit = AuditWriter(jsonl_dir=tmp_path / "audit", db_path=tmp_path / "a.duckdb")
    kg = KGStore(kg_dir=tmp_path / "kg")
    reset_default_audit_kg(audit, kg)
    monkeypatch.setenv("ENERGY_AUDIT_DIR", str(tmp_path / "audit"))
    monkeypatch.setenv("ENERGY_KG_DIR", str(tmp_path / "kg"))
    monkeypatch.setenv("ENERGY_AUDIT_REQUIRED", "true")
    monkeypatch.setenv("ENERGY_BOUNDARY_GATE", "warn")
    cfg_reload()
    yield audit, kg
    reset_default_audit_kg(None, None)
    try:
        audit.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# REST path
# ---------------------------------------------------------------------------


def test_rest_endpoint_writes_audit_and_kg(tmp_audit_kg, monkeypatch):
    audit, kg = tmp_audit_kg
    monkeypatch.setenv("ENERGY_L4_BACKEND", "gpu_rest_stub")  # cheap stub path
    cfg_reload()
    from energy_pipeline.rest import create_app

    n0_audit = audit.count()
    n0_kg_nodes = kg.stats()["nodes"]

    client = TestClient(create_app())
    r = client.post("/v1/electrochem/l4/pybamm", json={"campaign_id": "rest-audit-test"})
    assert r.status_code == 200

    assert audit.count() == n0_audit + 1, "REST endpoint did not write audit row"
    assert kg.stats()["nodes"] >= n0_kg_nodes + 1, "REST endpoint did not write KG node"


# ---------------------------------------------------------------------------
# Parser path
# ---------------------------------------------------------------------------


_CIF_SAMPLE = """
data_TestCell
_cell_length_a 5.0
_cell_length_b 5.0
_cell_length_c 5.0
_cell_angle_alpha 90.0
_cell_angle_beta 90.0
_cell_angle_gamma 90.0
"""


def test_parser_writes_audit_and_kg(tmp_audit_kg):
    audit, kg = tmp_audit_kg
    n0 = audit.count()
    nodes0 = kg.stats()["nodes"]

    from energy_pipeline.adapters.electrochem.parsers import StructureParserAdapter

    StructureParserAdapter().parse_cif(_CIF_SAMPLE)

    assert audit.count() == n0 + 1, "parser did not write audit row"
    assert kg.stats()["nodes"] >= nodes0 + 1, "parser did not write KG node"


# ---------------------------------------------------------------------------
# Adapter path — call PyBaMM, then accept_envelope explicitly
# ---------------------------------------------------------------------------


def test_adapter_via_accept_envelope_writes_audit_kg(tmp_audit_kg):
    pytest.importorskip("pybamm")
    audit, kg = tmp_audit_kg
    n0 = audit.count()
    nodes0 = kg.stats()["nodes"]

    from energy_pipeline.adapters.electrochem.l4 import PyBaMMBatteryAdapter
    from energy_pipeline.l6 import accept_envelope_and_dro

    env, dro = PyBaMMBatteryAdapter().run({"campaign_id": "adapter-audit-test"})
    accept_envelope_and_dro(env, dro)

    assert audit.count() >= n0 + 1, "adapter accept_envelope did not write audit row"
    assert kg.stats()["nodes"] >= nodes0 + 2, "adapter accept_envelope did not write SimulationRun + DRO"


# ---------------------------------------------------------------------------
# MCP path
# ---------------------------------------------------------------------------


def test_mcp_pybamm_writes_audit_kg(tmp_audit_kg):
    pytest.importorskip("pybamm")
    pytest.importorskip("mcp")
    audit, kg = tmp_audit_kg
    n0 = audit.count()
    nodes0 = kg.stats()["nodes"]

    importlib.invalidate_caches()
    from energy_pipeline.mcp_servers import pybamm_mcp

    server = pybamm_mcp.build_server()
    tool = server._tool_manager._tools["simulate_discharge"]
    tool.fn(rate_C=1.0, duration_s=120.0)

    assert audit.count() >= n0 + 1, "MCP tool did not write audit row"
    assert kg.stats()["nodes"] >= nodes0 + 1, "MCP tool did not write KG node"
