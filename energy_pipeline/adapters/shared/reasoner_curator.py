"""Reasoner curator — build ReasonerTuple from a run envelope and write to KG.

Public API::

    build_tuple_from_run(envelope, dro, falsifier_results, disagreements,
                         ground_truth_ref=None) -> ReasonerTuple

    write_to_kg(tuple_obj, kg) -> str   # returns KG node sha256

The ``tuple_id`` is derived deterministically from the content hash of the
tuple's core fields so the same run always produces the same tuple_id.
"""
from __future__ import annotations

import hashlib
from typing import Any

import orjson

from energy_pipeline.schemas.reasoner import OutcomeLabel, ReasonerTuple, RightsLabel
from energy_pipeline.schemas.envelope import UniversalLayerEnvelope, Mode
from energy_pipeline.schemas.dro import DeviceResponseObject


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _content_hash(obj: Any) -> str:
    """Deterministic sha256 hex of *obj* serialised as sorted-key canonical JSON."""
    raw = orjson.dumps(obj, option=orjson.OPT_SORT_KEYS | orjson.OPT_NON_STR_KEYS)
    return hashlib.sha256(raw).hexdigest()


def _derive_outcome(
    envelope: UniversalLayerEnvelope,
    falsifier_results: list[str],
) -> OutcomeLabel:
    """Derive an outcome label from envelope falsification state."""
    fb = envelope.falsification
    if fb.scientific_valid and not falsifier_results:
        return OutcomeLabel.pass_
    if not fb.scientific_valid and falsifier_results:
        return OutcomeLabel.fail
    # Mixed or inconclusive
    return OutcomeLabel.inconclusive


def _derive_rights(envelope: UniversalLayerEnvelope) -> RightsLabel:
    """Map envelope mode to a rights label."""
    if envelope.mode == Mode.scientific:
        return RightsLabel.internal
    return RightsLabel.internal  # default to internal; override via post-processing


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_tuple_from_run(
    envelope: UniversalLayerEnvelope,
    dro: DeviceResponseObject,
    falsifier_results: list[str],
    disagreements: list[str],
    ground_truth_ref: str | None = None,
) -> ReasonerTuple:
    """Build a :class:`~energy_pipeline.schemas.reasoner.ReasonerTuple` from a pipeline run.

    The ``tuple_id`` is derived deterministically from the content hash of the
    structural fields (envelope_id, dro_id, falsifier_results, disagreements,
    ground_truth_ref) so the same run always yields the same ``tuple_id``.

    Args:
        envelope: The finalized :class:`UniversalLayerEnvelope` from the run.
        dro: The finalized :class:`DeviceResponseObject` from the run.
        falsifier_results: List of falsifier gate IDs / evidence strings that fired.
        disagreements: List of cross-model disagreement record IDs.
        ground_truth_ref: Optional URI to ground-truth observation.

    Returns:
        A validated :class:`ReasonerTuple`.
    """
    envelope_id = envelope.envelope_id or "unfinalized-envelope"
    dro_id = dro.dro_id or "unfinalized-dro"

    # Deterministic content hash for tuple_id
    hash_payload = {
        "envelope_id": envelope_id,
        "dro_id": dro_id,
        "falsifier_results": sorted(falsifier_results),
        "disagreements": sorted(disagreements),
        "ground_truth_ref": ground_truth_ref,
    }
    tuple_id = f"sha256:{_content_hash(hash_payload)}"

    outcome = _derive_outcome(envelope, falsifier_results)
    rights = _derive_rights(envelope)

    next_action: str
    if outcome == OutcomeLabel.pass_:
        next_action = "promote-to-l5"
    elif outcome == OutcomeLabel.fail:
        next_action = "quarantine-and-review"
    else:
        next_action = "review-inconclusive"

    return ReasonerTuple(
        tuple_id=tuple_id,
        problem_context=(
            f"sub_vertical={envelope.sub_vertical.value} "
            f"domain={envelope.domain.value} "
            f"layer={envelope.layer.value} "
            f"mode={envelope.mode.value}"
        ),
        input_spec_ref=envelope_id,
        tool_plan={
            "adapter": envelope.backend.adapter,
            "tool": envelope.backend.tool,
            "tool_version": envelope.backend.tool_version,
            "execution_mode": envelope.backend.execution_mode.value,
            "license_class": envelope.backend.license_class.value,
        },
        simulation_request_ref=str(envelope.run_id),
        raw_result_ref=dro_id,
        reduced_observables_ref=dro_id,
        falsifier_results=list(falsifier_results),
        disagreement_records=list(disagreements),
        ground_truth_ref=ground_truth_ref,
        outcome_label=outcome,
        rights_label=rights,
        next_action=next_action,
    )


def write_to_kg(tuple_obj: ReasonerTuple, kg: Any) -> str:
    """Write *tuple_obj* to *kg* as a ReasonerTuple node with DERIVED_FROM edges.

    Creates:
    - A ``ReasonerTuple`` node in the KG for the tuple itself.
    - A ``DERIVED_FROM`` edge from the tuple node to the ``input_spec_ref``
      (envelope node ID).
    - A ``DERIVED_FROM`` edge from the tuple node to the ``raw_result_ref``
      (DRO node ID).

    Args:
        tuple_obj: A validated :class:`ReasonerTuple`.
        kg: A :class:`~energy_pipeline.kg.graph.KGStore` instance.

    Returns:
        The sha256 of the newly written KG node record.
    """
    attrs = tuple_obj.model_dump(mode="json")

    sha = kg.add_node(
        "ReasonerTuple",
        tuple_obj.tuple_id,
        attrs,
        boundary_required=False,
    )

    # DERIVED_FROM → envelope
    kg.add_edge(
        "DERIVED_FROM",
        tuple_obj.tuple_id,
        tuple_obj.input_spec_ref,
        attrs={"role": "envelope"},
    )

    # DERIVED_FROM → DRO
    if tuple_obj.raw_result_ref != tuple_obj.input_spec_ref:
        kg.add_edge(
            "DERIVED_FROM",
            tuple_obj.tuple_id,
            tuple_obj.raw_result_ref,
            attrs={"role": "dro"},
        )

    return sha
