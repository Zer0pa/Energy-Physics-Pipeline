"""Unit omission falsification tests.

Verifies that output payloads without 'unit' on quantity dicts
are caught by units_required_falsifier.
"""
from __future__ import annotations


from energy_pipeline.schemas import (
    UniversalLayerEnvelope,
    BackendBlock,
    ProvenanceBlock,
    IOBlock,
    GateStatus,
    LicenseClass,
    ExecutionMode,
    Mode,
    LayerLevel,
    SubVertical,
    Domain,
)
from energy_pipeline.l6.router import run as router_run, units_required_falsifier


def _prov() -> ProvenanceBlock:
    h = "d" * 64
    return ProvenanceBlock(
        agent_id="a", model_id="m", git_sha="abc",
        input_hash=h, output_hash=h, config_hash=h,
    )


def _env(quantities: dict) -> UniversalLayerEnvelope:
    return UniversalLayerEnvelope(
        campaign_id="test",
        sub_vertical=SubVertical.electrochemistry,
        layer=LayerLevel.L4,
        domain=Domain.battery,
        mode=Mode.engineering_stub,
        backend=BackendBlock(
            adapter="test", tool="test", tool_version="0",
            execution_mode=ExecutionMode.local_cpu,
            license_class=LicenseClass.A,
            license_evidence_uri="",
        ),
        outputs=IOBlock(payload={"quantities": quantities}),
        provenance=_prov(),
    )


def test_missing_unit_fails():
    """Single quantity without unit → gate_status=fail."""
    result = router_run(_env({"voltage": {"value": 3.7}}), [units_required_falsifier])
    assert result.falsification.gate_status == GateStatus.fail
    assert any(f.gate_id == "units_required" for f in result.falsification.failures)
    assert any("voltage" in f.message for f in result.falsification.failures)


def test_multiple_missing_units():
    """Multiple quantities without unit → all flagged."""
    result = router_run(
        _env({"voltage": {"value": 3.7}, "current": {"value": 1.2}}),
        [units_required_falsifier],
    )
    assert result.falsification.gate_status == GateStatus.fail
    assert len(result.falsification.failures) >= 1
    msg = result.falsification.failures[0].message
    assert "voltage" in msg or "current" in msg


def test_quantity_with_unit_passes():
    """Quantities with unit field → gate_status=pass."""
    result = router_run(
        _env({"voltage": {"value": 3.7, "unit": "V"}}),
        [units_required_falsifier],
    )
    assert result.falsification.gate_status == GateStatus.pass_
    assert result.falsification.failures == []


def test_empty_quantities_passes():
    """Empty quantities dict → no failure."""
    result = router_run(_env({}), [units_required_falsifier])
    assert result.falsification.gate_status == GateStatus.pass_


def test_no_quantities_key_passes():
    """Payload without 'quantities' key → no failure."""
    env = UniversalLayerEnvelope(
        campaign_id="test",
        sub_vertical=SubVertical.electrochemistry,
        layer=LayerLevel.L4,
        domain=Domain.battery,
        mode=Mode.engineering_stub,
        backend=BackendBlock(
            adapter="test", tool="test", tool_version="0",
            execution_mode=ExecutionMode.local_cpu,
            license_class=LicenseClass.A,
            license_evidence_uri="",
        ),
        outputs=IOBlock(payload={"scalar": 42.0}),
        provenance=_prov(),
    )
    result = router_run(env, [units_required_falsifier])
    assert result.falsification.gate_status == GateStatus.pass_
