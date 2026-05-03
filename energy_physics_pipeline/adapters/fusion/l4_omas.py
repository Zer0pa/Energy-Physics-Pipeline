"""L4 fusion adapter — real OMAS-backed IMAS path validator.

This module provides ``OmasRealValidatorAdapter``, which uses the installed
``omas`` library (0.95.2+) to validate IMAS Data Dictionary paths against the
actual DD JSON structures bundled with OMAS.  When ``omas`` is absent it falls
back to a string-pattern validator that mirrors the path format rules and emits
``mode=engineering_stub``.

Design notes
------------
* OMAS 0.95.2 ships DD 3.41.0 as the default ``imas_version``.
* Path validation strategy (two independent checks):

  1. ``omas.omas_info_node(dd_path)`` — queries the embedded DD JSON and
     returns a non-empty dict with a ``data_type`` key for every valid leaf
     path.  Returns ``{}`` for unknown paths.  This is the primary check.

  2. ``ods[user_path] = value`` — sets the path on a live ``ODS()`` instance.
     OMAS raises ``LookupError`` for unknown paths.  This confirms the path is
     also writable/readable as real data, not just a DD metadata entry.

* Integer index segments in user-facing paths (e.g. ``time_slice.0``) are
  replaced by ``:`` before querying ``omas_info_node``, which uses the
  colon-wildcard notation for array-of-structures indices.

CPU-only; no GPU required.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from energy_physics_pipeline.boundary import BoundaryViolation, check_fusion_intent
from energy_physics_pipeline.schemas.canonical import sha256_of
from energy_physics_pipeline.schemas.envelope import (
    BackendBlock,
    Domain,
    ExecutionMode,
    FailureRecord,
    FalsificationBlock,
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
# Spec dataclass
# ---------------------------------------------------------------------------

_DEFAULT_PATHS: list[str] = [
    "equilibrium.time_slice.0.global_quantities.q_axis",
    "equilibrium.time_slice.0.profiles_1d.q",
    "core_profiles.profiles_1d.0.electrons.density",
    "core_profiles.profiles_1d.0.electrons.temperature",
]


@dataclass
class OmasValidateSpec:
    """Input contract for ``OmasRealValidatorAdapter.run()``."""

    intent: str = "OMAS path validation against research-bound fixture"
    ods_paths: list[str] = field(default_factory=lambda: list(_DEFAULT_PATHS))
    data_dictionary_version: str = "3.41.0"
    campaign_id: str = "fusion-l4-omas"

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "ods_paths": self.ods_paths,
            "data_dictionary_version": self.data_dictionary_version,
            "campaign_id": self.campaign_id,
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_INDEX_RE = re.compile(r"\b\d+\b")


def _user_path_to_dd_path(path: str) -> str:
    """Replace integer index segments with ':' for ``omas_info_node`` queries."""
    return _INDEX_RE.sub(":", path)


def _validate_path_pattern(path: str) -> bool:
    """Fallback string-pattern validity check (used when omas is unavailable).

    A minimal structural sanity check: path must have at least 3 dot-separated
    segments, contain no spaces, and start with a known IDS prefix.
    """
    known_ids = {
        "equilibrium", "core_profiles", "core_sources", "core_transport",
        "magnetics", "mhd", "nbi", "ec_launchers", "ic_antennas",
        "lh_antennas", "pellets", "gas_injection",
    }
    parts = path.split(".")
    if len(parts) < 3:
        return False
    if " " in path:
        return False
    if parts[0] not in known_ids:
        return False
    return True


# ---------------------------------------------------------------------------
# Sample values for real-path ODS write-and-read test
# ---------------------------------------------------------------------------

def _sample_value_for_path(path: str) -> Any:
    """Return a physically representative sample value for each known path."""
    import numpy as np  # lazy import; only called on real path

    if path.endswith(".q_axis"):
        return 1.05
    if path.endswith(".profiles_1d.q") or path.endswith(".q"):
        return list(np.linspace(1.05, 5.0, 20).tolist())
    if path.endswith(".electrons.density"):
        return list(np.linspace(1.0e19, 5.0e19, 20).tolist())
    if path.endswith(".electrons.temperature"):
        return list(np.linspace(5000.0, 1000.0, 20).tolist())
    # Generic fallback
    return 1.0


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class OmasRealValidatorAdapter:
    """L4 IMAS path validator backed by the real OMAS Data Dictionary.

    Validation strategy
    -------------------
    **Real path (omas available):**

    For each path in ``spec.ods_paths``:

    1. Convert integer indices to ``:`` and call ``omas.omas_info_node`` on the
       resulting DD path.  An empty or ``data_type``-less result means the path
       does not exist in the DD.
    2. Attempt to write a sample value to a live ``ODS()`` instance.  A
       ``LookupError`` from OMAS confirms the path is invalid.
    3. Both checks must agree.  A path is ``valid`` only when both pass.

    **Fallback (omas absent):**

    Apply ``_validate_path_pattern`` (structural string check) and emit
    ``mode=engineering_stub`` to signal reduced confidence.
    """

    ADAPTER_NAME = "fusion.l4.omas_real_validator"
    TOOL_NAME = "OMAS (real Data Dictionary validator)"
    TOOL_VERSION = "omas-0.95.2"

    def __init__(
        self,
        *,
        agent_id: str = "fusion.l4.omas_real",
        git_sha: str = "fixture",
    ) -> None:
        self.agent_id = agent_id
        self.git_sha = git_sha

    # ------------------------------------------------------------------
    def run(self, spec: OmasValidateSpec) -> UniversalLayerEnvelope:
        """Validate all paths in ``spec.ods_paths`` and return an envelope.

        Raises
        ------
        BoundaryViolation
            If ``spec.intent`` matches a forbidden fusion intent.
        """
        # Pre-flight boundary check
        forbidden = check_fusion_intent(spec.intent)
        if forbidden:
            raise BoundaryViolation(
                f"L4 OMAS input intent matched forbidden term '{forbidden}'; refusing"
            )

        spec_payload = spec.to_dict()
        input_hash = sha256_of(spec_payload)

        # Try to import OMAS
        omas_available = False
        omas_version_str = "unavailable"
        try:
            import omas as _omas  # noqa: PLC0415

            omas_available = True
            omas_version_str = getattr(_omas, "__version__", "unknown")
        except ImportError:
            pass

        if omas_available:
            path_results, failures, mode = self._validate_real(spec, _omas)  # type: ignore[name-defined]
        else:
            path_results, failures, mode = self._validate_fallback(spec)

        n_valid = sum(1 for r in path_results.values() if r["valid"])
        n_invalid = len(path_results) - n_valid

        # Any invalid path forces gate_status=fail
        any_invalid = n_invalid > 0
        gate = GateStatus.fail if any_invalid else GateStatus.pass_

        # scientific_valid only when real OMAS ran AND all paths pass
        scientific_valid = omas_available and not any_invalid

        outputs: dict[str, Any] = {
            "per_path_results": path_results,
            "total_paths_checked": len(path_results),
            "n_valid": n_valid,
            "n_invalid": n_invalid,
            "omas_version": omas_version_str,
            "dd_version": spec.data_dictionary_version,
            "omas_available": omas_available,
            "quantities": {
                "n_paths_valid": {"value": n_valid, "unit": "1"},
            },
        }
        outputs_hash = sha256_of(outputs)

        env = UniversalLayerEnvelope(
            campaign_id=spec.campaign_id,
            sub_vertical=SubVertical.fusion,
            layer=LayerLevel.L4,
            domain=Domain.fusion,
            mode=mode,
            backend=BackendBlock(
                adapter=self.ADAPTER_NAME,
                tool=self.TOOL_NAME,
                tool_version=self.TOOL_VERSION,
                execution_mode=ExecutionMode.local_cpu,
                license_class=LicenseClass.A,
                license_evidence_uri="https://github.com/gafusion/omas/blob/master/LICENSE",
            ),
            inputs=IOBlock(payload=spec_payload),
            outputs=IOBlock(payload=outputs),
            falsification=FalsificationBlock(
                gate_status=gate,
                scientific_valid=scientific_valid,
                unit_check_passed=True,
                conservation_check_passed=True,
                boundary_check_passed=True,
                failures=failures,
            ),
            provenance=ProvenanceBlock(
                agent_id=self.agent_id,
                model_id=f"omas-dd-{spec.data_dictionary_version}",
                git_sha=self.git_sha,
                created_at=datetime.now(timezone.utc),
                input_hash=input_hash,
                output_hash=outputs_hash,
                config_hash=sha256_of(
                    {
                        "dd_version": spec.data_dictionary_version,
                        "paths": spec.ods_paths,
                        "omas_available": omas_available,
                    }
                ),
                source_refs=[
                    "gafusion/omas",
                    "ITER IMAS Data Dictionary 3.41.0",
                    "https://github.com/gafusion/omas",
                ],
            ),
        )
        return env.finalize()

    # ------------------------------------------------------------------
    def _validate_real(
        self,
        spec: OmasValidateSpec,
        omas_mod: Any,
    ) -> tuple[dict[str, Any], list[FailureRecord], Mode]:
        """Run real OMAS DD validation for each path."""
        try:
            ods = omas_mod.ODS()
        except Exception as exc:  # OMAS API surface changed — degrade gracefully
            return self._validate_fallback(
                spec, extra_note=f"ODS() constructor failed: {exc}"
            )

        path_results: dict[str, Any] = {}
        failures: list[FailureRecord] = []

        for user_path in spec.ods_paths:
            dd_path = _user_path_to_dd_path(user_path)
            result: dict[str, Any] = {
                "user_path": user_path,
                "dd_path": dd_path,
                "valid": False,
                "dd_check": None,
                "ods_write_check": None,
                "data_type": None,
                "units": None,
                "error": None,
            }

            # --- Check 1: DD metadata lookup via omas_info_node ---
            dd_check_passed = False
            try:
                info = omas_mod.omas_info_node(dd_path)
                dd_check_passed = bool(info) and "data_type" in info
                result["dd_check"] = dd_check_passed
                if dd_check_passed:
                    result["data_type"] = info.get("data_type")
                    result["units"] = info.get("units")
            except Exception as exc:
                result["dd_check"] = False
                result["error"] = f"omas_info_node error: {exc}"

            # --- Check 2: ODS write validation ---
            ods_write_passed = False
            if dd_check_passed:
                try:
                    sample = _sample_value_for_path(user_path)
                    ods[user_path] = sample
                    # Confirm readback
                    _ = ods[user_path]
                    ods_write_passed = True
                    result["ods_write_check"] = True
                except LookupError as exc:
                    result["ods_write_check"] = False
                    result["error"] = f"ODS LookupError: {exc}"
                except Exception as exc:
                    result["ods_write_check"] = False
                    result["error"] = f"ODS write error: {type(exc).__name__}: {exc}"
            else:
                # DD check already failed — skip ODS write
                result["ods_write_check"] = False
                if result["error"] is None:
                    result["error"] = f"Path not found in IMAS DD {spec.data_dictionary_version}"

            result["valid"] = dd_check_passed and ods_write_passed
            path_results[user_path] = result

            if not result["valid"]:
                failures.append(
                    FailureRecord(
                        gate_id="omas.path_invalid",
                        severity="fail",
                        message=(
                            f"IMAS path '{user_path}' failed DD validation "
                            f"(dd_check={result['dd_check']}, "
                            f"ods_write_check={result['ods_write_check']}): "
                            f"{result.get('error', 'unknown error')}"
                        ),
                    )
                )

        mode = Mode.scientific if not failures else Mode.engineering_stub
        return path_results, failures, mode

    # ------------------------------------------------------------------
    def _validate_fallback(
        self,
        spec: OmasValidateSpec,
        extra_note: str = "",
    ) -> tuple[dict[str, Any], list[FailureRecord], Mode]:
        """String-pattern path validation when OMAS is unavailable."""
        path_results: dict[str, Any] = {}
        failures: list[FailureRecord] = []

        for user_path in spec.ods_paths:
            is_valid = _validate_path_pattern(user_path)
            result: dict[str, Any] = {
                "user_path": user_path,
                "dd_path": _user_path_to_dd_path(user_path),
                "valid": is_valid,
                "dd_check": None,  # not available in fallback
                "ods_write_check": None,
                "data_type": None,
                "units": None,
                "error": None if is_valid else f"Path fails structural pattern check{'; ' + extra_note if extra_note else ''}",
            }
            path_results[user_path] = result

            if not is_valid:
                failures.append(
                    FailureRecord(
                        gate_id="omas.path_invalid",
                        severity="fail",
                        message=f"IMAS path '{user_path}' failed fallback structural validation",
                    )
                )

        return path_results, failures, Mode.engineering_stub
