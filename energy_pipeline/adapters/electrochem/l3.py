"""L3 — Mesoscale Adapter for electrochemistry sub-vertical.

BOUNDARY_BLOCK: Research infrastructure for in silico energy science: electrochemical conversion
(batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics,
thermoelectrics) and fusion / plasma physics. Outputs are research artifacts.
No regulatory certification claims. No clinical or human-subject use.
Defence / weapons applications are out of scope under operator policy.

Capabilities
------------
- VTKManifestParser       : manifest stub; parses VTK file headers without loading bulk data.
- HDF5ManifestParser      : manifest stub; reads HDF5 group structure without loading bulk data.
- phasefield_stub(spec)   : synthetic tortuosity / effective diffusivity fixture.

Falsifiers
----------
- mass drift <= 1e-5 (relative)
- charge residual <= 1e-4
- grid-refinement change <= 5%
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np

from energy_pipeline.schemas import (
    BackendBlock,
    Domain,
    ExecutionMode,
    FalsificationBlock,
    FailureRecord,
    GateStatus,
    IOBlock,
    LayerLevel,
    LicenseClass,
    Mode,
    ProvenanceBlock,
    SubVertical,
    UniversalLayerEnvelope,
)

_AGENT_ID = "electrochem-l3-mesoscale"
_GIT_SHA = "parser-first-cpu-0000000"


def _prov(input_hash: str, output_hash: str, config_hash: str) -> ProvenanceBlock:
    return ProvenanceBlock(
        agent_id=_AGENT_ID,
        model_id="mesoscale-manifest-parser",
        git_sha=_GIT_SHA,
        input_hash=input_hash,
        output_hash=output_hash,
        config_hash=config_hash,
    )


def _h(d: Any) -> str:
    return hashlib.sha256(str(d).encode()).hexdigest()[:16]


def _make_envelope(
    *,
    domain: Domain,
    mode: Mode,
    license_class: LicenseClass,
    license_evidence_uri: str,
    execution_mode: ExecutionMode,
    tool: str,
    tool_version: str,
    inputs_payload: dict,
    outputs_payload: dict,
    falsification: FalsificationBlock,
) -> UniversalLayerEnvelope:
    inp_hash = _h(inputs_payload)
    out_hash = _h(outputs_payload)
    cfg_hash = _h({"tool": tool, "mode": mode})
    env = UniversalLayerEnvelope(
        campaign_id="electrochem-l3-campaign",
        sub_vertical=SubVertical.electrochemistry,
        layer=LayerLevel.L3,
        domain=domain,
        mode=mode,
        backend=BackendBlock(
            adapter="MesoscaleAdapter",
            tool=tool,
            tool_version=tool_version,
            execution_mode=execution_mode,
            license_class=license_class,
            license_evidence_uri=license_evidence_uri,
        ),
        inputs=IOBlock(payload=inputs_payload),
        outputs=IOBlock(payload=outputs_payload),
        falsification=falsification,
        provenance=_prov(inp_hash, out_hash, cfg_hash),
    )
    return env.finalize()


# ---------------------------------------------------------------------------
# VTK manifest parser stub
# ---------------------------------------------------------------------------

class VTKManifestParser:
    """Parses VTK file header/metadata only — does not load bulk data arrays.

    This is a manifest-only stub. Actual VTK data loading requires
    vtk or pyvista in a licensed compute environment.
    """

    def parse_header(self, vtk_path: str | Path) -> dict:
        """Return manifest of VTK file without reading bulk data.

        For non-existent files (testing), returns a synthetic manifest.
        """
        path = Path(vtk_path)
        if not path.exists():
            return {
                "file": str(vtk_path),
                "manifest": "synthetic_stub",
                "version": "# vtk DataFile Version 3.0",
                "title": "Synthetic electrode microstructure",
                "data_type": "BINARY",
                "dataset_type": "UNSTRUCTURED_GRID",
                "n_points_approx": 1000000,
                "n_cells_approx": 800000,
                "fields": ["phase_id", "Li_concentration", "electrolyte_potential"],
                "units": {"phase_id": "dimensionless", "Li_concentration": "mol/m^3",
                          "electrolyte_potential": "V"},
                "note": "Stub manifest — file not loaded",
            }
        # Real header parsing (first 5 lines of ASCII or binary VTK)
        with open(path, "rb") as f:
            header_bytes = f.read(512)
        lines = header_bytes.decode("ascii", errors="replace").splitlines()
        return {
            "file": str(vtk_path),
            "manifest": "real_header",
            "header_lines": lines[:5],
            "file_size_bytes": path.stat().st_size,
            "note": "Only first 5 header lines read; bulk data NOT loaded",
        }

    def manifest_envelope(self, vtk_path: str | Path) -> UniversalLayerEnvelope:
        manifest = self.parse_header(vtk_path)
        outputs_payload = {
            "vtk_manifest": {"value": manifest, "unit": "dimensionless"},
            "bulk_data_loaded": {"value": False, "unit": "dimensionless"},
        }
        fb = FalsificationBlock(
            gate_status=GateStatus.pass_,
            scientific_valid=False,
            unit_check_passed=True,
            conservation_check_passed=True,
            boundary_check_passed=True,
        )
        return _make_envelope(
            domain=Domain.battery,
            mode=Mode.engineering_stub,
            license_class=LicenseClass.A,
            license_evidence_uri="file://fixtures/electrochem/battery_chen2020.json",
            execution_mode=ExecutionMode.local_cpu,
            tool="vtk_manifest_parser",
            tool_version="0.1.0",
            inputs_payload={"vtk_path": str(vtk_path)},
            outputs_payload=outputs_payload,
            falsification=fb,
        )


# ---------------------------------------------------------------------------
# HDF5 manifest parser stub
# ---------------------------------------------------------------------------

class HDF5ManifestParser:
    """Reads HDF5 group/dataset structure without loading bulk arrays."""

    def parse_structure(self, h5_path: str | Path) -> dict:
        """Return group/dataset tree manifest."""
        path = Path(h5_path)
        if not path.exists():
            return {
                "file": str(h5_path),
                "manifest": "synthetic_stub",
                "groups": ["/phase_field", "/electrolyte", "/results"],
                "datasets": {
                    "/phase_field/phi": {"shape": [256, 256, 128], "dtype": "float64", "unit": "dimensionless"},
                    "/electrolyte/concentration": {"shape": [256, 256, 128], "dtype": "float64", "unit": "mol/m^3"},
                    "/results/tortuosity": {"shape": [3], "dtype": "float64", "unit": "dimensionless"},
                },
                "note": "Stub manifest — file not loaded",
            }
        try:
            import h5py
            with h5py.File(path, "r") as f:
                groups = []
                datasets = {}
                def _visit(name, obj):
                    if isinstance(obj, h5py.Group):
                        groups.append(f"/{name}")
                    elif isinstance(obj, h5py.Dataset):
                        datasets[f"/{name}"] = {
                            "shape": list(obj.shape),
                            "dtype": str(obj.dtype),
                        }
                f.visititems(_visit)
            return {"file": str(h5_path), "manifest": "real", "groups": groups, "datasets": datasets}
        except ImportError:
            return {
                "file": str(h5_path),
                "manifest": "h5py_unavailable",
                "note": "h5py not installed; install for real parsing",
            }

    def manifest_envelope(self, h5_path: str | Path) -> UniversalLayerEnvelope:
        structure = self.parse_structure(h5_path)
        outputs_payload = {
            "hdf5_manifest": {"value": structure, "unit": "dimensionless"},
            "bulk_data_loaded": {"value": False, "unit": "dimensionless"},
        }
        fb = FalsificationBlock(
            gate_status=GateStatus.pass_,
            scientific_valid=False,
            unit_check_passed=True,
            conservation_check_passed=True,
            boundary_check_passed=True,
        )
        return _make_envelope(
            domain=Domain.battery,
            mode=Mode.engineering_stub,
            license_class=LicenseClass.A,
            license_evidence_uri="file://fixtures/electrochem/battery_chen2020.json",
            execution_mode=ExecutionMode.local_cpu,
            tool="hdf5_manifest_parser",
            tool_version="0.1.0",
            inputs_payload={"h5_path": str(h5_path)},
            outputs_payload=outputs_payload,
            falsification=fb,
        )


# ---------------------------------------------------------------------------
# Phase-field / mesoscale stub
# ---------------------------------------------------------------------------

def phasefield_stub(spec: dict | None = None) -> UniversalLayerEnvelope:
    """Synthetic tortuosity and effective diffusivity fixture.

    Falsifiers:
    - mass drift <= 1e-5 (relative)
    - charge residual <= 1e-4
    - grid-refinement change <= 5%
    """
    spec = spec or {}
    rng = np.random.default_rng(99)

    # Geometry parameters
    porosity = spec.get("porosity", 0.3)
    tortuosity_factor = spec.get("tortuosity_factor", 2.5)  # realistic battery electrode
    D_bulk_m2_s = spec.get("D_bulk_m2_s", 2.6e-10)  # Li in liquid electrolyte

    # Bruggeman relation for effective diffusivity
    D_eff_m2_s = D_bulk_m2_s * (porosity ** 1.5)

    # Synthetic mass balance check
    mass_initial = 1.0
    mass_final = mass_initial + float(rng.normal(0, 1e-7))  # tiny numerical drift
    mass_drift = abs(mass_final - mass_initial) / mass_initial

    # Synthetic charge residual (from Poisson solver convergence)
    charge_residual = float(abs(rng.normal(0, 1e-6)))

    # Grid refinement study: coarse vs fine grid tortuosity
    tau_coarse = tortuosity_factor * (1 + 0.03 * float(rng.uniform(-1, 1)))
    tau_fine = tortuosity_factor * (1 + 0.01 * float(rng.uniform(-1, 1)))
    grid_change_frac = abs(tau_fine - tau_coarse) / abs(tau_coarse)

    failures: list[FailureRecord] = []
    if mass_drift > 1e-5:
        failures.append(
            FailureRecord(
                gate_id="mass_drift_gate",
                severity="fail",
                message=f"Mass drift {mass_drift:.2e} > 1e-5 tolerance",
            )
        )
    if charge_residual > 1e-4:
        failures.append(
            FailureRecord(
                gate_id="charge_residual_gate",
                severity="fail",
                message=f"Charge residual {charge_residual:.2e} > 1e-4 tolerance",
            )
        )
    if grid_change_frac > 0.05:
        failures.append(
            FailureRecord(
                gate_id="grid_refinement_gate",
                severity="fail",
                message=f"Grid refinement change {grid_change_frac:.3f} > 5% tolerance; mesh not converged",
            )
        )

    gate = GateStatus.fail if failures else GateStatus.pass_
    outputs_payload = {
        "porosity": {"value": porosity, "unit": "dimensionless"},
        "tortuosity_bruggeman": {"value": tortuosity_factor, "unit": "dimensionless"},
        "D_eff_m2_s": {"value": D_eff_m2_s, "unit": "m^2/s"},
        "D_bulk_m2_s": {"value": D_bulk_m2_s, "unit": "m^2/s"},
        "mass_drift_relative": {"value": mass_drift, "unit": "dimensionless"},
        "charge_residual": {"value": charge_residual, "unit": "C"},
        "grid_refinement_change_frac": {"value": grid_change_frac, "unit": "dimensionless"},
        "tortuosity_coarse": {"value": tau_coarse, "unit": "dimensionless"},
        "tortuosity_fine": {"value": tau_fine, "unit": "dimensionless"},
        "method": {"value": "bruggeman_plus_fixture_checks", "unit": "dimensionless"},
    }
    fb = FalsificationBlock(
        gate_status=gate,
        scientific_valid=False,
        unit_check_passed=True,
        conservation_check_passed=(charge_residual <= 1e-4 and mass_drift <= 1e-5),
        boundary_check_passed=True,
        failures=failures,
    )
    return _make_envelope(
        domain=Domain.battery,
        mode=Mode.engineering_stub,
        license_class=LicenseClass.A,
        license_evidence_uri="file://fixtures/electrochem/battery_chen2020.json",
        execution_mode=ExecutionMode.local_cpu,
        tool="fixture.phasefield_stub",
        tool_version="0.1.0",
        inputs_payload=dict(spec),
        outputs_payload=outputs_payload,
        falsification=fb,
    )
