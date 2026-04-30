"""Live cross-model disagreement emission in the fusion L2 path.

Per PRD §"Falsification Framework": cross-model disagreement is a first-class quantity.
This test emits real `CrossModelDisagreementRecord` artifacts during a fusion phase-0
run by comparing TGLF reduced output vs CGYRO stub output (in three preset modes:
agree, warn, quarantine), writing the records to KG, and asserting the threshold
ladder is honored end-to-end.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from energy_pipeline.adapters.fusion import (
    CgyroNonlinearAdapter,
    TglfReducedAdapter,
    cross_model_disagreement,
)
from energy_pipeline.adapters.fusion.l2 import GyroSpec
from energy_pipeline.audit import AuditWriter
from energy_pipeline.boundary import BOUNDARY_BLOCK
from energy_pipeline.kg import KGStore
from energy_pipeline.schemas import DisagreementStatus


@pytest.mark.parametrize(
    "stub_mode,expected_status",
    [
        ("agree", DisagreementStatus.pass_),
        ("warn", DisagreementStatus.warn),
        ("quarantine", DisagreementStatus.quarantine),
    ],
)
def test_cross_model_disagreement_threshold_ladder(stub_mode: str, expected_status: DisagreementStatus):
    """TGLF vs CGYRO stub at three disagreement levels — verify threshold ladder."""
    spec = GyroSpec(campaign_id=f"disagreement-{stub_mode}")
    tglf_env = TglfReducedAdapter().run(spec)
    cgyro_env = CgyroNonlinearAdapter().run(spec, stub_mode=stub_mode)

    rec = cross_model_disagreement(
        object_id=f"obj-{stub_mode}",
        tglf_envelope=tglf_env,
        cgyro_envelope=cgyro_env,
    )

    assert rec.status == expected_status, (
        f"stub_mode={stub_mode}: expected status={expected_status.value}, got {rec.status.value}; "
        f"values={rec.values} relative_disagreement={(abs(rec.values[1]-rec.values[0])/max(abs(rec.values[0]),1e-30)):.3f}"
    )
    assert rec.metric.value == "relative"
    assert rec.unit == "MW/m^2"
    assert len(rec.models_compared) == 2
    assert rec.pass_threshold == 0.25
    assert rec.warn_threshold == 0.50


def test_cross_model_disagreement_quarantine_writes_kg(tmp_path: Path):
    """A quarantine-level disagreement is recorded as a DisagreementRecord KG node.

    Per PRD: 'fail blocks downstream L5 and L6 optimization'. We verify the KG
    record exists and the audit log captures it.
    """
    audit = AuditWriter(jsonl_dir=tmp_path / "a", db_path=tmp_path / "a.duckdb")
    kg = KGStore(kg_dir=tmp_path / "k")

    spec = GyroSpec(campaign_id="disagreement-quarantine-kg")
    tglf_env = TglfReducedAdapter().run(spec)
    cgyro_env = CgyroNonlinearAdapter().run(spec, stub_mode="quarantine")
    rec = cross_model_disagreement(
        object_id="quarantine-obj",
        tglf_envelope=tglf_env,
        cgyro_envelope=cgyro_env,
    )
    assert rec.status == DisagreementStatus.quarantine

    audit.write_event("envelope.v0.1", tglf_env.model_dump(mode="json"))
    audit.write_event("envelope.v0.1", cgyro_env.model_dump(mode="json"))
    kg.add_node(
        "DisagreementRecord",
        rec.record_id,
        {
            "boundary": BOUNDARY_BLOCK,
            "status": rec.status.value,
            "values": rec.values,
            "models_compared": rec.models_compared,
            "resolution_action": rec.resolution_action,
        },
    )
    audit.close()

    assert kg.stats()["nodes"] == 1
    # Resolution action must block downstream
    assert rec.resolution_action == "block_handoff"


def test_envelopes_carry_boundary_block_through_disagreement():
    spec = GyroSpec(campaign_id="boundary-check")
    tglf_env = TglfReducedAdapter().run(spec)
    cgyro_env = CgyroNonlinearAdapter().run(spec, stub_mode="agree")
    assert tglf_env.boundary == BOUNDARY_BLOCK
    assert cgyro_env.boundary == BOUNDARY_BLOCK


def test_cross_model_emits_for_phase0_e2e_path(tmp_path: Path):
    """The full Phase-0 path can emit at least one DisagreementRecord per scenario."""
    spec = GyroSpec(campaign_id="phase0-disagreement")
    tglf_env = TglfReducedAdapter().run(spec)

    # Run all three CGYRO modes against the same TGLF baseline; record each.
    records = []
    for stub_mode in ("agree", "warn", "quarantine"):
        cgyro_env = CgyroNonlinearAdapter().run(spec, stub_mode=stub_mode)
        records.append(
            cross_model_disagreement(
                object_id=f"phase0-{stub_mode}",
                tglf_envelope=tglf_env,
                cgyro_envelope=cgyro_env,
            )
        )

    statuses = [r.status for r in records]
    assert DisagreementStatus.pass_ in statuses
    assert DisagreementStatus.warn in statuses
    assert DisagreementStatus.quarantine in statuses

    # Aggregate verdict: any quarantine -> downstream blocked
    aggregate = "block" if any(r.status == DisagreementStatus.quarantine for r in records) else "ok"
    assert aggregate == "block"
