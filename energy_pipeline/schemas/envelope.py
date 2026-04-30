"""UniversalLayerEnvelope — every adapter, stub, simulator, MCP tool emits this."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from energy_pipeline.boundary import BOUNDARY_BLOCK
from energy_pipeline.schemas.canonical import content_id, sha256_of


class SubVertical(str, Enum):
    electrochemistry = "electrochemistry"
    fusion = "fusion"


class LayerLevel(str, Enum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"
    L6 = "L6"


class Domain(str, Enum):
    battery = "battery"
    green_h2 = "green_h2"
    fuel_cell = "fuel_cell"
    sofc = "sofc"
    soec = "soec"
    pv = "pv"
    thermoelectric = "thermoelectric"
    fusion = "fusion"


class Mode(str, Enum):
    scientific = "scientific"
    engineering_stub = "engineering_stub"
    replay = "replay"
    validation = "validation"


class LicenseClass(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


class ExecutionMode(str, Enum):
    local_cpu = "local_cpu"
    isolated_cpu = "isolated_cpu"
    gpu_rest_stub = "gpu_rest_stub"
    runpod_rest = "runpod_rest"
    external_service = "external_service"


class GateStatus(str, Enum):
    pass_ = "pass"
    warn = "warn"
    fail = "fail"
    quarantine = "quarantine"


class UncertaintyDistribution(str, Enum):
    none = "none"
    normal = "normal"
    lognormal = "lognormal"
    empirical = "empirical"
    ensemble = "ensemble"
    posterior = "posterior"


class ArtifactRef(BaseModel):
    type: str
    uri: str
    sha256: str
    schema_version: str

    model_config = ConfigDict(extra="forbid")


class IOBlock(BaseModel):
    refs: list[ArtifactRef] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class UncertaintyBlock(BaseModel):
    distribution: UncertaintyDistribution = UncertaintyDistribution.none
    p05: dict[str, Any] = Field(default_factory=dict)
    p50: dict[str, Any] = Field(default_factory=dict)
    p95: dict[str, Any] = Field(default_factory=dict)
    contributors: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class FailureRecord(BaseModel):
    gate_id: str
    severity: str  # info|warn|fail|critical
    message: str
    evidence_uri: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class FalsificationBlock(BaseModel):
    gate_status: GateStatus = GateStatus.pass_
    scientific_valid: bool = False
    cross_model_disagreement: dict[str, Any] = Field(default_factory=dict)
    unit_check_passed: bool = False
    conservation_check_passed: bool = False
    boundary_check_passed: bool = False
    failures: list[FailureRecord] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class BackendBlock(BaseModel):
    adapter: str
    tool: str
    tool_version: str
    execution_mode: ExecutionMode
    license_class: LicenseClass
    license_evidence_uri: str

    model_config = ConfigDict(extra="forbid")


class ProvenanceBlock(BaseModel):
    agent_id: str
    model_id: str
    git_sha: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    input_hash: str
    output_hash: str
    config_hash: str
    artifact_hashes: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class UniversalLayerEnvelope(BaseModel):
    """The single object every layer emits and every layer accepts."""

    schema_version: str = "energy.envelope.v0.1"
    boundary: str = BOUNDARY_BLOCK
    envelope_id: Optional[str] = None  # populated post-init via finalize()
    campaign_id: str
    run_id: UUID = Field(default_factory=uuid4)
    sub_vertical: SubVertical
    layer: LayerLevel
    domain: Domain
    mode: Mode
    backend: BackendBlock
    inputs: IOBlock = Field(default_factory=IOBlock)
    outputs: IOBlock = Field(default_factory=IOBlock)
    uncertainty: UncertaintyBlock = Field(default_factory=UncertaintyBlock)
    falsification: FalsificationBlock = Field(default_factory=FalsificationBlock)
    provenance: ProvenanceBlock

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    @field_validator("boundary")
    @classmethod
    def _boundary_byte_identical(cls, v: str) -> str:
        if v != BOUNDARY_BLOCK:
            raise ValueError("boundary string mutated; boundary check failed")
        return v

    @model_validator(mode="after")
    def _stub_cannot_be_scientific_valid(self) -> Self:
        # Per PRD: stubs cannot set scientific_valid=true.
        if self.mode == Mode.engineering_stub and self.falsification.scientific_valid:
            raise ValueError(
                "engineering_stub may not be scientific_valid=true (PRD acceptance gate)"
            )
        if self.backend.execution_mode in (
            ExecutionMode.gpu_rest_stub,
        ) and self.falsification.scientific_valid:
            raise ValueError(
                "gpu_rest_stub backend cannot emit scientific_valid=true (PRD)"
            )
        return self

    @model_validator(mode="after")
    def _class_cde_promotion_gate(self) -> Self:
        # Class C/D/E backends cannot be promoted to product mode without explicit license grant.
        if self.backend.license_class in (LicenseClass.C, LicenseClass.D, LicenseClass.E):
            if self.mode == Mode.scientific and not self.backend.license_evidence_uri.startswith(
                ("file://", "https://", "kg://license-grant/")
            ):
                raise ValueError(
                    f"license_class={self.backend.license_class.value} requires license_evidence_uri "
                    "(file://, https://, or kg://license-grant/) before promotion to scientific mode"
                )
        return self

    def finalize(self) -> "UniversalLayerEnvelope":
        """Compute envelope_id from canonical JSON of *self minus envelope_id*."""
        # Dump excluding envelope_id, then content-id over the rest. UUID is normalised to str.
        payload = self.model_dump(mode="json", exclude={"envelope_id"})
        # Use only structural fields for hashing — exclude per-run ids that change naturally.
        # We DO include run_id so envelope_id is unique per run.
        eid = content_id(payload)
        return self.model_copy(update={"envelope_id": eid})

    def output_hash(self) -> str:
        """Sha256 of canonical-JSON payload of outputs only — stable across timestamps."""
        return sha256_of(self.outputs.model_dump(mode="json"))
