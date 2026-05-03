"""L6 acceptance enforcement — make audit/KG and the production falsifier set MANDATORY.

Per CPU hardening brief §2 + §3:

  - "If `ENERGY_AUDIT_REQUIRED=true`, accepted outputs require an audit writer
    and KG store or use a configured default."
  - "Move COCOS/unit, negative temperature/density, above-Carnot, SoC range, PV
    fill-factor, IMAS DD-version, and cross-model disagreement threshold gates
    into production falsifier code."
  - "Apply the default falsifier set to all REST and adapter outputs before
    acceptance."

Use `accept_envelope(env, audit_writer=None, kg_store=None)` from every adapter's
`run()` end. The function:

  1. Runs the default production falsifier set.
  2. If `ENERGY_AUDIT_REQUIRED` is true, refuses to accept the envelope unless a
     writer + store are provided (or fetchable from `audit_kg_default`).
  3. Writes the envelope (and DRO if provided) to the audit + KG.
  4. Refuses to return an envelope whose final gate_status==fail in
     ENERGY_BOUNDARY_GATE=strict mode.
"""
from __future__ import annotations

import threading
from typing import Optional

from energy_physics_pipeline.audit import AuditWriter
from energy_physics_pipeline.kg import KGStore
from energy_physics_pipeline.l6.config import get_config
from energy_physics_pipeline.l6.production_falsifiers import (
    apply_default_falsifiers,
    apply_dro_falsifiers,
)
from energy_physics_pipeline.schemas import (
    DeviceResponseObject,
    GateStatus,
    UniversalLayerEnvelope,
)
from energy_physics_pipeline.schemas.envelope import FalsificationBlock


class EnvelopeRejected(Exception):
    """Raised when an envelope cannot be accepted under the current gate policy."""


# ---------------------------------------------------------------------------
# Default audit writer / KG store — process-global, thread-safe lazy singletons
# ---------------------------------------------------------------------------


_AUDIT_LOCK = threading.RLock()
_KG_LOCK = threading.RLock()
_DEFAULT_AUDIT: Optional[AuditWriter] = None
_DEFAULT_KG: Optional[KGStore] = None


def audit_kg_default() -> tuple[AuditWriter, KGStore]:
    """Return process-global default audit writer + KG store, lazily initialised."""
    global _DEFAULT_AUDIT, _DEFAULT_KG
    with _AUDIT_LOCK:
        if _DEFAULT_AUDIT is None:
            _DEFAULT_AUDIT = AuditWriter()
    with _KG_LOCK:
        if _DEFAULT_KG is None:
            _DEFAULT_KG = KGStore()
    return _DEFAULT_AUDIT, _DEFAULT_KG


def reset_default_audit_kg(audit: Optional[AuditWriter] = None, kg: Optional[KGStore] = None) -> None:
    """Test-only: replace the process defaults (e.g. with tmp_path-backed instances)."""
    global _DEFAULT_AUDIT, _DEFAULT_KG
    with _AUDIT_LOCK:
        _DEFAULT_AUDIT = audit
    with _KG_LOCK:
        _DEFAULT_KG = kg


# ---------------------------------------------------------------------------
# accept_envelope — the production gate
# ---------------------------------------------------------------------------


def accept_envelope(
    envelope: UniversalLayerEnvelope,
    *,
    audit_writer: Optional[AuditWriter] = None,
    kg_store: Optional[KGStore] = None,
    write_audit: bool = True,
    write_kg: bool = True,
) -> UniversalLayerEnvelope:
    """Run production falsifiers, write audit + KG, return the gated envelope.

    Behaviour:
      - Always runs `apply_default_falsifiers(envelope)`.
      - If `ENERGY_AUDIT_REQUIRED` is true, requires either passed-in writer/store
        or process defaults (`audit_kg_default()`). Refuses with EnvelopeRejected
        when `write_audit`/`write_kg` are True but no writer/store available.
      - In `ENERGY_BOUNDARY_GATE=strict` mode, raises EnvelopeRejected if the
        final gate_status is `fail` or `quarantine`.
      - Returns the gated envelope.
    """
    cfg = get_config()
    gated = apply_default_falsifiers(envelope)

    audit_required = cfg.audit_required

    if audit_required and (write_audit or write_kg):
        if audit_writer is None or kg_store is None:
            try:
                default_audit, default_kg = audit_kg_default()
            except Exception as e:  # noqa: BLE001
                raise EnvelopeRejected(
                    f"audit-required mode but no audit/KG writer available: {e!r}"
                ) from e
            audit_writer = audit_writer or default_audit
            kg_store = kg_store or default_kg

    if write_audit and audit_writer is not None:
        audit_writer.write_event(
            kind=gated.schema_version,
            payload=gated.model_dump(mode="json"),
        )

    if write_kg and kg_store is not None:
        # Register the tool adapter as a metadata node and the simulation run as
        # a boundary-bearing artifact node + USED_TOOL edge.
        tool_id = f"tool::{gated.backend.adapter}"
        try:
            kg_store.add_node(
                "ToolAdapter",
                tool_id,
                {
                    "tool": gated.backend.tool,
                    "version": gated.backend.tool_version,
                    "license_class": gated.backend.license_class.value,
                },
                boundary_required=False,
            )
        except ValueError:
            # already exists (duplicate id) — fine
            pass
        sim_id = gated.envelope_id or f"run::{gated.run_id}"
        kg_store.add_node(
            "SimulationRun",
            sim_id,
            gated.model_dump(mode="json"),
            boundary_required=True,
        )
        kg_store.add_edge("USED_TOOL", sim_id, tool_id)

    if cfg.boundary_gate == "strict" and gated.falsification.gate_status in (
        GateStatus.fail,
        GateStatus.quarantine,
    ):
        raise EnvelopeRejected(
            f"strict gate refused envelope {gated.envelope_id}: "
            f"gate_status={gated.falsification.gate_status.value}; "
            f"failures={[f.gate_id for f in gated.falsification.failures]}"
        )

    return gated


def accept_envelope_and_dro(
    envelope: UniversalLayerEnvelope,
    dro: DeviceResponseObject,
    *,
    audit_writer: Optional[AuditWriter] = None,
    kg_store: Optional[KGStore] = None,
    write_audit: bool = True,
    write_kg: bool = True,
) -> tuple[UniversalLayerEnvelope, DeviceResponseObject]:
    """Like `accept_envelope`, but also runs DRO-side falsifiers (COCOS, etc.) and
    attaches their failures to the envelope before final gating.
    """
    dro_failures = apply_dro_falsifiers(dro)
    if dro_failures:
        merged = FalsificationBlock(
            gate_status=envelope.falsification.gate_status,
            scientific_valid=envelope.falsification.scientific_valid,
            cross_model_disagreement=envelope.falsification.cross_model_disagreement,
            unit_check_passed=envelope.falsification.unit_check_passed,
            conservation_check_passed=envelope.falsification.conservation_check_passed,
            boundary_check_passed=envelope.falsification.boundary_check_passed,
            failures=[*envelope.falsification.failures, *dro_failures],
        )
        envelope = envelope.model_copy(update={"falsification": merged})

    gated = accept_envelope(
        envelope,
        audit_writer=audit_writer,
        kg_store=kg_store,
        write_audit=write_audit,
        write_kg=write_kg,
    )

    # Write DRO node + PRODUCED edge if KG is available
    if write_kg:
        cfg = get_config()
        store = kg_store
        if store is None and cfg.audit_required:
            _, store = audit_kg_default()
        if store is not None:
            sim_id = gated.envelope_id or f"run::{gated.run_id}"
            dro_id = dro.dro_id or f"dro::{gated.run_id}"
            store.add_node(
                "DeviceResponseObject",
                dro_id,
                dro.model_dump(mode="json"),
                boundary_required=True,
            )
            store.add_edge("PRODUCED", sim_id, dro_id)

    return gated, dro
