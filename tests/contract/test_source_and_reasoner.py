"""Contract tests for SourceManifest and ReasonerTuple shapes (schema-only)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from energy_pipeline.schemas import ReasonerTuple, SourceManifest
from energy_pipeline.schemas.reasoner import OutcomeLabel, RightsLabel
from energy_pipeline.schemas.source import AllowedUse, RetrievalMethod


def test_source_manifest_construct_ok():
    sm = SourceManifest(
        source_id="pybamm",
        uri="https://github.com/pybamm-team/PyBaMM/blob/develop/LICENSE.txt",
        retrieval_method=RetrievalMethod.manual,
        retrieved_at=datetime(2026, 4, 30, tzinfo=timezone.utc),
        license_spdx_or_text="BSD-3-Clause",
        allowed_use=AllowedUse.commercial,
        geography_restrictions=None,
        checksum="sha256:" + "0" * 64,
        local_slice_size_mb=0.0,
        bulk_data_stored=False,
        citation="PyBaMM Project",
        rights_notes="research and commercial",
    )
    assert sm.source_id == "pybamm"


def test_source_manifest_extra_fields_rejected():
    with pytest.raises(ValidationError):
        SourceManifest(
            source_id="x",
            uri="https://x",
            retrieval_method=RetrievalMethod.manual,
            retrieved_at=datetime.now(timezone.utc),
            license_spdx_or_text="MIT",
            allowed_use=AllowedUse.research,
            checksum="sha256:" + "0" * 64,
            citation="x",
            extra_field="boom",  # type: ignore[call-arg]
        )


def test_reasoner_tuple_construct_ok():
    t = ReasonerTuple(
        tuple_id="t1",
        problem_context="battery design",
        input_spec_ref="env://r1",
        tool_plan={"step1": "pybamm"},
        simulation_request_ref="env://r2",
        raw_result_ref="env://r3",
        reduced_observables_ref="env://r4",
        falsifier_results=["units_required:pass"],
        disagreement_records=[],
        ground_truth_ref=None,
        outcome_label=OutcomeLabel.pass_,
        rights_label=RightsLabel.public,
        next_action="record",
    )
    assert t.outcome_label == OutcomeLabel.pass_
