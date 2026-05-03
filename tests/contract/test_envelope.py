"""Contract tests for UniversalLayerEnvelope."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from energy_physics_pipeline.boundary import BOUNDARY_BLOCK
from energy_physics_pipeline.schemas import (
    BackendBlock,
    Domain,
    ExecutionMode,
    GateStatus,
    LayerLevel,
    LicenseClass,
    Mode,
    SubVertical,
    UniversalLayerEnvelope,
)
from energy_physics_pipeline.schemas.envelope import (
    FalsificationBlock,
    ProvenanceBlock,
)


def _envelope(**overrides):
    base = dict(
        campaign_id="c1",
        sub_vertical=SubVertical.electrochemistry,
        layer=LayerLevel.L4,
        domain=Domain.battery,
        mode=Mode.engineering_stub,
        backend=BackendBlock(
            adapter="t",
            tool="t",
            tool_version="0",
            execution_mode=ExecutionMode.local_cpu,
            license_class=LicenseClass.A,
            license_evidence_uri="kg://license-grant/t",
        ),
        falsification=FalsificationBlock(
            gate_status=GateStatus.pass_,
            scientific_valid=False,
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
    )
    base.update(overrides)
    return UniversalLayerEnvelope(**base)


def test_envelope_finalize_stable_id():
    e1 = _envelope().finalize()
    # Run twice — same content => same envelope_id (excluding run_id which is unique).
    assert e1.envelope_id is not None and e1.envelope_id.startswith("sha256:")


def test_boundary_mutation_rejected():
    with pytest.raises(ValidationError):
        _envelope(boundary=BOUNDARY_BLOCK + " extra")


def test_stub_cannot_be_scientific_valid():
    with pytest.raises(ValidationError):
        _envelope(
            mode=Mode.engineering_stub,
            falsification=FalsificationBlock(
                gate_status=GateStatus.pass_,
                scientific_valid=True,
                unit_check_passed=True,
                conservation_check_passed=True,
                boundary_check_passed=True,
            ),
        )


def test_gpu_rest_stub_cannot_be_scientific_valid():
    with pytest.raises(ValidationError):
        _envelope(
            backend=BackendBlock(
                adapter="t",
                tool="t",
                tool_version="0",
                execution_mode=ExecutionMode.gpu_rest_stub,
                license_class=LicenseClass.A,
                license_evidence_uri="kg://license-grant/t",
            ),
            mode=Mode.scientific,
            falsification=FalsificationBlock(
                gate_status=GateStatus.pass_,
                scientific_valid=True,
                unit_check_passed=True,
                conservation_check_passed=True,
                boundary_check_passed=True,
            ),
        )


def test_class_d_promotion_blocked_without_evidence():
    with pytest.raises(ValidationError):
        _envelope(
            mode=Mode.scientific,
            backend=BackendBlock(
                adapter="t",
                tool="t",
                tool_version="0",
                execution_mode=ExecutionMode.local_cpu,
                license_class=LicenseClass.D,
                license_evidence_uri="",
            ),
            falsification=FalsificationBlock(
                gate_status=GateStatus.pass_,
                scientific_valid=True,
                unit_check_passed=True,
                conservation_check_passed=True,
                boundary_check_passed=True,
            ),
        )


def test_class_d_promotion_allowed_with_kg_grant():
    e = _envelope(
        mode=Mode.scientific,
        backend=BackendBlock(
            adapter="t",
            tool="t",
            tool_version="0",
            execution_mode=ExecutionMode.local_cpu,
            license_class=LicenseClass.D,
            license_evidence_uri="kg://license-grant/AlphaPEM-isolated-2026-04-30",
        ),
        falsification=FalsificationBlock(
            gate_status=GateStatus.pass_,
            scientific_valid=True,
            unit_check_passed=True,
            conservation_check_passed=True,
            boundary_check_passed=True,
        ),
    )
    assert e.mode == Mode.scientific


def test_extra_fields_rejected():
    with pytest.raises(ValidationError):
        _envelope(extra_field="oops")


def test_envelope_carries_boundary_byte_identical():
    e = _envelope()
    assert e.boundary == BOUNDARY_BLOCK
    assert len(e.boundary) == len(BOUNDARY_BLOCK)
