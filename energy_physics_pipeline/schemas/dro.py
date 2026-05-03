"""DeviceResponseObject — unified L4 -> L5 handoff for both sub-verticals."""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from energy_physics_pipeline.boundary import BOUNDARY_BLOCK
from energy_physics_pipeline.schemas.canonical import content_id
from energy_physics_pipeline.schemas.envelope import SubVertical


class DeviceFamily(str, Enum):
    battery = "battery"
    pem_electrolyzer = "pem_electrolyzer"
    pem_fuel_cell = "pem_fuel_cell"
    sofc = "sofc"
    soec = "soec"
    photovoltaic = "photovoltaic"
    thermoelectric = "thermoelectric"
    tokamak = "tokamak"
    stellarator = "stellarator"
    spherical_tokamak = "spherical_tokamak"


class CurveType(str, Enum):
    V_vs_j = "V_vs_j"
    J_vs_V = "J_vs_V"
    voltage_time = "voltage_time"
    capacity_cycle = "capacity_cycle"
    impedance = "impedance"
    ZT_vs_T = "ZT_vs_T"
    power_deltaT = "power_deltaT"
    q_profile = "q_profile"
    pressure_profile = "pressure_profile"
    current_density_profile = "current_density_profile"
    confinement_time = "confinement_time"


class Axis(BaseModel):
    name: str
    unit: str
    values: list[float]

    model_config = ConfigDict(extra="forbid")


class CurveAxis(BaseModel):
    quantity: str
    unit: str
    values: list[float]

    model_config = ConfigDict(extra="forbid")


class CurveUncertainty(BaseModel):
    lower: list[float] = Field(default_factory=list)
    upper: list[float] = Field(default_factory=list)
    method: str = "none"

    model_config = ConfigDict(extra="forbid")


class Curve(BaseModel):
    curve_type: CurveType
    x: CurveAxis
    y: CurveAxis
    uncertainty: CurveUncertainty = Field(default_factory=CurveUncertainty)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _x_y_same_length(self) -> Self:
        if len(self.x.values) != len(self.y.values):
            raise ValueError("Curve x and y must have the same length")
        return self


class ScalarMetrics(BaseModel):
    ocv_V: Optional[float] = None
    overpotential_V_at_target_j: Optional[float] = None
    capacity_Ah: Optional[float] = None
    pce_fraction: Optional[float] = None
    fill_factor: Optional[float] = None
    zt: Optional[float] = None
    q95: Optional[float] = None
    beta_N: Optional[float] = None
    H98: Optional[float] = None
    neutron_wall_loading_MW_m2: Optional[float] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("pce_fraction", "fill_factor")
    @classmethod
    def _zero_one(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return None
        if not (0.0 <= v <= 1.0):
            raise ValueError("pce_fraction / fill_factor must be in [0, 1]")
        return v


class OperatingConditions(BaseModel):
    axes: list[Axis] = Field(default_factory=list)
    fixed: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class ResponseBlock(BaseModel):
    curves: list[Curve] = Field(default_factory=list)
    scalar_metrics: ScalarMetrics = Field(default_factory=ScalarMetrics)

    model_config = ConfigDict(extra="forbid")


class DegradationTrajectoryPoint(BaseModel):
    t_s: float
    state: dict[str, Any]
    uncertainty: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class DegradationOrStability(BaseModel):
    modes: list[str] = Field(default_factory=list)
    trajectory: list[DegradationTrajectoryPoint] = Field(default_factory=list)
    invalid_regions: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class HandoffBlock(BaseModel):
    l5_targets: list[str] = Field(default_factory=list)
    required_fields_satisfied: bool = False
    missing_fields: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class DroAuditBlock(BaseModel):
    envelope_id: str
    dro_source_layer_run_ids: list[UUID] = Field(default_factory=list)
    kg_nodes: list[str] = Field(default_factory=list)
    artifact_refs: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class DeviceResponseObject(BaseModel):
    """Unified L4->L5 token; handles all electrochem + fusion device families."""

    schema_version: str = "energy.dro.v0.1"
    dro_id: Optional[str] = None
    boundary: str = BOUNDARY_BLOCK
    sub_vertical: SubVertical
    device_family: DeviceFamily
    operating_conditions: OperatingConditions = Field(default_factory=OperatingConditions)
    response: ResponseBlock = Field(default_factory=ResponseBlock)
    degradation_or_stability: DegradationOrStability = Field(default_factory=DegradationOrStability)
    handoff: HandoffBlock = Field(default_factory=HandoffBlock)
    audit: DroAuditBlock

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    @field_validator("boundary")
    @classmethod
    def _boundary_byte_identical(cls, v: str) -> str:
        if v != BOUNDARY_BLOCK:
            raise ValueError("DRO boundary mutated")
        return v

    @model_validator(mode="after")
    def _device_subvertical_consistency(self) -> Self:
        ec = {
            DeviceFamily.battery,
            DeviceFamily.pem_electrolyzer,
            DeviceFamily.pem_fuel_cell,
            DeviceFamily.sofc,
            DeviceFamily.soec,
            DeviceFamily.photovoltaic,
            DeviceFamily.thermoelectric,
        }
        fu = {
            DeviceFamily.tokamak,
            DeviceFamily.stellarator,
            DeviceFamily.spherical_tokamak,
        }
        if self.sub_vertical == SubVertical.electrochemistry and self.device_family not in ec:
            raise ValueError("electrochemistry sub_vertical requires an electrochemistry device_family")
        if self.sub_vertical == SubVertical.fusion and self.device_family not in fu:
            raise ValueError("fusion sub_vertical requires a fusion device_family")
        return self

    def finalize(self) -> "DeviceResponseObject":
        payload = self.model_dump(mode="json", exclude={"dro_id"})
        return self.model_copy(update={"dro_id": content_id(payload)})
