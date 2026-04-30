# ADR 003 — Falsification Wave: 12-Negative-Case Gate

**Status:** Active  
**PRD reference:** §Falsification Framework, §Architecture Invariants (UniversalLayerEnvelope)  
**Date:** 2026-04-30  

---

## Context

The Zer0pa Energy pipeline must not emit any result that is physically absurd, legally incoherent, or methodologically compromised.  A falsification wave — 12 negative cases that must each be explicitly blocked or quarantined — is the acceptance gate before any research artifact is promoted toward an L5/L6 optimization or published result.

The PRD states: *"Any output without units, uncertainty, source manifest, and falsifier status is invalid."*  
And: *"Never average away a failed disagreement."*

---

## Decision

Implement a 12-test falsification wave.  The wave PASSES only if every bad case is blocked by the mechanism listed below.  All 12 tests must be green before a pipeline release is approved.

---

## The 12 Negative Cases

| # | Test ID | Bad case | Blocking mechanism | Gate / error type |
|---|---------|----------|--------------------|-------------------|
| T1 | `test_t1_boundary_mutation` | One byte of `BOUNDARY_BLOCK` replaced in an envelope | `UniversalLayerEnvelope._boundary_byte_identical` field_validator | `ValidationError` |
| T2 | `test_t2_license_promotion_blocked` | `license_class=D`, `mode=scientific`, `license_evidence_uri=""` | `UniversalLayerEnvelope._class_cde_promotion_gate` model_validator | `ValidationError` |
| T3 | `test_t3_stub_scientific_valid_blocked` | `mode=engineering_stub` with `scientific_valid=True` | `UniversalLayerEnvelope._stub_cannot_be_scientific_valid` model_validator | `ValidationError` |
| T4 | `test_t4_unit_omission` | Output `quantities[k]` dict with `value` but no `unit` | `units_required_falsifier` in `l6.router` | `FailureRecord(gate_id="units_required")`, `gate_status=fail` |
| T5 | `test_t5_bad_coordinate_convention` | DRO `operating_conditions` axis `name="psi"` with empty `unit` | `_cocos_unit_falsifier` (inline, test file) | `FailureRecord(gate_id="cocos_unit_required")` |
| T6 | `test_t6_negative_temperature` | Fusion payload `T_e_eV=-1.0` | `_negative_te_falsifier` (inline, test file) | `FailureRecord(gate_id="negative_temperature", severity="critical")` |
| T7 | `test_t7_negative_density` | Fusion payload `n_e_m3<0` | `_negative_ne_falsifier` (inline, test file) | `FailureRecord(gate_id="negative_density", severity="critical")` |
| T8 | `test_t8_pv_fill_factor_above_one` | `ScalarMetrics.fill_factor=1.2` | `ScalarMetrics._zero_one` field_validator (DRO schema) | `ValidationError` |
| T9 | `test_t9_thermoelectric_above_carnot` | Efficiency=0.9, T_h=400 K, T_c=300 K (Carnot=0.25) | `_above_carnot_falsifier` (inline, test file) | `FailureRecord(gate_id="above_carnot_efficiency", severity="critical")` |
| T10 | `test_t10_battery_soc_outside_range` | Battery `soc=1.2` | `_soc_range_falsifier` (inline, test file) | `FailureRecord(gate_id="soc_range_check")` |
| T11 | `test_t11_fusion_missing_imas_version` | IMAS-shaped payload without `data_dictionary_version` | `_imas_version_falsifier` (inline, test file) | `FailureRecord(gate_id="imas_version_required")` |
| T12 | `test_t12_cross_model_disagreement_fail` | `CrossModelDisagreementRecord` values=[1.0,2.0], fail_threshold=0.5 → status=fail | `_cross_model_disagreement_falsifier` via `l6.router.run()` | `gate_status=fail`, `FailureRecord(gate_id="cross_model_disagreement_fail")` |

---

## Principle Behind Each Case

**T1 — Boundary integrity:** The boundary block is the pipeline's operator-policy anchor. Any mutation — even one byte — invalidates the artifact chain. Byte-identical comparison is the correct check; string normalisation would hide tampering.

**T2 — License promotion:** Class C/D/E code (GPL, LGPL, AGPL, proprietary) cannot enter `scientific` mode without an explicit license-grant evidence URI. Promotion without evidence exposes the operator to IP liability.

**T3 — Stub scientific validity:** An engineering stub cannot be marked `scientific_valid=true`. Stubs may satisfy engineering acceptance gates only; scientific promotion requires the full L1–L4 real computation chain.

**T4 — Unit omission:** Any quantity without a unit is not a physical measurement. Downstream optimisation (PyPSA, pvlib) will silently produce wrong results if units are missing. The falsifier makes unit presence a hard gate.

**T5 — Coordinate convention:** Fusion operating_conditions axes must carry SI units (e.g. `Wb` for poloidal flux ψ). Without the unit, COCOS coordinate transforms (Sauter & Medvedev 2013) are undefined.

**T6 — Negative temperature:** Electron temperature T_e < 0 eV is non-physical. Third law of thermodynamics: temperatures are absolute. Negative T_e in a payload signals a unit conversion error (e.g. Celsius subtracted without offset) or a sign bug.

**T7 — Negative density:** Particle density n_e < 0 is non-physical. A negative density will produce imaginary plasma frequencies, breaking all downstream transport calculations.

**T8 — Fill factor range:** Photovoltaic fill factor is defined as FF = (V_mp × J_mp) / (V_oc × J_sc) ∈ [0,1]. Values > 1 violate the definition; they typically indicate incorrect normalisation or unit confusion (mA vs A).

**T9 — Carnot limit:** No heat engine operating between T_h and T_c can exceed η_C = 1 - T_c/T_h (Kelvin statement of the second law). Efficiency 0.9 with η_C = 0.25 is a factor-of-3.6 violation. This catches surrogate model extrapolation outside training distribution.

**T10 — State of charge range:** Battery SoC is a fraction ∈ [0,1]. SoC > 1 indicates overcharge beyond rated capacity — physically impossible in a correctly modelled cell and a sign of integration or normalisation error.

**T11 — IMAS IDS version:** Every IMAS Interface Data Structure must carry a `data_dictionary_version` at its root (ITER standard, ITER_D_7LKQCT). Without the version, the IDS schema cannot be validated against the correct DD version and downstream IMAS tools will reject the file silently or use the wrong schema.

**T12 — Cross-model disagreement blocking:** The PRD states explicitly: *"fail blocks downstream L5 and L6 optimization. Never average away a failed disagreement."* A disagreement ratio of 1.0 (values 1.0 vs 2.0) against a fail_threshold of 0.5 is an unambiguous fail. The router must propagate this to `gate_status=fail` before any L5 handoff.

---

## TDA Early-Warning Design Decisions

- **CPU path only:** ripser + persim. No giotto-tda (AGPL). No GUDHI (requires module-level license whitelist per PRD).
- **Takens embedding:** delay-coordinate reconstruction per Takens (1981). Embedding dimension and delay set per domain from primary literature.
- **Persistence entropy:** H = -∑(l_i/L)·log(l_i/L) over finite H1 lifetimes. Formula from Atienza et al. (2020).
- **No-leakage guards:** Three guards (temporal, pulse-level, normalisation) prevent train→test contamination in TDA-based disruption models.
- **Performance target:** <2 s per 1024-sample window with embedding_dim=3 (observed ~0.9 s on Apple M-series).

---

## Consequences

- The 12 tests in `tests/falsification/test_falsification_wave.py` are the acceptance gate for every pipeline release.
- Inline falsifiers (T5–T12) are test-local; production equivalents will be promoted to `energy_pipeline/l6/falsifiers/` when the corresponding domain adapter is built.
- `EarlyWarningSignal` (from `schemas/falsification.py`) is the canonical TDA output; no scalar classifier alone may substitute it.
