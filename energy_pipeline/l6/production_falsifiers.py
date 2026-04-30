"""Production falsifier set — moved from test-local helpers per CPU hardening brief §3.

These falsifiers must run on every accepted adapter / REST output, not just inside the
falsification wave tests. Test-local helpers are no longer authority.

Structure:

  - One production falsifier per physical / contractual gate.
  - `DEFAULT_FALSIFIER_SET` is the ordered tuple to apply to every envelope.
  - `apply_default_falsifiers(env)` is the production entry point — runs the default
    set, mutates `env.falsification`, and returns the (possibly demoted) envelope.
  - `apply_default_falsifiers_to_dro(dro)` does the equivalent for DRO-only checks.

Boundary: every falsifier preserves the boundary block. None mutate the input
artifact's `boundary` field.
"""
from __future__ import annotations

from typing import Any, Mapping

from energy_pipeline.l6.router import (
    Falsifier,
    boundary_falsifier,
    license_promotion_falsifier,
    run as run_router,
    stub_scientific_valid_falsifier,
)
from energy_pipeline.schemas import (
    DeviceResponseObject,
    Mode,
    UniversalLayerEnvelope,
)
from energy_pipeline.schemas.envelope import FailureRecord


# ---------------------------------------------------------------------------
# Tools that require isolation evidence even though they sit in Class B
# Per CPU hardening brief §5: GPL/AGPL must carry isolation evidence before
# scientific or product promotion.
# ---------------------------------------------------------------------------

GPL_TOOLS_REQUIRING_ISOLATION_EVIDENCE: frozenset[str] = frozenset(
    {
        # Each lower-cased tool string we expect to encounter in BackendBlock.tool.
        "alphapem",
        "lbpm",
        "moose",  # MOOSE LGPL technically allows dynamic linking; we still demand evidence
        "raccoon",
        "moose+raccoon",
        "lammps",
        "cp2k",
        "gpaw",
        # Llama-family models inherit conditional licensing — treat them similarly
        "deepseek-r1-distill-llama-70b",
        "llama",
    }
)


_VETTED_LOCAL_GRANT_PREFIX = "file:///etc/zer0pa/license-grants/"


def gpl_isolation_falsifier(env: UniversalLayerEnvelope) -> list[FailureRecord] | None:
    """Refuse scientific mode for GPL-style tools without an isolation grant URI.

    Wave 4 §5 tightening: a public `https://...` LICENSE URL is NOT acceptable
    isolation evidence. Acceptable forms:

      * `kg://license-grant/<tool>...` — knowledge-graph isolation grant record.
      * `file:///etc/zer0pa/license-grants/...` — vetted local grant record (the
        single canonical local prefix for production deploys).

    The bare project LICENSE URL (which is publicly shared with everyone) cannot
    constitute an isolation/grant decision — the brief states "public HTTPS
    license pages do not count as GPL/conditional isolation grants".
    """
    if env.mode != Mode.scientific:
        return None
    tool_lower = (env.backend.tool or "").lower()
    needs = any(needle in tool_lower for needle in GPL_TOOLS_REQUIRING_ISOLATION_EVIDENCE)
    if not needs:
        return None
    uri = env.backend.license_evidence_uri or ""
    if uri.startswith("kg://license-grant/") or uri.startswith(_VETTED_LOCAL_GRANT_PREFIX):
        return None
    return [
        FailureRecord(
            gate_id="gpl_isolation_required",
            severity="fail",
            message=(
                f"Tool '{env.backend.tool}' is GPL/conditional-license; "
                "scientific mode requires `kg://license-grant/<tool>` or "
                f"`{_VETTED_LOCAL_GRANT_PREFIX}<tool>...` evidence. "
                f"Got `{uri}` — bare HTTPS LICENSE URLs are not isolation grants."
            ),
        )
    ]


# ---------------------------------------------------------------------------
# Recursive units enforcement (H5)
# ---------------------------------------------------------------------------

# Numeric leaves whose key suggests an explicit dimensionless quantity. These
# are allowed without an explicit `unit` sibling.
_DIMENSIONLESS_KEY_HINTS: tuple[str, ...] = (
    "_fraction",
    "_pct",
    "_ratio",
    "soc",
    "fill_factor",
    "pce_fraction",
    "tbr_dimensionless_research_only",
    "h98",
    "beta_n",
    "q95",
    "ti_te",
    "shat",
    "li6_enrichment",
    "cocos",
    "li_6",
    "n_iterations",
    "n_voltage_points",
    "n_total",
    "n_psi",
    "n_time_slices",
    "occurrence",
    "exp_iterations",
)

_NON_PHYSICAL_KEY_HINTS: tuple[str, ...] = (
    "_count",
    "_id",
    "_path",
    "version",
    "checksum",
    "method",
    "scheme",
    "campaign",
    "intent",
    "domain",
    "boundary",
    "agent",
    "model",
    "shape",
    "convergence",
    "solver",
    "license",
    "rights",
    "uri",
    "url",
    "sha",
    "epoch",
    "seed",
    "iteration",
    "ids_paths_used",
    "ids_paths",
    "tool",
    "gate",
)

_QUANTITIES_KEY = "quantities"


def _looks_dimensionless(key: str) -> bool:
    k = key.lower()
    if k in _DIMENSIONLESS_KEY_HINTS:
        return True
    return any(hint in k for hint in _DIMENSIONLESS_KEY_HINTS)


def _looks_non_physical(key: str) -> bool:
    k = key.lower()
    return any(hint in k for hint in _NON_PHYSICAL_KEY_HINTS)


def _walk_for_unitless_numbers(
    obj: Any,
    path: tuple[str, ...] = (),
    *,
    inside_quantities: bool = False,
) -> list[tuple[tuple[str, ...], Any]]:
    """Find numeric leaves whose key hints physical and which lack a unit sibling.

    We treat:
      - dict {value, unit, ...} as a unit-bearing physical leaf when both keys present
      - a number under a *_dimensionless or whitelisted key as compliant
      - anything else numeric under a physical-sounding key as a violation
    """
    out: list[tuple[tuple[str, ...], Any]] = []
    if isinstance(obj, Mapping):
        # Specifically inside an `outputs.payload.quantities` block, every entry
        # must be {value, unit, ...}.
        if inside_quantities:
            for k, v in obj.items():
                p = path + (str(k),)
                if isinstance(v, Mapping):
                    if "value" not in v or "unit" not in v:
                        out.append((p, v))
                else:
                    out.append((p, v))
            return out

        if "value" in obj and "unit" in obj:
            return out  # this dict is a unit-bearing leaf
        # Recurse with `inside_quantities=True` if we step into a `quantities` key.
        for k, v in obj.items():
            sub_inside = inside_quantities or (isinstance(k, str) and k.lower() == _QUANTITIES_KEY)
            out.extend(_walk_for_unitless_numbers(v, path + (str(k),), inside_quantities=sub_inside))
        return out
    if isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            out.extend(_walk_for_unitless_numbers(v, path + (str(i),), inside_quantities=inside_quantities))
        return out
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        # We only complain at the leaf when the path's last segment looks
        # physical and is not whitelisted.
        if path:
            last = path[-1]
            if last.isdigit():
                # numeric index inside a list — judge by parent
                last = path[-2] if len(path) >= 2 else last
            if _looks_non_physical(last):
                return out
            if _looks_dimensionless(last):
                return out
            # Heuristic: if the leaf appears outside a `quantities` block AND the
            # key looks physical (contains an SI hint), require unit.
            si_hints = ("_v", "_w", "_a", "_s", "_kg", "_pa", "_mw", "_kev",
                        "_ev", "_t", "_m", "_hz", "_k_", "_bq", "_msv",
                        "_usv", "_ohm", "_torr", "_per_", "_voltage", "_current")
            # Trailing-unit suffix patterns ("..._K", "..._eV", "..._MA")
            # standardised to lowercase for the .endswith() check below.
            si_suffix_hints = (
                "_k", "_v", "_a", "_w", "_s", "_t", "_m", "_pa", "_mw", "_kev",
                "_ev", "_ma", "_kg", "_hz", "_bq",
            )
            if any(last.lower().endswith(s) for s in si_suffix_hints):
                out.append((path, obj))
                return out
            if any(h in last.lower() for h in si_hints):
                out.append((path, obj))
        return out
    return out


def units_recursive_falsifier(env: UniversalLayerEnvelope) -> list[FailureRecord] | None:
    """Walk outputs.payload looking for numeric physical leaves without units."""
    payload = env.outputs.payload or {}
    bad = _walk_for_unitless_numbers(payload)
    if not bad:
        return None
    # Aggregate the first 8 violations to keep messages bounded.
    sample = ", ".join(".".join(p) for p, _ in bad[:8])
    return [
        FailureRecord(
            gate_id="units_recursive_required",
            severity="fail",
            message=(
                f"Numeric physical leaves missing unit / quantities wrapper: "
                f"{sample} ({len(bad)} total). Every physical scalar must be "
                "either inside an `outputs.payload.quantities` map with `value`+`unit` "
                "or carry an explicit dimensionless suffix (_fraction, _ratio, etc.)."
            ),
        )
    ]


# ---------------------------------------------------------------------------
# COCOS unit gate (T5) — moved from test_falsification_wave.py
# ---------------------------------------------------------------------------


def cocos_unit_falsifier_dro(dro: DeviceResponseObject) -> list[FailureRecord] | None:
    """Fusion DROs must carry an explicit unit on every operating-conditions axis."""
    if dro.sub_vertical.value != "fusion":
        return None
    failures: list[FailureRecord] = []
    for axis in dro.operating_conditions.axes:
        if not axis.unit or axis.unit.strip() == "":
            failures.append(
                FailureRecord(
                    gate_id="cocos_unit_required",
                    severity="fail",
                    message=(
                        f"Axis '{axis.name}' has no unit. COCOS / IMAS require "
                        "every spatial coordinate to carry an explicit SI unit."
                    ),
                )
            )
    return failures or None


# ---------------------------------------------------------------------------
# Negative T_e (T6)
# ---------------------------------------------------------------------------


def negative_te_falsifier(env: UniversalLayerEnvelope) -> list[FailureRecord] | None:
    payload = env.outputs.payload or {}
    te = payload.get("T_e_eV")
    if te is None:
        # also check inside quantities
        q = payload.get("quantities") or {}
        te_q = q.get("T_e") or q.get("T_e_eV")
        if isinstance(te_q, Mapping):
            te = te_q.get("value")
    if te is not None and te < 0:
        return [
            FailureRecord(
                gate_id="negative_temperature",
                severity="critical",
                message=f"T_e_eV={te} non-physical; electron temperature must be >= 0 eV.",
            )
        ]
    return None


# ---------------------------------------------------------------------------
# Negative n_e (T7)
# ---------------------------------------------------------------------------


def negative_ne_falsifier(env: UniversalLayerEnvelope) -> list[FailureRecord] | None:
    payload = env.outputs.payload or {}
    ne = payload.get("n_e_m3")
    if ne is None:
        q = payload.get("quantities") or {}
        ne_q = q.get("n_e") or q.get("n_e_m3")
        if isinstance(ne_q, Mapping):
            ne = ne_q.get("value")
    if ne is not None and ne < 0:
        return [
            FailureRecord(
                gate_id="negative_density",
                severity="critical",
                message=f"n_e_m3={ne} non-physical; electron density must be >= 0.",
            )
        ]
    return None


# ---------------------------------------------------------------------------
# Above-Carnot (T9)
# ---------------------------------------------------------------------------


def above_carnot_falsifier(env: UniversalLayerEnvelope) -> list[FailureRecord] | None:
    payload = env.outputs.payload or {}
    eff = payload.get("efficiency")
    T_h = payload.get("T_h_K")
    T_c = payload.get("T_c_K")
    if eff is None or T_h is None or T_c is None:
        return None
    if T_h <= 0 or T_c <= 0:
        return [
            FailureRecord(
                gate_id="carnot_check",
                severity="critical",
                message=f"Non-physical temperatures: T_h={T_h} K, T_c={T_c} K",
            )
        ]
    carnot = 1.0 - T_c / T_h
    if eff > carnot:
        return [
            FailureRecord(
                gate_id="above_carnot_efficiency",
                severity="critical",
                message=(
                    f"Claimed efficiency={eff:.4f} exceeds Carnot limit "
                    f"η_C={carnot:.4f} (T_h={T_h} K, T_c={T_c} K). Second-law violation."
                ),
            )
        ]
    return None


# ---------------------------------------------------------------------------
# PV fill factor (T8) — at envelope payload level
# ---------------------------------------------------------------------------


def pv_fill_factor_falsifier(env: UniversalLayerEnvelope) -> list[FailureRecord] | None:
    """PV fill factor must be in [0, 1]. The DRO `ScalarMetrics._zero_one`
    validator catches this at construct time; we also check the envelope's
    output payload because some adapters emit `fill_factor` directly without
    a DRO.
    """
    payload = env.outputs.payload or {}

    def _walk_for_fill_factor(p: Any) -> list[float]:
        out = []
        if isinstance(p, Mapping):
            for k, v in p.items():
                lk = k.lower() if isinstance(k, str) else ""
                if "fill_factor" in lk and isinstance(v, (int, float)) and not isinstance(v, bool):
                    out.append(float(v))
                elif "fill_factor" in lk and isinstance(v, Mapping) and "value" in v:
                    val = v.get("value")
                    if isinstance(val, (int, float)) and not isinstance(val, bool):
                        out.append(float(val))
                else:
                    out.extend(_walk_for_fill_factor(v))
        elif isinstance(p, (list, tuple)):
            for item in p:
                out.extend(_walk_for_fill_factor(item))
        return out

    bad = [v for v in _walk_for_fill_factor(payload) if not (0.0 <= v <= 1.0)]
    if bad:
        return [
            FailureRecord(
                gate_id="pv_fill_factor_range",
                severity="fail",
                message=f"PV fill_factor outside [0, 1]: {bad}",
            )
        ]
    return None


def pce_fraction_falsifier(env: UniversalLayerEnvelope) -> list[FailureRecord] | None:
    """PV PCE fraction must be in [0, 1] — same logic as fill factor."""
    payload = env.outputs.payload or {}

    def _walk(p: Any) -> list[float]:
        out = []
        if isinstance(p, Mapping):
            for k, v in p.items():
                lk = k.lower() if isinstance(k, str) else ""
                if (
                    "pce_fraction" in lk
                    and isinstance(v, (int, float))
                    and not isinstance(v, bool)
                ):
                    out.append(float(v))
                elif (
                    "pce_fraction" in lk
                    and isinstance(v, Mapping)
                    and "value" in v
                ):
                    val = v.get("value")
                    if isinstance(val, (int, float)) and not isinstance(val, bool):
                        out.append(float(val))
                else:
                    out.extend(_walk(v))
        elif isinstance(p, (list, tuple)):
            for item in p:
                out.extend(_walk(item))
        return out

    bad = [v for v in _walk(payload) if not (0.0 <= v <= 1.0)]
    if bad:
        return [
            FailureRecord(
                gate_id="pv_pce_fraction_range",
                severity="fail",
                message=f"PCE fraction outside [0, 1]: {bad}",
            )
        ]
    return None


# ---------------------------------------------------------------------------
# Battery SoC range (T10)
# ---------------------------------------------------------------------------


def soc_range_falsifier(env: UniversalLayerEnvelope) -> list[FailureRecord] | None:
    payload = env.outputs.payload or {}
    soc = payload.get("soc")
    if soc is None:
        return None
    if not (0.0 <= soc <= 1.0):
        return [
            FailureRecord(
                gate_id="soc_range_check",
                severity="fail",
                message=f"SoC={soc} outside [0,1]; battery state-of-charge is a fraction.",
            )
        ]
    return None


# ---------------------------------------------------------------------------
# IMAS DD-version (T11)
# ---------------------------------------------------------------------------


def imas_version_falsifier(env: UniversalLayerEnvelope) -> list[FailureRecord] | None:
    payload = env.outputs.payload or {}
    if not payload.get("imas_ids"):
        return None
    ids_block = payload["imas_ids"]
    if not isinstance(ids_block, Mapping) or "data_dictionary_version" not in ids_block:
        return [
            FailureRecord(
                gate_id="imas_version_required",
                severity="fail",
                message="IMAS IDS payload missing `data_dictionary_version`.",
            )
        ]
    return None


# ---------------------------------------------------------------------------
# Cross-model disagreement (T12)
# ---------------------------------------------------------------------------


def cross_model_disagreement_falsifier(env: UniversalLayerEnvelope) -> list[FailureRecord] | None:
    cmd = env.falsification.cross_model_disagreement
    if not cmd:
        return None
    status = cmd.get("status", "")
    if status in ("fail", "quarantine"):
        sev = "fail" if status == "fail" else "critical"
        return [
            FailureRecord(
                gate_id="cross_model_disagreement_fail",
                severity=sev,
                message=(
                    f"cross_model_disagreement.status='{status}' — downstream blocked. "
                    "Per PRD: never average away a failed disagreement."
                ),
            )
        ]
    return None


# ---------------------------------------------------------------------------
# DEFAULT SET — applied centrally
# ---------------------------------------------------------------------------


DEFAULT_FALSIFIER_SET: tuple[Falsifier, ...] = (
    boundary_falsifier,
    stub_scientific_valid_falsifier,
    license_promotion_falsifier,
    gpl_isolation_falsifier,
    units_recursive_falsifier,
    negative_te_falsifier,
    negative_ne_falsifier,
    above_carnot_falsifier,
    soc_range_falsifier,
    pv_fill_factor_falsifier,
    pce_fraction_falsifier,
    imas_version_falsifier,
    cross_model_disagreement_falsifier,
)


def apply_default_falsifiers(env: UniversalLayerEnvelope) -> UniversalLayerEnvelope:
    """Run every production falsifier; return envelope with updated falsification block."""
    return run_router(env, DEFAULT_FALSIFIER_SET)


def apply_dro_falsifiers(dro: DeviceResponseObject) -> list[FailureRecord]:
    """Return DRO-side failures (e.g. COCOS unit). DROs do not have a falsification
    block, so we return the failure list for the caller to attach to the parent envelope.
    """
    failures: list[FailureRecord] = []
    cocos = cocos_unit_falsifier_dro(dro)
    if cocos:
        failures.extend(cocos)
    return failures
