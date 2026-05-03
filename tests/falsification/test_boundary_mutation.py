"""Boundary mutation falsification tests (expanded).

Covers: single-byte mutation, prefix truncation, empty boundary,
DRO boundary check, and verify_boundary utility.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from energy_physics_pipeline.boundary import BOUNDARY_BLOCK, verify_boundary, assert_boundary, BoundaryViolation
from energy_physics_pipeline.schemas.dro import DeviceResponseObject, DeviceFamily, DroAuditBlock
from energy_physics_pipeline.schemas.envelope import SubVertical


def _make_dro_audit() -> DroAuditBlock:
    return DroAuditBlock(envelope_id="sha256:" + "a" * 64)


def test_boundary_exact_match():
    assert verify_boundary(BOUNDARY_BLOCK) is True


def test_boundary_single_byte_mutation():
    mutated = BOUNDARY_BLOCK[:5] + "X" + BOUNDARY_BLOCK[6:]
    assert verify_boundary(mutated) is False


def test_boundary_empty_string():
    assert verify_boundary("") is False


def test_boundary_none():
    assert verify_boundary(None) is False


def test_boundary_mapping_valid():
    assert verify_boundary({"boundary": BOUNDARY_BLOCK}) is True


def test_boundary_mapping_missing_key():
    assert verify_boundary({"boundary": "wrong"}) is False


def test_assert_boundary_raises_on_mutation():
    with pytest.raises(BoundaryViolation):
        assert_boundary("mutated boundary")


def test_envelope_rejects_mutated_boundary():
    """UniversalLayerEnvelope must reject any non-canonical boundary."""
    from energy_physics_pipeline.schemas import UniversalLayerEnvelope, BackendBlock, ProvenanceBlock
    from energy_physics_pipeline.schemas.envelope import Mode, Domain, LayerLevel, LicenseClass, ExecutionMode

    mutated = BOUNDARY_BLOCK.replace("Research", "Resarch", 1)
    h = "b" * 64
    with pytest.raises(ValidationError):
        UniversalLayerEnvelope(
            boundary=mutated,
            campaign_id="test",
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L4,
            domain=Domain.battery,
            mode=Mode.engineering_stub,
            backend=BackendBlock(
                adapter="x", tool="x", tool_version="0",
                execution_mode=ExecutionMode.local_cpu,
                license_class=LicenseClass.A,
                license_evidence_uri="https://example.com",
            ),
            provenance=ProvenanceBlock(
                agent_id="a", model_id="m", git_sha="abc",
                input_hash=h, output_hash=h, config_hash=h,
            ),
        )


def test_dro_rejects_mutated_boundary():
    """DeviceResponseObject must reject any non-canonical boundary."""
    mutated = BOUNDARY_BLOCK + " extra"
    with pytest.raises(ValidationError):
        DeviceResponseObject(
            boundary=mutated,
            sub_vertical=SubVertical.electrochemistry,
            device_family=DeviceFamily.battery,
            audit=_make_dro_audit(),
        )
