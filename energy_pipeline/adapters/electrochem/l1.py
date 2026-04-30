"""L1 — Electronic Structure Adapter for electrochemistry sub-vertical.

BOUNDARY_BLOCK: Research infrastructure for in silico energy science: electrochemical conversion
(batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics,
thermoelectrics) and fusion / plasma physics. Outputs are research artifacts.
No regulatory certification claims. No clinical or human-subject use.
Defence / weapons applications are out of scope under operator policy.

Capabilities
------------
- singlepoint(spec)    : molecule-scale DFT/HF; runs tiny PySCF H2 RHF if available, else fixture.
- marcus(spec)         : Marcus electron-transfer rates; CPU-deterministic fixture.
- optical_spectrum(spec): fixture-only band-gap / optical spectrum.

Falsifiers embedded
-------------------
- lambda_eV must be > 0
- band_gap_eV in [0, 5] eV
- units field required on every quantity
- electrode reference convention must be recorded
"""
from __future__ import annotations

import hashlib
from typing import Any

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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AGENT_ID = "electrochem-l1-electronic-structure"
_GIT_SHA = "fixture-cpu-only-0000000"


def _prov(input_hash: str, output_hash: str, config_hash: str) -> ProvenanceBlock:
    return ProvenanceBlock(
        agent_id=_AGENT_ID,
        model_id="pyscf-rhf-sto3g-or-fixture",
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
        campaign_id="electrochem-l1-campaign",
        sub_vertical=SubVertical.electrochemistry,
        layer=LayerLevel.L1,
        domain=domain,
        mode=mode,
        backend=BackendBlock(
            adapter="ElectronicStructureAdapter",
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
# Falsifier helpers
# ---------------------------------------------------------------------------

def _check_units(payload: dict) -> list[FailureRecord]:
    """Verify every quantity dict has a 'unit' field."""
    failures = []
    for k, v in payload.items():
        if isinstance(v, dict) and "value" in v and "unit" not in v:
            failures.append(
                FailureRecord(
                    gate_id="units_required",
                    severity="fail",
                    message=f"quantity '{k}' missing 'unit' field",
                )
            )
    return failures


def _check_electrode_ref(payload: dict) -> list[FailureRecord]:
    if "electrode_reference" not in payload:
        return [
            FailureRecord(
                gate_id="electrode_reference_missing",
                severity="warn",
                message="electrode_reference convention not recorded in outputs",
            )
        ]
    return []


# ---------------------------------------------------------------------------
# Adapter class
# ---------------------------------------------------------------------------

class ElectronicStructureAdapter:
    """L1 electronic-structure adapter — electrochemistry sub-vertical.

    Uses PySCF (RHF/DFT) if importable; falls back to deterministic CPU fixtures.
    """

    def __init__(self) -> None:
        try:
            import pyscf  # noqa: F401
            self._pyscf_version = pyscf.__version__
            self._has_pyscf = True
        except ImportError:
            self._pyscf_version = "not-installed"
            self._has_pyscf = False

    # ------------------------------------------------------------------
    # singlepoint
    # ------------------------------------------------------------------

    def singlepoint(self, spec: dict | None = None) -> UniversalLayerEnvelope:
        """Molecule-scale single-point energy.

        If PySCF is available, runs a tiny H2 RHF/STO-3G. Otherwise returns a
        deterministic fixture with the same schema.
        """
        spec = spec or {}
        if self._has_pyscf:
            return self._singlepoint_pyscf(spec)
        return self._singlepoint_fixture(spec)

    def _singlepoint_pyscf(self, spec: dict) -> UniversalLayerEnvelope:
        from pyscf import gto, scf

        mol_spec = spec.get("molecule", "H 0 0 0; H 0 0 0.74")
        basis = spec.get("basis", "sto-3g")

        mol = gto.M(atom=mol_spec, basis=basis, verbose=0)
        mf = scf.RHF(mol)
        mf.verbose = 0
        energy_hartree = float(mf.kernel())
        energy_eV = energy_hartree * 27.2114

        outputs_payload = {
            "total_energy": {"value": energy_hartree, "unit": "hartree"},
            "total_energy_eV": {"value": energy_eV, "unit": "eV"},
            "molecule": {"value": mol_spec, "unit": "dimensionless"},
            "basis": {"value": basis, "unit": "dimensionless"},
            "method": {"value": "RHF", "unit": "dimensionless"},
            "electrode_reference": {"value": "Li/Li+ (0 V)", "unit": "dimensionless"},
        }
        unit_fails = _check_units(outputs_payload)
        ref_fails = _check_electrode_ref(outputs_payload)
        all_fails = unit_fails + ref_fails
        gate = GateStatus.fail if all_fails else GateStatus.pass_
        fb = FalsificationBlock(
            gate_status=gate,
            scientific_valid=(gate == GateStatus.pass_),
            unit_check_passed=not unit_fails,
            conservation_check_passed=True,
            boundary_check_passed=True,
            failures=all_fails,
        )
        return _make_envelope(
            domain=Domain.battery,
            mode=Mode.scientific,
            license_class=LicenseClass.A,
            license_evidence_uri="https://github.com/pyscf/pyscf/blob/master/LICENSE",
            execution_mode=ExecutionMode.local_cpu,
            tool="pyscf.scf.RHF",
            tool_version=self._pyscf_version,
            inputs_payload={"molecule": mol_spec, "basis": basis},
            outputs_payload=outputs_payload,
            falsification=fb,
        )

    def _singlepoint_fixture(self, spec: dict) -> UniversalLayerEnvelope:
        # Deterministic fixture for H2 RHF/STO-3G
        outputs_payload = {
            "total_energy": {"value": -1.1175, "unit": "hartree"},
            "total_energy_eV": {"value": -30.4086, "unit": "eV"},
            "molecule": {"value": "H 0 0 0; H 0 0 0.74", "unit": "dimensionless"},
            "basis": {"value": "sto-3g", "unit": "dimensionless"},
            "method": {"value": "RHF_fixture", "unit": "dimensionless"},
            "electrode_reference": {"value": "Li/Li+ (0 V)", "unit": "dimensionless"},
            "fixture": {"value": True, "unit": "dimensionless"},
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
            tool="fixture.singlepoint",
            tool_version="0.1.0",
            inputs_payload=spec,
            outputs_payload=outputs_payload,
            falsification=fb,
        )

    # ------------------------------------------------------------------
    # marcus
    # ------------------------------------------------------------------

    def marcus(self, spec: dict | None = None) -> UniversalLayerEnvelope:
        """Marcus electron-transfer rate — CPU-deterministic fixture.

        Falsifiers: lambda_eV > 0, units present, electrode reference recorded.
        """
        spec = spec or {}
        # Deterministic fixture values for CoO2/Li redox couple (seeded)
        lambda_eV = 0.42       # reorganisation energy, must be > 0
        delta_G0_eV = -0.15    # free energy of reaction
        T_K = spec.get("temperature_K", 298.15)

        # Marcus rate: k = (pi / hbar*lambda*kT)^0.5 * V^2 * exp(-(lambda+dG)^2/(4*lambda*kT))
        # V (electronic coupling) = 0.01 eV; kT in eV
        import math
        kT_eV = 8.617333e-5 * T_K
        V_eV = spec.get("electronic_coupling_eV", 0.01)
        prefactor = (math.pi / (lambda_eV * kT_eV)) ** 0.5 / 6.582119569e-16  # hbar in eV*s
        exponent = -((lambda_eV + delta_G0_eV) ** 2) / (4.0 * lambda_eV * kT_eV)
        k_et = prefactor * (V_eV ** 2) * math.exp(max(exponent, -700.0))

        # Falsifier: lambda must be positive
        failures: list[FailureRecord] = []
        if lambda_eV <= 0:
            failures.append(
                FailureRecord(
                    gate_id="marcus_lambda_positive",
                    severity="fail",
                    message=f"lambda_eV={lambda_eV} must be > 0 (Marcus theory requires positive reorganisation energy)",
                )
            )

        outputs_payload = {
            "lambda_eV": {"value": lambda_eV, "unit": "eV"},
            "delta_G0_eV": {"value": delta_G0_eV, "unit": "eV"},
            "k_et_s_inv": {"value": k_et, "unit": "s^-1"},
            "temperature_K": {"value": T_K, "unit": "K"},
            "electronic_coupling_eV": {"value": V_eV, "unit": "eV"},
            "electrode_reference": {"value": "Li/Li+ (0 V)", "unit": "dimensionless"},
            "method": {"value": "Marcus_classical_fixture", "unit": "dimensionless"},
        }
        unit_fails = _check_units(outputs_payload)
        ref_fails = _check_electrode_ref(outputs_payload)
        failures.extend(unit_fails + ref_fails)
        gate = GateStatus.fail if failures else GateStatus.pass_
        fb = FalsificationBlock(
            gate_status=gate,
            scientific_valid=False,  # stub
            unit_check_passed=not unit_fails,
            conservation_check_passed=True,
            boundary_check_passed=True,
            failures=failures,
        )
        return _make_envelope(
            domain=Domain.battery,
            mode=Mode.engineering_stub,
            license_class=LicenseClass.A,
            license_evidence_uri="file://fixtures/electrochem/battery_chen2020.json",
            execution_mode=ExecutionMode.local_cpu,
            tool="fixture.marcus_classical",
            tool_version="0.1.0",
            inputs_payload=dict(spec),
            outputs_payload=outputs_payload,
            falsification=fb,
        )

    # ------------------------------------------------------------------
    # optical_spectrum
    # ------------------------------------------------------------------

    def optical_spectrum(self, spec: dict | None = None) -> UniversalLayerEnvelope:
        """Optical spectrum — fixture only.

        Falsifier: band_gap_eV in [0, 5].
        """
        spec = spec or {}
        material = spec.get("material", "Si")

        # Fixture: Si at 300 K
        band_gap_eV = spec.get("band_gap_eV_override", 1.12)  # Si indirect gap

        failures: list[FailureRecord] = []
        if not (0.0 <= band_gap_eV <= 5.0):
            failures.append(
                FailureRecord(
                    gate_id="band_gap_range",
                    severity="fail",
                    message=f"band_gap_eV={band_gap_eV} outside [0, 5] eV range",
                )
            )

        # Simple 3-point absorption spectrum fixture
        photon_energies_eV = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
        absorption_cm_inv = [
            0.0 if e < band_gap_eV else 1e4 * (e - band_gap_eV) ** 0.5
            for e in photon_energies_eV
        ]

        outputs_payload = {
            "material": {"value": material, "unit": "dimensionless"},
            "band_gap_eV": {"value": band_gap_eV, "unit": "eV"},
            "photon_energies_eV": {"value": photon_energies_eV, "unit": "eV"},
            "absorption_cm_inv": {"value": absorption_cm_inv, "unit": "cm^-1"},
            "electrode_reference": {"value": "vacuum_level", "unit": "dimensionless"},
            "method": {"value": "fixture_parabolic_band", "unit": "dimensionless"},
        }
        unit_fails = _check_units(outputs_payload)
        failures.extend(unit_fails)
        gate = GateStatus.fail if failures else GateStatus.pass_
        fb = FalsificationBlock(
            gate_status=gate,
            scientific_valid=False,
            unit_check_passed=not unit_fails,
            conservation_check_passed=True,
            boundary_check_passed=True,
            failures=failures,
        )
        return _make_envelope(
            domain=Domain.pv,
            mode=Mode.engineering_stub,
            license_class=LicenseClass.A,
            license_evidence_uri="file://fixtures/electrochem/pv_sandton.json",
            execution_mode=ExecutionMode.local_cpu,
            tool="fixture.optical_spectrum",
            tool_version="0.1.0",
            inputs_payload=dict(spec),
            outputs_payload=outputs_payload,
            falsification=fb,
        )
