"""Wave 4 §7 — OPTIMADE / Materials Project / NOMAD pointer manifest tests.

Each pointer adapter must:
  * accept a query string + intended downstream layer/domain
  * emit a manifest-only envelope (no bulk data ever stored)
  * carry a license / rights note matching upstream policy
  * pass through `accept_envelope` (audit + KG written)
"""
from __future__ import annotations


from energy_physics_pipeline.adapters.electrochem.data_pointers import (
    DataPointerAdapter,
    materials_project_pointer,
    nomad_pointer,
    optimade_pointer,
)
from energy_physics_pipeline.boundary import BOUNDARY_BLOCK
from energy_physics_pipeline.l6 import reload as cfg_reload
from energy_physics_pipeline.schemas import Domain, LayerLevel, Mode, SubVertical


def _isolated_runtime(monkeypatch, tmp_path):
    monkeypatch.setenv("ENERGY_AUDIT_DIR", str(tmp_path / "audit"))
    monkeypatch.setenv("ENERGY_KG_DIR", str(tmp_path / "kg"))
    monkeypatch.setenv("ENERGY_BOUNDARY_GATE", "warn")
    cfg_reload()
    from energy_physics_pipeline.l6.enforcement import reset_default_audit_kg

    reset_default_audit_kg(None, None)


def test_optimade_pointer_manifest_envelope_shape(monkeypatch, tmp_path):
    _isolated_runtime(monkeypatch, tmp_path)
    spec = optimade_pointer(
        query_string='filter=elements HAS "Li" AND nelements<=3',
        intended_downstream_layer=LayerLevel.L1,
        intended_downstream_domain=Domain.battery,
    )
    env = DataPointerAdapter().emit(spec)
    assert env.boundary == BOUNDARY_BLOCK
    assert env.mode == Mode.engineering_stub
    assert env.sub_vertical == SubVertical.electrochemistry
    out = env.outputs.payload
    assert out["source_kind"] == "optimade"
    assert out["bulk_data_stored"] is False
    assert out["manifest_only"] is True
    assert out["query_string"].startswith("filter=elements HAS")
    assert "providers.optimade.org" in out["source_uri"]


def test_materials_project_pointer_manifest_envelope_shape(monkeypatch, tmp_path):
    _isolated_runtime(monkeypatch, tmp_path)
    spec = materials_project_pointer(
        query_string="elements=Si,O&band_gap_min=1.0&band_gap_max=3.0",
        intended_downstream_layer=LayerLevel.L1,
        intended_downstream_domain=Domain.pv,
    )
    env = DataPointerAdapter().emit(spec)
    assert env.outputs.payload["source_kind"] == "materials_project"
    assert "CC-BY-4.0" in env.outputs.payload["license_spdx_or_text"]
    assert env.outputs.payload["bulk_data_stored"] is False


def test_nomad_pointer_manifest_envelope_shape(monkeypatch, tmp_path):
    _isolated_runtime(monkeypatch, tmp_path)
    spec = nomad_pointer(
        query_string='results.material.elements has "Pt"',
        intended_downstream_layer=LayerLevel.L2,
        intended_downstream_domain=Domain.green_h2,
    )
    env = DataPointerAdapter().emit(spec)
    assert env.outputs.payload["source_kind"] == "nomad"
    assert env.outputs.payload["intended_downstream_layer"] == "L2"
    assert env.outputs.payload["intended_downstream_domain"] == "green_h2"


def test_pointer_envelope_carries_manifest_sha(monkeypatch, tmp_path):
    _isolated_runtime(monkeypatch, tmp_path)
    spec = optimade_pointer(query_string="elements=O,H")
    env = DataPointerAdapter().emit(spec)
    assert "manifest_sha256" in env.outputs.payload
    assert len(env.outputs.payload["manifest_sha256"]) == 64


def test_pointer_envelope_writes_audit_when_requested(monkeypatch, tmp_path):
    """When write_audit=True (the default), accept_envelope writes a row."""
    _isolated_runtime(monkeypatch, tmp_path)
    from energy_physics_pipeline.audit import AuditWriter
    from energy_physics_pipeline.kg import KGStore
    from energy_physics_pipeline.l6.enforcement import reset_default_audit_kg

    audit = AuditWriter(jsonl_dir=tmp_path / "a", db_path=tmp_path / "a.duckdb")
    kg = KGStore(kg_dir=tmp_path / "kg2")
    reset_default_audit_kg(audit, kg)
    n0 = audit.count()

    DataPointerAdapter().emit(materials_project_pointer(query_string="elements=Li"))

    assert audit.count() == n0 + 1
    audit.close()
    reset_default_audit_kg(None, None)
