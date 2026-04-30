"""Falsifier router — applies all configured falsifiers to an envelope.

A falsifier is a callable `(envelope) -> list[FailureRecord] | None`. It can:
  - return None or [] to pass
  - return non-empty list of FailureRecord -> envelope's gate_status drops to fail/quarantine
"""
from __future__ import annotations

from typing import Callable, Iterable

from energy_pipeline.schemas import (
    UniversalLayerEnvelope,
    GateStatus,
)
from energy_pipeline.schemas.envelope import FailureRecord, FalsificationBlock

Falsifier = Callable[[UniversalLayerEnvelope], list[FailureRecord] | None]


def _max_status(a: GateStatus, b: GateStatus) -> GateStatus:
    order = {GateStatus.pass_: 0, GateStatus.warn: 1, GateStatus.fail: 2, GateStatus.quarantine: 3}
    return max(a, b, key=lambda s: order[s])


def run(envelope: UniversalLayerEnvelope, falsifiers: Iterable[Falsifier]) -> UniversalLayerEnvelope:
    """Apply all falsifiers; mutate envelope.falsification accordingly. Returns the same object (re-validated)."""
    fail_records: list[FailureRecord] = []
    new_status = envelope.falsification.gate_status
    for f in falsifiers:
        try:
            r = f(envelope)
        except Exception as exc:  # falsifier failure itself is a quarantine signal
            fail_records.append(
                FailureRecord(
                    gate_id=getattr(f, "__name__", "anonymous"),
                    severity="critical",
                    message=f"falsifier raised: {exc!r}",
                    evidence_uri=None,
                )
            )
            new_status = _max_status(new_status, GateStatus.quarantine)
            continue
        if not r:
            continue
        for record in r:
            fail_records.append(record)
            sev = (record.severity or "fail").lower()
            if sev == "warn":
                new_status = _max_status(new_status, GateStatus.warn)
            elif sev == "critical":
                new_status = _max_status(new_status, GateStatus.quarantine)
            else:
                new_status = _max_status(new_status, GateStatus.fail)

    fb = envelope.falsification
    return envelope.model_copy(
        update={
            "falsification": FalsificationBlock(
                gate_status=new_status,
                scientific_valid=fb.scientific_valid and new_status == GateStatus.pass_,
                cross_model_disagreement=fb.cross_model_disagreement,
                unit_check_passed=fb.unit_check_passed,
                conservation_check_passed=fb.conservation_check_passed,
                boundary_check_passed=fb.boundary_check_passed,
                failures=[*fb.failures, *fail_records],
            )
        }
    )


# A small library of generic falsifiers used across both sub-verticals.

def boundary_falsifier(env: UniversalLayerEnvelope) -> list[FailureRecord] | None:
    from energy_pipeline.boundary import BOUNDARY_BLOCK
    if env.boundary != BOUNDARY_BLOCK:
        return [
            FailureRecord(
                gate_id="boundary_byte_identical",
                severity="critical",
                message="boundary block was mutated",
            )
        ]
    return None


def stub_scientific_valid_falsifier(env: UniversalLayerEnvelope) -> list[FailureRecord] | None:
    from energy_pipeline.schemas.envelope import ExecutionMode, Mode
    if env.mode == Mode.engineering_stub and env.falsification.scientific_valid:
        return [
            FailureRecord(
                gate_id="stub_scientific_valid_blocked",
                severity="fail",
                message="engineering_stub mode cannot set scientific_valid=True",
            )
        ]
    if env.backend.execution_mode == ExecutionMode.gpu_rest_stub and env.falsification.scientific_valid:
        return [
            FailureRecord(
                gate_id="gpu_rest_stub_scientific_valid_blocked",
                severity="fail",
                message="gpu_rest_stub backend cannot set scientific_valid=True",
            )
        ]
    return None


def units_required_falsifier(env: UniversalLayerEnvelope) -> list[FailureRecord] | None:
    out_payload = env.outputs.payload or {}
    quantities = out_payload.get("quantities") or {}
    if not isinstance(quantities, dict):
        return None
    missing = [k for k, v in quantities.items() if isinstance(v, dict) and "unit" not in v]
    if missing:
        return [
            FailureRecord(
                gate_id="units_required",
                severity="fail",
                message=f"quantities missing unit field: {missing}",
            )
        ]
    return None


def license_promotion_falsifier(env: UniversalLayerEnvelope) -> list[FailureRecord] | None:
    from energy_pipeline.schemas.envelope import LicenseClass, Mode
    if env.backend.license_class in (LicenseClass.C, LicenseClass.D, LicenseClass.E):
        if env.mode == Mode.scientific:
            uri = env.backend.license_evidence_uri or ""
            if not uri.startswith(("file://", "https://", "kg://license-grant/")):
                return [
                    FailureRecord(
                        gate_id="license_promotion_blocked",
                        severity="fail",
                        message=f"license_class={env.backend.license_class.value} cannot enter scientific mode without explicit license-grant evidence",
                    )
                ]
    return None
