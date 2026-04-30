"""ReasonerTuple — emitted from every meaningful run for self-bootstrapping reasoner curation."""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class OutcomeLabel(str, Enum):
    pass_ = "pass"
    fail = "fail"
    inconclusive = "inconclusive"
    superseded = "superseded"


class RightsLabel(str, Enum):
    public = "public"
    internal = "internal"
    customer_confidential = "customer_confidential"
    restricted = "restricted"


class ReasonerTuple(BaseModel):
    tuple_id: str
    problem_context: str
    input_spec_ref: str
    tool_plan: dict[str, Any]
    simulation_request_ref: str
    raw_result_ref: str
    reduced_observables_ref: str
    falsifier_results: list[str] = Field(default_factory=list)
    disagreement_records: list[str] = Field(default_factory=list)
    ground_truth_ref: Optional[str] = None
    outcome_label: OutcomeLabel
    rights_label: RightsLabel
    next_action: str

    model_config = ConfigDict(extra="forbid")
