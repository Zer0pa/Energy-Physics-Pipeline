"""Audit/KG mandatory enforcement — per CPU hardening §2.

When ENERGY_AUDIT_REQUIRED=true (production default), accepted outputs must:
  - Write to an audit writer (process default if none provided).
  - Write to a KG store (process default if none provided).
  - Refuse with `EnvelopeRejected` under strict gate when the envelope's
    final gate_status is fail or quarantine.

When ENERGY_AUDIT_REQUIRED=false (lab/explicit override), audit + KG writes are
skipped silently.
"""
from __future__ import annotations

import pytest

from energy_physics_pipeline.audit import AuditWriter
from energy_physics_pipeline.kg import KGStore
from energy_physics_pipeline.l6 import (
    EnvelopeRejected,
    accept_envelope,
    accept_envelope_and_dro,
    reload as cfg_reload,
)
from energy_physics_pipeline.l6.enforcement import reset_default_audit_kg
from energy_physics_pipeline.schemas import (
    BackendBlock,
    DeviceFamily,
    DeviceResponseObject,
    Domain,
    ExecutionMode,
    GateStatus,
    LayerLevel,
    LicenseClass,
    Mode,
    SubVertical,
    UniversalLayerEnvelope,
)
from energy_physics_pipeline.schemas.dro import DroAuditBlock, OperatingConditions, ResponseBlock
from energy_physics_pipeline.schemas.envelope import (
    FalsificationBlock,
    IOBlock,
    ProvenanceBlock,
)


def _good_envelope(domain: Domain = Domain.battery) -> UniversalLayerEnvelope:
    return UniversalLayerEnvelope(
        campaign_id="audit-required",
        sub_vertical=SubVertical.electrochemistry,
        layer=LayerLevel.L4,
        domain=domain,
        mode=Mode.scientific,
        backend=BackendBlock(
            adapter="test-adapter",
            tool="PyBaMM",
            tool_version="26.4",
            execution_mode=ExecutionMode.local_cpu,
            license_class=LicenseClass.A,
            license_evidence_uri="https://github.com/pybamm-team/PyBaMM/blob/develop/LICENSE.txt",
        ),
        outputs=IOBlock(
            payload={
                "quantities": {
                    "ocv_V": {"value": 3.7, "unit": "V"},
                    "capacity_Ah": {"value": 2.4, "unit": "Ah"},
                }
            }
        ),
        falsification=FalsificationBlock(
            gate_status=GateStatus.pass_,
            scientific_valid=True,
            unit_check_passed=True,
            conservation_check_passed=True,
            boundary_check_passed=True,
        ),
        provenance=ProvenanceBlock(
            agent_id="t",
            model_id="t",
            git_sha="t",
            input_hash="0" * 64,
            output_hash="0" * 64,
            config_hash="0" * 64,
        ),
    ).finalize()


@pytest.fixture()
def tmp_audit_kg(tmp_path):
    audit = AuditWriter(jsonl_dir=tmp_path / "audit", db_path=tmp_path / "audit.duckdb")
    kg = KGStore(kg_dir=tmp_path / "kg")
    reset_default_audit_kg(audit, kg)
    yield audit, kg
    reset_default_audit_kg(None, None)
    try:
        audit.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# A) Strict-mode + audit_required=true => audit + KG written for good envelope
# ---------------------------------------------------------------------------


def test_strict_mode_writes_audit_and_kg(monkeypatch: pytest.MonkeyPatch, tmp_audit_kg):
    audit, kg = tmp_audit_kg
    monkeypatch.setenv("ENERGY_BOUNDARY_GATE", "strict")
    monkeypatch.setenv("ENERGY_AUDIT_REQUIRED", "true")
    cfg_reload()

    env = _good_envelope()
    n_before = audit.count()
    nodes_before = kg.stats()["nodes"]
    accepted = accept_envelope(env)
    assert accepted.envelope_id is not None
    assert audit.count() == n_before + 1, "audit row not written"
    assert kg.stats()["nodes"] >= nodes_before + 1, "KG node not written"


# ---------------------------------------------------------------------------
# B) Strict-mode + envelope with gate_status=fail => EnvelopeRejected raised
# ---------------------------------------------------------------------------


def test_strict_mode_refuses_failed_envelope(monkeypatch: pytest.MonkeyPatch, tmp_audit_kg):
    monkeypatch.setenv("ENERGY_BOUNDARY_GATE", "strict")
    monkeypatch.setenv("ENERGY_AUDIT_REQUIRED", "true")
    cfg_reload()

    # Build a payload that the units_recursive_falsifier will fail.
    env = _good_envelope().model_copy(
        update={
            "outputs": IOBlock(
                payload={
                    # Numeric physical leaf without unit + outside `quantities`.
                    "T_h_K": 600.0,  # has SI hint and no unit sibling
                }
            )
        }
    )

    with pytest.raises(EnvelopeRejected) as excinfo:
        accept_envelope(env)
    assert "strict gate refused" in str(excinfo.value)


# ---------------------------------------------------------------------------
# C) audit_required=false => audit + KG writes skipped silently
# ---------------------------------------------------------------------------


def test_audit_off_skips_writes(monkeypatch: pytest.MonkeyPatch, tmp_audit_kg):
    audit, kg = tmp_audit_kg
    monkeypatch.setenv("ENERGY_AUDIT_REQUIRED", "false")
    monkeypatch.setenv("ENERGY_BOUNDARY_GATE", "warn")
    cfg_reload()

    n_before = audit.count()
    nodes_before = kg.stats()["nodes"]

    env = _good_envelope()
    accepted = accept_envelope(env, write_audit=False, write_kg=False)
    assert accepted.envelope_id is not None
    assert audit.count() == n_before, "audit row written despite audit_required=false + write_audit=false"
    assert kg.stats()["nodes"] == nodes_before, "KG node written despite write_kg=false"


# ---------------------------------------------------------------------------
# D) accept_envelope_and_dro: DRO falsifier failures are attached to envelope
# ---------------------------------------------------------------------------


def test_dro_cocos_failures_attached_to_envelope(monkeypatch: pytest.MonkeyPatch, tmp_audit_kg):
    monkeypatch.setenv("ENERGY_BOUNDARY_GATE", "warn")
    monkeypatch.setenv("ENERGY_AUDIT_REQUIRED", "true")
    cfg_reload()

    env = _good_envelope(domain=Domain.fusion).model_copy(
        update={"sub_vertical": SubVertical.fusion}
    )
    from energy_physics_pipeline.schemas.dro import Axis

    dro = DeviceResponseObject(
        sub_vertical=SubVertical.fusion,
        device_family=DeviceFamily.tokamak,
        operating_conditions=OperatingConditions(
            axes=[Axis(name="psi", unit="", values=[0.0, 0.5, 1.0])],
        ),
        response=ResponseBlock(),
        audit=DroAuditBlock(envelope_id=env.envelope_id or "sha256:none"),
    ).finalize()

    accepted_env, accepted_dro = accept_envelope_and_dro(env, dro)
    failure_ids = {f.gate_id for f in accepted_env.falsification.failures}
    assert "cocos_unit_required" in failure_ids
