"""Plug-replaceability test: gpu_rest_stub <-> local_cpu must preserve schema/contract.

Per PRD: Runpod cutover is accepted only when changing a config flag from `gpu_rest_stub`
to `runpod_rest` preserves golden fixture behaviour except for runtime/provenance fields.

We can't test runpod_rest live, but we can test the invariant: two envelopes with the
same output payload but different execution_mode/adapter must produce the same
output_hash. Differences allowed: provenance.created_at, run_id, envelope_id (because
envelope_id depends on those), backend.adapter, backend.tool_version,
backend.execution_mode, backend.license_evidence_uri.
"""
from __future__ import annotations

from energy_pipeline.schemas import (
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
from energy_pipeline.schemas.envelope import (
    FalsificationBlock,
    IOBlock,
    ProvenanceBlock,
)


def _envelope(execution_mode: ExecutionMode, adapter: str, license_class: LicenseClass = LicenseClass.A):
    return UniversalLayerEnvelope(
        campaign_id="c",
        sub_vertical=SubVertical.fusion,
        layer=LayerLevel.L4,
        domain=Domain.fusion,
        mode=Mode.engineering_stub,
        backend=BackendBlock(
            adapter=adapter,
            tool="ImasPython",
            tool_version="5.6.0",
            execution_mode=execution_mode,
            license_class=license_class,
            license_evidence_uri="kg://license-grant/imas-core",
        ),
        outputs=IOBlock(
            payload={
                "ids_paths_used": ["equilibrium", "core_profiles"],
                "quantities": {
                    "q95": {"value": 3.6, "unit": "1"},
                    "beta_N": {"value": 1.7, "unit": "1"},
                    "H98": {"value": 1.0, "unit": "1"},
                },
            }
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
    ).finalize()


def test_output_hash_preserved_across_backend_swap():
    """gpu_rest_stub vs local_cpu — same outputs → same output_hash."""
    e_stub = _envelope(execution_mode=ExecutionMode.gpu_rest_stub, adapter="rest-stub::imas")
    e_real = _envelope(execution_mode=ExecutionMode.local_cpu, adapter="local::imas")
    # output_hash() ignores everything except .outputs
    assert e_stub.output_hash() == e_real.output_hash()


def test_envelope_id_differs_across_backend_swap():
    """envelope_id includes backend metadata, so it must differ — that's the design."""
    e_stub = _envelope(execution_mode=ExecutionMode.gpu_rest_stub, adapter="rest-stub::imas")
    e_real = _envelope(execution_mode=ExecutionMode.local_cpu, adapter="local::imas")
    assert e_stub.envelope_id != e_real.envelope_id


def test_schema_version_invariant():
    e_stub = _envelope(execution_mode=ExecutionMode.gpu_rest_stub, adapter="rest-stub::imas")
    e_real = _envelope(execution_mode=ExecutionMode.local_cpu, adapter="local::imas")
    assert e_stub.schema_version == e_real.schema_version


def test_boundary_invariant_across_backend_swap():
    e_stub = _envelope(execution_mode=ExecutionMode.gpu_rest_stub, adapter="rest-stub::imas")
    e_real = _envelope(execution_mode=ExecutionMode.local_cpu, adapter="local::imas")
    assert e_stub.boundary == e_real.boundary
