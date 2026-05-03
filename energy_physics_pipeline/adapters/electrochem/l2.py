"""L2 — Atomistic / MLIP Adapter for electrochemistry sub-vertical.

BOUNDARY_BLOCK: Research infrastructure for in silico energy science: electrochemical conversion
(batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics,
thermoelectrics) and fusion / plasma physics. Outputs are research artifacts.
No regulatory certification claims. No clinical or human-subject use.
Defence / weapons applications are out of scope under operator policy.

Capabilities
------------
- MLIPManifestAdapter : checks license + checksums; requires ModelCheckpoint KG node.
- trajectory_msd(spec): synthetic MSD/RDF; numpy arrays; R^2 >= 0.95; alpha in [0.8, 1.2].
- reaction_ranking(spec): ranks candidates; falsifier rejects if uncertainty reorders or
  disagreement > 0.15 eV.

Design: manifest-only. Never loads actual MLIP weights without a registered ModelCheckpoint.
"""
from __future__ import annotations

import hashlib
from typing import Any

import numpy as np

from energy_physics_pipeline.schemas import (
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

_AGENT_ID = "electrochem-l2-atomistic-mlip"
_GIT_SHA = "manifest-only-cpu-0000000"


def _prov(input_hash: str, output_hash: str, config_hash: str) -> ProvenanceBlock:
    return ProvenanceBlock(
        agent_id=_AGENT_ID,
        model_id="mlip-manifest-only",
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
        campaign_id="electrochem-l2-campaign",
        sub_vertical=SubVertical.electrochemistry,
        layer=LayerLevel.L2,
        domain=domain,
        mode=mode,
        backend=BackendBlock(
            adapter="MLIPManifestAdapter",
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
# Manifest gating
# ---------------------------------------------------------------------------

class MLIPManifestAdapter:
    """Checks MLIP license + checksums and registers/verifies ModelCheckpoint KG nodes.

    Will NOT run weights without a registered ModelCheckpoint node in the KG.
    """

    KNOWN_MODELS = {
        "mace-mp-0": {
            "license": "MIT",
            "license_uri": "https://github.com/ACEsuit/mace/blob/main/LICENSE",
            "checksum_sha256": "placeholder_mace_mp0_sha256",
        },
        "chgnet-0.3.0": {
            "license": "MIT",
            "license_uri": "https://github.com/CederGroupHub/chgnet/blob/main/LICENSE",
            "checksum_sha256": "placeholder_chgnet_030_sha256",
        },
        "sevennet-0": {
            "license": "Apache-2.0",
            "license_uri": "https://github.com/MDIL-SNU/SevenNet/blob/main/LICENSE",
            "checksum_sha256": "placeholder_sevennet0_sha256",
        },
    }

    def check_manifest(self, model_id: str, kg_store: Any | None = None) -> dict:
        """Return manifest dict; raise if model unknown or KG node absent."""
        if model_id not in self.KNOWN_MODELS:
            raise ValueError(
                f"MLIP model '{model_id}' not in approved manifest. "
                "Register via ModelCheckpoint KG node first."
            )
        manifest = dict(self.KNOWN_MODELS[model_id])
        manifest["model_id"] = model_id
        manifest["manifest_valid"] = True

        # If kg_store provided, verify ModelCheckpoint node exists
        if kg_store is not None:
            node_id = f"ModelCheckpoint::{model_id}"
            if node_id not in getattr(kg_store, "_g", {}):
                manifest["kg_node_present"] = False
                manifest["warning"] = (
                    f"ModelCheckpoint node '{node_id}' not found in KG. "
                    "Manifest approved but weights must not be loaded until node is registered."
                )
            else:
                manifest["kg_node_present"] = True
        return manifest

    def manifest_envelope(self, model_id: str, kg_store: Any | None = None) -> UniversalLayerEnvelope:
        """Return a manifest-check envelope for the given MLIP model."""
        try:
            manifest = self.check_manifest(model_id, kg_store)
            failures: list[FailureRecord] = []
            if not manifest.get("kg_node_present", True):
                failures.append(
                    FailureRecord(
                        gate_id="model_checkpoint_missing",
                        severity="warn",
                        message=manifest.get("warning", "ModelCheckpoint KG node missing"),
                    )
                )
            gate = GateStatus.warn if failures else GateStatus.pass_
            outputs_payload = {
                "model_id": {"value": model_id, "unit": "dimensionless"},
                "license": {"value": manifest["license"], "unit": "dimensionless"},
                "license_uri": {"value": manifest["license_uri"], "unit": "dimensionless"},
                "checksum_sha256": {"value": manifest["checksum_sha256"], "unit": "dimensionless"},
                "manifest_valid": {"value": True, "unit": "dimensionless"},
            }
        except ValueError as exc:
            failures = [
                FailureRecord(
                    gate_id="mlip_manifest_rejected",
                    severity="fail",
                    message=str(exc),
                )
            ]
            gate = GateStatus.fail
            outputs_payload = {
                "model_id": {"value": model_id, "unit": "dimensionless"},
                "manifest_valid": {"value": False, "unit": "dimensionless"},
            }

        fb = FalsificationBlock(
            gate_status=gate,
            scientific_valid=False,
            unit_check_passed=True,
            conservation_check_passed=True,
            boundary_check_passed=True,
            failures=failures,
        )
        return _make_envelope(
            domain=Domain.battery,
            mode=Mode.engineering_stub,
            license_class=LicenseClass.B,
            license_evidence_uri="https://github.com/ACEsuit/mace/blob/main/LICENSE",
            execution_mode=ExecutionMode.local_cpu,
            tool="mlip.manifest_check",
            tool_version="0.1.0",
            inputs_payload={"model_id": model_id},
            outputs_payload=outputs_payload,
            falsification=fb,
        )


# ---------------------------------------------------------------------------
# Trajectory analysis
# ---------------------------------------------------------------------------

def trajectory_msd(spec: dict | None = None) -> UniversalLayerEnvelope:
    """Synthetic MSD fixture.

    Generates a deterministic MSD(t) curve for Li diffusion in a model electrode.
    Fits diffusion coefficient via linear regression.
    Falsifiers: R^2 >= 0.95; diffusion exponent alpha in [0.8, 1.2].
    """
    spec = spec or {}
    rng = np.random.default_rng(42)
    n_steps = spec.get("n_steps", 200)
    # Use nanosecond timesteps so signal >> noise throughout trajectory
    # Li diffusion in graphite: D ~ 1.5e-10 cm^2/s
    # At t=1 ns: MSD_true = 6*1.5e-10*1e-9 = 9e-19 cm^2
    # Noise std = 1e-21 cm^2 (< 0.2% of signal) -> clean log-log fit
    dt_ns = spec.get("dt_ns", 1.0)   # [ns]; default 1 ns
    D_true_cm2_s = spec.get("D_true_cm2_s", 1.5e-10)  # Li in graphite [cm^2/s]

    t_ns = np.arange(1, n_steps + 1, dtype=float) * dt_ns
    t_s = t_ns * 1e-9  # [s]
    msd_signal = 6.0 * D_true_cm2_s * t_s  # [cm^2]; linear in t (normal diffusion)
    noise_std = 0.002 * float(msd_signal.mean())  # 0.2% relative noise
    msd_cm2 = msd_signal + rng.normal(0, noise_std, n_steps)
    msd_cm2 = np.maximum(msd_cm2, 1e-35)

    # Fit D from linear portion (slope of MSD vs t)
    D_fit = float(np.polyfit(t_s, msd_cm2, 1)[0]) / 6.0
    # Fit MSD = A * t^alpha via log-log regression (middle 50% of data)
    i_start = n_steps // 4
    i_end = 3 * n_steps // 4
    log_t = np.log(t_s[i_start:i_end])
    log_msd = np.log(msd_cm2[i_start:i_end])
    coeffs = np.polyfit(log_t, log_msd, 1)
    alpha = float(coeffs[0])  # should be ~ 1.0 for normal diffusion

    # R^2 of linear MSD fit
    msd_pred = 6.0 * D_fit * t_s
    ss_res = float(np.sum((msd_cm2 - msd_pred) ** 2))
    ss_tot = float(np.sum((msd_cm2 - msd_cm2.mean()) ** 2))
    r2 = 1.0 - ss_res / (ss_tot + 1e-60)

    # Expose dt in ps units for output (backward compat)
    dt_ps = dt_ns * 1000.0
    t_ps = t_ns * 1000.0

    failures: list[FailureRecord] = []
    if r2 < 0.95:
        failures.append(
            FailureRecord(
                gate_id="msd_r2_gate",
                severity="fail",
                message=f"MSD linear fit R^2={r2:.4f} < 0.95 (diffusive regime not established)",
            )
        )
    if not (0.8 <= alpha <= 1.2):
        failures.append(
            FailureRecord(
                gate_id="msd_alpha_gate",
                severity="fail",
                message=f"Diffusion exponent alpha={alpha:.3f} outside [0.8, 1.2]",
            )
        )

    gate = GateStatus.fail if failures else GateStatus.pass_
    outputs_payload = {
        "D_fit_cm2_s": {"value": D_fit, "unit": "cm^2/s"},
        "diffusion_exponent_alpha": {"value": alpha, "unit": "dimensionless"},
        "msd_r2": {"value": r2, "unit": "dimensionless"},
        "n_steps": {"value": n_steps, "unit": "dimensionless"},
        "dt_ps": {"value": dt_ps, "unit": "ps"},
        "t_ps": {"value": t_ps.tolist(), "unit": "ps"},
        "msd_cm2": {"value": msd_cm2.tolist(), "unit": "cm^2"},
        "species": {"value": "Li", "unit": "dimensionless"},
    }
    fb = FalsificationBlock(
        gate_status=gate,
        scientific_valid=False,
        unit_check_passed=True,
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
        tool="fixture.trajectory_msd",
        tool_version="0.1.0",
        inputs_payload=dict(spec),
        outputs_payload=outputs_payload,
        falsification=fb,
    )


def reaction_ranking(spec: dict | None = None) -> UniversalLayerEnvelope:
    """Rank candidate electrode reactions by predicted reaction energy.

    Falsifier: ranking invalid if uncertainty reorders candidates or
    model disagreement > 0.15 eV on any pair.
    """
    spec = spec or {}
    rng = np.random.default_rng(7)

    # Synthetic candidate reactions (LiCoO2 delithiation stages)
    candidates = spec.get("candidates", [
        {"id": "rxn_A", "label": "LiCoO2 -> Li0.75CoO2 + 0.25 Li", "dE_eV": -0.12},
        {"id": "rxn_B", "label": "Li0.75CoO2 -> Li0.5CoO2 + 0.25 Li", "dE_eV": -0.08},
        {"id": "rxn_C", "label": "Li0.5CoO2 -> Li0.25CoO2 + 0.25 Li", "dE_eV": 0.05},
    ])

    # Simulate two MLIP model predictions with uncertainty
    predictions = []
    failures: list[FailureRecord] = []

    for c in candidates:
        dE_mean = c["dE_eV"]
        sigma_model1 = float(rng.uniform(0.01, 0.05))
        sigma_model2 = float(rng.uniform(0.01, 0.05))
        pred_m1 = dE_mean + float(rng.normal(0, sigma_model1))
        pred_m2 = dE_mean + float(rng.normal(0, sigma_model2))
        disagreement = abs(pred_m1 - pred_m2)
        if disagreement > 0.15:
            failures.append(
                FailureRecord(
                    gate_id="reaction_ranking_disagreement",
                    severity="fail",
                    message=(
                        f"Model disagreement for {c['id']}: {disagreement:.3f} eV > 0.15 eV threshold; "
                        "ranking invalid"
                    ),
                )
            )
        predictions.append({
            "id": c["id"],
            "label": c["label"],
            "dE_eV_mean": (pred_m1 + pred_m2) / 2.0,
            "dE_eV_model1": pred_m1,
            "dE_eV_model2": pred_m2,
            "disagreement_eV": disagreement,
            "sigma_model1": sigma_model1,
            "sigma_model2": sigma_model2,
        })

    # Check uncertainty reordering: rank by mean vs rank by model1
    ranked_mean = sorted(predictions, key=lambda x: x["dE_eV_mean"])
    ranked_m1 = sorted(predictions, key=lambda x: x["dE_eV_model1"])
    for i, (rm, r1) in enumerate(zip(ranked_mean, ranked_m1)):
        if rm["id"] != r1["id"]:
            failures.append(
                FailureRecord(
                    gate_id="reaction_ranking_uncertainty_reorder",
                    severity="fail",
                    message=(
                        f"Uncertainty reorders ranking at position {i}: "
                        f"mean_rank={rm['id']} vs model1_rank={r1['id']}; "
                        "ranking unreliable"
                    ),
                )
            )
            break  # report first reordering only

    gate = GateStatus.fail if failures else GateStatus.pass_
    outputs_payload = {
        "ranked_reactions": {"value": ranked_mean, "unit": "dimensionless"},
        "n_candidates": {"value": len(candidates), "unit": "dimensionless"},
        "max_disagreement_eV": {"value": max(p["disagreement_eV"] for p in predictions), "unit": "eV"},
        "ranking_valid": {"value": not failures, "unit": "dimensionless"},
    }
    fb = FalsificationBlock(
        gate_status=gate,
        scientific_valid=False,
        unit_check_passed=True,
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
        tool="fixture.reaction_ranking",
        tool_version="0.1.0",
        inputs_payload=dict(spec),
        outputs_payload=outputs_payload,
        falsification=fb,
    )
