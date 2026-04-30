"""Adapter registry — every simulator, MCP server, model, dataset has a record here.

Selecting a backend at runtime resolves through the registry + EnergyConfig flags.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from energy_pipeline.schemas.envelope import (
    LayerLevel,
    LicenseClass,
    SubVertical,
    Domain,
)


class AdapterCapability(str, Enum):
    cpu_real = "cpu_real"
    cpu_fixture = "cpu_fixture"
    gpu_rest_stub = "gpu_rest_stub"
    runpod_rest = "runpod_rest"
    parser_only = "parser_only"
    manifest_only = "manifest_only"


@dataclass(frozen=True)
class AdapterRecord:
    adapter_id: str
    tool: str
    tool_version: str
    sub_vertical: SubVertical
    layer: LayerLevel
    domains: tuple[Domain, ...]
    capabilities: tuple[AdapterCapability, ...]
    license_class: LicenseClass
    license_evidence_uri: str
    notes: str = ""


class AdapterRegistry:
    def __init__(self) -> None:
        self._by_id: dict[str, AdapterRecord] = {}

    def register(self, record: AdapterRecord) -> None:
        if record.adapter_id in self._by_id:
            raise ValueError(f"duplicate adapter_id: {record.adapter_id}")
        self._by_id[record.adapter_id] = record

    def get(self, adapter_id: str) -> AdapterRecord:
        return self._by_id[adapter_id]

    def find(
        self,
        *,
        sub_vertical: Optional[SubVertical] = None,
        layer: Optional[LayerLevel] = None,
        domain: Optional[Domain] = None,
    ) -> list[AdapterRecord]:
        out = []
        for r in self._by_id.values():
            if sub_vertical and r.sub_vertical != sub_vertical:
                continue
            if layer and r.layer != layer:
                continue
            if domain and domain not in r.domains:
                continue
            out.append(r)
        return out

    def all(self) -> list[AdapterRecord]:
        return list(self._by_id.values())


def default_registry() -> AdapterRegistry:
    """Bootstrap the registry with the seed adapters per PRD."""
    reg = AdapterRegistry()
    seeds: list[AdapterRecord] = [
        AdapterRecord(
            adapter_id="pyscf_l1",
            tool="PySCF",
            tool_version="2.8",
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L1,
            domains=(Domain.battery, Domain.green_h2, Domain.fuel_cell),
            capabilities=(AdapterCapability.cpu_real, AdapterCapability.cpu_fixture),
            license_class=LicenseClass.A,
            license_evidence_uri="https://github.com/pyscf/pyscf/blob/master/LICENSE",
            notes="Marcus parameter / CDFT smoke; molecule scale only",
        ),
        AdapterRecord(
            adapter_id="mace_l2_manifest",
            tool="MACE-OMol25",
            tool_version="manifest-only-v1",
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L2,
            domains=(Domain.battery, Domain.green_h2, Domain.fuel_cell),
            capabilities=(AdapterCapability.manifest_only, AdapterCapability.gpu_rest_stub),
            license_class=LicenseClass.A,
            license_evidence_uri="https://github.com/ACEsuit/mace/blob/main/LICENSE",
            notes="Code MIT; OMol25 weights need separate license manifest before activation.",
        ),
        AdapterRecord(
            adapter_id="esen_oc25_gated",
            tool="eSEN-M (fairchem)",
            tool_version="fairchem-2025",
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L2,
            domains=(Domain.green_h2, Domain.fuel_cell),
            capabilities=(AdapterCapability.manifest_only, AdapterCapability.gpu_rest_stub),
            license_class=LicenseClass.A,
            license_evidence_uri="https://github.com/facebookresearch/fairchem/blob/main/LICENSE.md",
            notes="ZA acceptance must be verified; gated until license-grant KG node lands.",
        ),
        AdapterRecord(
            adapter_id="moose_raccoon_l3",
            tool="MOOSE+RACCOON",
            tool_version="2025.1",
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L3,
            domains=(Domain.battery,),
            capabilities=(AdapterCapability.parser_only, AdapterCapability.cpu_fixture),
            license_class=LicenseClass.B,
            license_evidence_uri="https://github.com/idaholab/moose/blob/master/LICENSE",
            notes="LGPL — keep dynamic linkage; production runs HPC-parked.",
        ),
        AdapterRecord(
            adapter_id="pybamm_l4",
            tool="PyBaMM",
            tool_version="23.5+",
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L4,
            domains=(Domain.battery,),
            capabilities=(AdapterCapability.cpu_real,),
            license_class=LicenseClass.A,
            license_evidence_uri="https://github.com/pybamm-team/PyBaMM/blob/develop/LICENSE.txt",
            notes="BSD-3; happy path P2D; emits DRO with curve V_vs_j or voltage_time.",
        ),
        AdapterRecord(
            adapter_id="solcore_l4",
            tool="Solcore",
            tool_version="6.x",
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L4,
            domains=(Domain.pv,),
            capabilities=(AdapterCapability.cpu_real, AdapterCapability.cpu_fixture),
            license_class=LicenseClass.B,
            license_evidence_uri="https://github.com/qpv-research-group/solcore5/blob/develop/LICENSE.txt",
            notes="LGPL-3 — replacement for SCAPS-1D.",
        ),
        AdapterRecord(
            adapter_id="cantera_l4",
            tool="Cantera",
            tool_version="3.2",
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L4,
            domains=(Domain.sofc, Domain.soec),
            capabilities=(AdapterCapability.cpu_real, AdapterCapability.cpu_fixture),
            license_class=LicenseClass.A,
            license_evidence_uri="https://github.com/Cantera/cantera/blob/main/License.txt",
            notes="BSD-3; elementary kinetics for SOFC/SOEC.",
        ),
        AdapterRecord(
            adapter_id="alphapem_l4_isolated",
            tool="AlphaPEM",
            tool_version="2024.07",
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L4,
            domains=(Domain.fuel_cell, Domain.green_h2),
            capabilities=(AdapterCapability.parser_only,),
            license_class=LicenseClass.B,
            license_evidence_uri="https://github.com/gassraphael/AlphaPEM",
            notes="GPL-3 — isolate behind subprocess boundary; replace with permissive PEM fixture for product path.",
        ),
        AdapterRecord(
            adapter_id="pypsa_l5",
            tool="PyPSA",
            tool_version="0.31",
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L5,
            domains=(Domain.battery, Domain.green_h2, Domain.pv),
            capabilities=(AdapterCapability.cpu_real,),
            license_class=LicenseClass.A,
            license_evidence_uri="https://github.com/PyPSA/PyPSA/blob/master/LICENSE",
            notes="MIT; sector-coupled.",
        ),
        AdapterRecord(
            adapter_id="pvlib_l5",
            tool="pvlib-python",
            tool_version="0.10+",
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L5,
            domains=(Domain.pv,),
            capabilities=(AdapterCapability.cpu_real,),
            license_class=LicenseClass.A,
            license_evidence_uri="https://github.com/pvlib/pvlib-python/blob/main/LICENSE",
            notes="BSD-3.",
        ),
        AdapterRecord(
            adapter_id="pysam_l5",
            tool="NREL SAM (pySAM)",
            tool_version="2024",
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L5,
            domains=(Domain.pv, Domain.green_h2),
            capabilities=(AdapterCapability.cpu_real,),
            license_class=LicenseClass.A,
            license_evidence_uri="https://github.com/NREL/pysam/blob/main/LICENSE",
            notes="BSD-3; LCOE/LCOH P5/P50/P95.",
        ),
        # Fusion
        AdapterRecord(
            adapter_id="openmc_l1",
            tool="OpenMC",
            tool_version="0.15.3",
            sub_vertical=SubVertical.fusion,
            layer=LayerLevel.L1,
            domains=(Domain.fusion,),
            capabilities=(AdapterCapability.cpu_real, AdapterCapability.cpu_fixture),
            license_class=LicenseClass.A,
            license_evidence_uri="https://github.com/openmc-dev/openmc/blob/develop/LICENSE",
            notes="MIT; tiny fixed-source transport CPU fixture; bulk libraries manifest-only.",
        ),
        AdapterRecord(
            adapter_id="gacode_cgyro_l2",
            tool="GACODE / CGYRO",
            tool_version="2025",
            sub_vertical=SubVertical.fusion,
            layer=LayerLevel.L2,
            domains=(Domain.fusion,),
            capabilities=(AdapterCapability.parser_only, AdapterCapability.gpu_rest_stub),
            license_class=LicenseClass.A,
            license_evidence_uri="https://github.com/gafusion/gacode/blob/master/LICENSE",
            notes="Apache-2.0; nonlinear runs Runpod-parked; TGLF reduced lane CPU-feasible.",
        ),
        AdapterRecord(
            adapter_id="gyroswin_l2_surrogate",
            tool="GyroSwin",
            tool_version="2025",
            sub_vertical=SubVertical.fusion,
            layer=LayerLevel.L2,
            domains=(Domain.fusion,),
            capabilities=(AdapterCapability.gpu_rest_stub, AdapterCapability.runpod_rest),
            license_class=LicenseClass.A,
            license_evidence_uri="https://github.com/gyroswin/gyroswin",
            notes="MIT; surrogate; calibrated only after acceptance gate.",
        ),
        AdapterRecord(
            adapter_id="freegs4e_l3",
            tool="FreeGS4E",
            tool_version="0.7+",
            sub_vertical=SubVertical.fusion,
            layer=LayerLevel.L3,
            domains=(Domain.fusion,),
            capabilities=(AdapterCapability.cpu_real, AdapterCapability.cpu_fixture),
            license_class=LicenseClass.B,
            license_evidence_uri="https://github.com/freegs-plasma/freegs",
            notes="LGPL-3; Grad-Shafranov solver; pip-installable.",
        ),
        AdapterRecord(
            adapter_id="imas_python_l4",
            tool="IMAS-Python (imas_core)",
            tool_version="5.6.0",
            sub_vertical=SubVertical.fusion,
            layer=LayerLevel.L4,
            domains=(Domain.fusion,),
            capabilities=(AdapterCapability.cpu_real, AdapterCapability.cpu_fixture),
            license_class=LicenseClass.B,
            license_evidence_uri="https://github.com/iterorganization/IMAS-Core/releases/tag/5.6.0",
            notes="LGPL-3.0; netCDF backend first; HDF5/MDSplus deferred.",
        ),
        AdapterRecord(
            adapter_id="omas_l4_converter",
            tool="OMAS",
            tool_version="0.92",
            sub_vertical=SubVertical.fusion,
            layer=LayerLevel.L4,
            domains=(Domain.fusion,),
            capabilities=(AdapterCapability.cpu_real, AdapterCapability.cpu_fixture),
            license_class=LicenseClass.A,
            license_evidence_uri="https://github.com/gafusion/omas/blob/master/LICENSE",
            notes="MIT; IMAS path validators + converters.",
        ),
        AdapterRecord(
            adapter_id="paramak_l5_geometry",
            tool="Paramak",
            tool_version="2025",
            sub_vertical=SubVertical.fusion,
            layer=LayerLevel.L5,
            domains=(Domain.fusion,),
            capabilities=(AdapterCapability.cpu_real, AdapterCapability.cpu_fixture),
            license_class=LicenseClass.A,
            license_evidence_uri="https://github.com/fusion-energy/paramak/blob/main/LICENSE.txt",
            notes="MIT; parametric reactor CAD.",
        ),
    ]
    for r in seeds:
        reg.register(r)
    return reg
