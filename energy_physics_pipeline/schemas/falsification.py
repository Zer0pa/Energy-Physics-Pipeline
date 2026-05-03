"""Falsification schemas — CrossModelDisagreement and EarlyWarning (TDA)."""
from __future__ import annotations

from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DisagreementMetric(str, Enum):
    absolute = "absolute"
    relative = "relative"
    sigma_normalized = "sigma_normalized"
    distributional = "distributional"


class DisagreementStatus(str, Enum):
    pass_ = "pass"
    warn = "warn"
    fail = "fail"
    quarantine = "quarantine"


class CrossModelDisagreementRecord(BaseModel):
    record_id: str
    object_id: str
    quantity: str
    unit: str
    models_compared: list[str]
    values: list[float]
    uncertainties: list[float] = Field(default_factory=list)
    metric: DisagreementMetric
    pass_threshold: float
    warn_threshold: float
    fail_threshold: float
    status: DisagreementStatus
    resolution_action: str  # rerun | add_reference_model | block_handoff | escalate

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _at_least_two_models(self) -> Self:
        if len(self.models_compared) < 2:
            raise ValueError("CrossModelDisagreement requires >=2 models compared")
        if len(self.values) != len(self.models_compared):
            raise ValueError("values length must match models_compared length")
        if self.uncertainties and len(self.uncertainties) != len(self.models_compared):
            raise ValueError("uncertainties length must match models_compared length")
        if not (0 <= self.pass_threshold <= self.warn_threshold <= self.fail_threshold):
            raise ValueError("thresholds must satisfy 0 <= pass <= warn <= fail")
        return self


class WindowSpec(BaseModel):
    length_s: float
    stride_s: float
    embedding_dim: int = 1
    delay_s: float = 0.0

    model_config = ConfigDict(extra="forbid")


class EarlyWarningFeatures(BaseModel):
    persistence_entropy: float | None = None
    max_lifetime_h0: float | None = None
    max_lifetime_h1: float | None = None
    bottleneck_delta: float | None = None
    landscape_delta: float | None = None

    model_config = ConfigDict(extra="forbid")


class EarlyWarningStatus(str, Enum):
    normal = "normal"
    watch = "watch"
    warn = "warn"
    fail = "fail"


class EarlyWarningSignal(BaseModel):
    signal_id: str
    source_object_id: str
    domain: str  # battery | electrolyser | fuel_cell | sofc | pv | thermoelectric | fusion
    window_spec: WindowSpec
    features: EarlyWarningFeatures = Field(default_factory=EarlyWarningFeatures)
    warning_score: float = 0.0
    lead_time_estimate_s: float = 0.0
    false_positive_rate_estimate: float = 0.0
    status: EarlyWarningStatus = EarlyWarningStatus.normal

    model_config = ConfigDict(extra="forbid")
