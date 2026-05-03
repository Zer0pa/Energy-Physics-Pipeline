"""Cross-model disagreement falsification tests.

Verifies CrossModelDisagreementRecord schema validation and
router-level blocking when status='fail'.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from energy_physics_pipeline.schemas.falsification import (
    CrossModelDisagreementRecord,
    DisagreementMetric,
    DisagreementStatus,
)
from energy_physics_pipeline.schemas import (
    UniversalLayerEnvelope,
    BackendBlock,
    FalsificationBlock,
    ProvenanceBlock,
    GateStatus,
    LicenseClass,
    ExecutionMode,
    Mode,
    LayerLevel,
    SubVertical,
    Domain,
)
from energy_physics_pipeline.l6.router import run as router_run
from energy_physics_pipeline.schemas.envelope import FailureRecord


def _cmd(status: DisagreementStatus = DisagreementStatus.fail) -> CrossModelDisagreementRecord:
    return CrossModelDisagreementRecord(
        record_id="rec-001",
        object_id="obj-001",
        quantity="capacity_Ah",
        unit="Ah",
        models_compared=["model-A", "model-B"],
        values=[1.0, 2.0],
        metric=DisagreementMetric.relative,
        pass_threshold=0.05,
        warn_threshold=0.20,
        fail_threshold=0.50,
        status=status,
        resolution_action="block_handoff",
    )


def test_cmd_requires_two_models():
    with pytest.raises(ValidationError, match=">=2 models"):
        CrossModelDisagreementRecord(
            record_id="r", object_id="o", quantity="q", unit="u",
            models_compared=["single"],
            values=[1.0],
            metric=DisagreementMetric.absolute,
            pass_threshold=0.1, warn_threshold=0.2, fail_threshold=0.3,
            status=DisagreementStatus.pass_,
            resolution_action="rerun",
        )


def test_cmd_values_length_mismatch():
    with pytest.raises(ValidationError, match="values length"):
        CrossModelDisagreementRecord(
            record_id="r", object_id="o", quantity="q", unit="u",
            models_compared=["A", "B"],
            values=[1.0],  # only 1 value for 2 models
            metric=DisagreementMetric.absolute,
            pass_threshold=0.1, warn_threshold=0.2, fail_threshold=0.3,
            status=DisagreementStatus.fail,
            resolution_action="rerun",
        )


def test_cmd_threshold_ordering():
    with pytest.raises(ValidationError, match="thresholds"):
        CrossModelDisagreementRecord(
            record_id="r", object_id="o", quantity="q", unit="u",
            models_compared=["A", "B"],
            values=[1.0, 2.0],
            metric=DisagreementMetric.absolute,
            pass_threshold=0.5, warn_threshold=0.2, fail_threshold=0.3,  # wrong order
            status=DisagreementStatus.fail,
            resolution_action="rerun",
        )


def _prov() -> ProvenanceBlock:
    h = "e" * 64
    return ProvenanceBlock(
        agent_id="a", model_id="m", git_sha="abc",
        input_hash=h, output_hash=h, config_hash=h,
    )


def _cross_model_disagreement_falsifier(env: UniversalLayerEnvelope) -> list[FailureRecord] | None:
    cmd = env.falsification.cross_model_disagreement
    if not cmd:
        return None
    if cmd.get("status") == "fail":
        return [
            FailureRecord(
                gate_id="cross_model_disagreement_fail",
                severity="fail",
                message="cross_model_disagreement.status=fail — blocking downstream",
            )
        ]
    return None


def test_fail_status_blocks_envelope():
    env = UniversalLayerEnvelope(
        campaign_id="test",
        sub_vertical=SubVertical.electrochemistry,
        layer=LayerLevel.L4,
        domain=Domain.battery,
        mode=Mode.engineering_stub,
        backend=BackendBlock(
            adapter="t", tool="t", tool_version="0",
            execution_mode=ExecutionMode.local_cpu,
            license_class=LicenseClass.A,
            license_evidence_uri="",
        ),
        falsification=FalsificationBlock(
            cross_model_disagreement=_cmd(DisagreementStatus.fail).model_dump(mode="json")
        ),
        provenance=_prov(),
    )
    result = router_run(env, [_cross_model_disagreement_falsifier])
    assert result.falsification.gate_status == GateStatus.fail
    assert any(f.gate_id == "cross_model_disagreement_fail" for f in result.falsification.failures)


def test_pass_status_does_not_block():
    env = UniversalLayerEnvelope(
        campaign_id="test",
        sub_vertical=SubVertical.electrochemistry,
        layer=LayerLevel.L4,
        domain=Domain.battery,
        mode=Mode.engineering_stub,
        backend=BackendBlock(
            adapter="t", tool="t", tool_version="0",
            execution_mode=ExecutionMode.local_cpu,
            license_class=LicenseClass.A,
            license_evidence_uri="",
        ),
        falsification=FalsificationBlock(
            cross_model_disagreement=_cmd(DisagreementStatus.pass_).model_dump(mode="json")
        ),
        provenance=_prov(),
    )
    result = router_run(env, [_cross_model_disagreement_falsifier])
    assert result.falsification.gate_status == GateStatus.pass_
