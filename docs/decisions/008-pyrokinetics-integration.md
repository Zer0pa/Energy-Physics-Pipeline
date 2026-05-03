# ADR 008 — Pyrokinetics Integration as L2 Universal Gyrokinetic Parser

```
BOUNDARY: Research infrastructure for in silico energy science: electrochemical conversion
(batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics,
thermoelectrics) and fusion / plasma physics. Outputs are research artifacts.
No regulatory certification claims. No clinical or human-subject use.
Defence / weapons applications are out of scope under operator policy.
```

**Status:** Accepted  
**Date:** 2026-04-30  
**Deciders:** Zer0pa Energy Pipeline architecture team  
**Refs:** PRD §"Part B - Fusion / Plasma Contracts" §L2; fusion handover note

---

## Context

The Zer0pa fusion L2 stack already carries three gyrokinetic adapters:

| Adapter | Backend | Mode | Notes |
|---|---|---|---|
| `TglfReducedAdapter` | Analytic reduced fixture | `engineering_stub` | CPU; gyroBohm roundtrip residual < 1e-8 |
| `CgyroNonlinearAdapter` | REST stub (Runpod-parked) | `engineering_stub` | GPU required; never `scientific_valid` |
| `GyroSwinSurrogateAdapter` | REST stub (Runpod-parked) | `engineering_stub` | Surrogate; placeholder calibration |

None of these adapters can **read** native gyrokinetic input decks from existing codes (GS2, GENE, GKW, Stella) or **convert** between formats.  Research campaigns that start from an experimental equilibrium and a pre-existing input deck have no on-ramp into the L2 stack.

The PRD §L2 handover note ranks **Pyrokinetics** as "the universal adapter" precisely because it bridges all major open-source gyrokinetic codes through a single Python interface.

---

## Decision

We integrate Pyrokinetics 0.8.0 as a **dynamically imported CPU-side adapter**:

- File: `energy_physics_pipeline/adapters/fusion/l2_pyrokinetics.py`
- Class: `PyrokineticsParserAdapter` (emits `UniversalLayerEnvelope`)
- Fixture: `fixtures/fusion/pyrokinetics_demo.gs2` (synthetic GS2 deck; q=1.5, shat=0.8, beta=0.005)
- Tests: `tests/integration/test_pyrokinetics_parser.py` (4 tests, all green in < 30 s)

### Round-trip falsifier

The adapter loads a GS2 input deck, converts it to CGYRO format, reloads the CGYRO file, and compares four parameters: **q, shat, beta, ti\_te**.

Beta normalisation: GS2 stores `beta_ref_ee_B0`; CGYRO stores `beta_ref_ee_Bunit`.  Before comparing, GS2 beta is converted:

```
beta_Bunit = beta_B0 / (bunit_over_b0)^2
```

This conversion is exact, so the round-trip residual for beta is 0.00e+00 on the demo fixture.

| Threshold | FailureRecord severity |
|---|---|
| max\_residual > 1e-6 | `warn` |
| max\_residual > 1e-3 | `fail` |

Only `mode=scientific` is emitted when max\_residual < 1e-3 **and** Pyrokinetics is importable.

---

## Why Pyrokinetics is the right choice

1. **Universal format coverage.** Pyrokinetics 0.8.0 reads GS2, GENE, CGYRO, TGLF, GKW, GX, and Stella — the full set of open-source codes in use at L2.

2. **CPU-only operation.** The parser does no time-stepping; it only reads and writes Fortran namelists.  No GPU is required.  Runpod inherits the adapter unchanged: the adapter runs on the Runpod CPU allocation before dispatching a full nonlinear CGYRO run to the GPU worker.

3. **LGPL-3 licensing.** Pyrokinetics is released under LGPL-3.  Dynamic import (`import pyrokinetics`) satisfies the LGPL-3 dynamic-linking clause without imposing LGPL-3 on downstream pipeline code.  License evidence URI: `https://github.com/pyro-kinetics/pyrokinetics`.  In the envelope this maps to `LicenseClass.B` (`license_evidence_uri` carries the upstream repo URL).

4. **Zero vendoring.** The adapter imports Pyrokinetics from the project venv; no source code is copied.  The demo fixture (`pyrokinetics_demo.gs2`) is a synthetic ~70-line Fortran namelist, not a derived reproduction of any upstream file.

5. **Graceful degradation.** If Pyrokinetics is absent (e.g. in a stripped Docker image), the adapter emits `mode=engineering_stub` with a `FailureRecord(gate_id="pyrokinetics.import", severity="warn")` rather than crashing.  The pipeline can still construct envelopes; upstream code decides whether to block on the stub.

---

## Consequences

**Accepted costs:**

- Pyrokinetics must be present in the venv for `mode=scientific` envelopes.  This is a deliberate soft-dependency; the adapter handles the missing-library case.
- The round-trip residual for beta is non-zero on codes that use different B-field normalisations (B0 vs Bunit).  The adapter converts to a common reference before computing residuals, making the check physically meaningful.

**Excluded scope:**

- This adapter does not run any gyrokinetic solver.  It is a **format bridge**, not a simulation.
- It does not replace `CgyroNonlinearAdapter` or `TglfReducedAdapter`; those remain the scientific simulation path.

---

## Alternatives considered

| Option | Rejected because |
|---|---|
| Hand-write GS2→CGYRO namelist converter | Would need to be maintained per-code; Pyrokinetics already does this |
| Use OMAS / IMAS as the interchange format | Adds a heavy dependency; OMAS round-trips are not validated against native formats in 0.8 |
| Defer until a GPU run is available | The universal parser is CPU-only and does not block on GPU availability |

---

## References

- Pyrokinetics GitHub: <https://github.com/pyro-kinetics/pyrokinetics>
- Pyrokinetics JOSS paper: <https://doi.org/10.21105/joss.05866>
- PRD §"Part B - Fusion / Plasma Contracts" §L2
- `energy_physics_pipeline/adapters/fusion/l2.py` (existing L2 adapters, frozen)
- `energy_physics_pipeline/boundary.py` (BOUNDARY_BLOCK definition)
