# ADR 007 — OMAS Integration: Real IMAS Data Dictionary Path Validation at L4

**Status:** Active  
**Date:** 2026-04-30  
**Source:** PRD §"Part B - Fusion / Plasma Contracts" §L4; `energy_pipeline/adapters/fusion/l4_omas.py`

---

## Boundary Block

> Research infrastructure for in silico energy science: electrochemical conversion
> (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics,
> thermoelectrics) and fusion / plasma physics. Outputs are research artifacts.
> No regulatory certification claims. No clinical or human-subject use.
> Defence / weapons applications are out of scope under operator policy.

---

## Context

PRD §"Part B - Fusion / Plasma Contracts" §L4 mandates that the fusion L4 layer
validate IMAS-compliant data against a Data Dictionary (DD) before passing
results to the L4 scenario solvers or the L4→L5 handoff (`DeviceResponseObject`).

The existing `OmasConverterAdapter` (in `l4.py`) satisfies this requirement with
a **pure-Python path-string validator**: it walks a nested Python dict and checks
that hard-coded canonical path strings are present as keys.  This approach works
for the IMAS fixture (a dict produced by `imas_fixture.write_fixture`) but has a
critical limitation: it cannot distinguish between a correctly-spelled path that
happens to be absent from the fixture and a misspelled or non-existent IMAS path.
Both cases look the same — a missing key.

OMAS (Open IMAS Access System, `gafusion/omas`) ships the full IMAS Data
Dictionary (DD) as embedded JSON structures and exposes two complementary APIs
that make genuine path verification possible:

1. `omas.omas_info_node(dd_path)` — queries the embedded DD JSON directly and
   returns a metadata dict (containing `data_type`, `units`, `documentation`,
   etc.) for any valid leaf node, or an empty dict `{}` for any path that does
   not exist in the DD.  This operates without constructing an ODS instance and
   is therefore cheap and deterministic.

2. `ods[user_path] = value` — a live `ODS()` instance enforces DD compliance at
   assignment time; it raises `LookupError` immediately for any path that does
   not exist in the DD version the ODS was initialised with (default 3.41.0).

---

## Decision

Add `OmasRealValidatorAdapter` (in `energy_pipeline/adapters/fusion/l4_omas.py`)
alongside the existing `OmasConverterAdapter`.  The new adapter:

1. Calls `check_fusion_intent(spec.intent)` on every input and raises
   `BoundaryViolation` if a forbidden term is matched — identical pre-flight
   policy as every other L4 adapter.

2. Imports `omas` at runtime.  If OMAS is absent (e.g. a stripped deployment
   image) it degrades gracefully to a structural string-pattern check and emits
   `mode=engineering_stub` so the caller can see the reduced confidence level.

3. On the real path, for each path in `spec.ods_paths`:
   - Converts integer array indices (e.g. `time_slice.0`) to `:` and calls
     `omas.omas_info_node` to confirm the path exists in the IMAS DD.
   - Writes a physically representative sample value to a live `ODS()` instance
     to confirm the path is also writable (not just present as DD metadata).
   - Both checks must pass for the path to be recorded as `valid`.
   - Any invalid path appends a `FailureRecord(gate_id="omas.path_invalid",
     severity="fail", ...)` and sets `gate_status=fail`.

4. Emits `mode=scientific` and `scientific_valid=True` only when OMAS is
   available and all paths pass — enforcing the PRD prohibition on stubs
   claiming scientific validity.

5. Records `license_evidence_uri="https://github.com/gafusion/omas/blob/master/LICENSE"`
   (MIT — License Class A), which satisfies the `_class_cde_promotion_gate`
   for class-A tools without requiring a kg://license-grant node.

---

## Why OMAS Adds Value Beyond the netCDF Fixture

| Capability | netCDF fixture + string walker | OMAS real path |
|---|---|---|
| Reads real plasma profile data | Yes (via `imas_fixture`) | Yes (via `ODS`) |
| Validates DD path existence | **No** — only checks keys in fixture dict | **Yes** — queries embedded DD JSON |
| Rejects misspelled paths | **No** — missing key = absent path, no error | **Yes** — `LookupError` on write, empty dict on `omas_info_node` |
| Returns DD metadata (units, data\_type) | No | Yes |
| DD version traceability | Via fixture attribute only | Explicit `imas_version` on `ODS` |
| Works without a fixture file | No | Yes |

The core gap is **canonicalisation**.  The netCDF fixture is one particular
instantiation of IMAS paths.  A path string like
`core_profiles.profiles_1d.0.electrons.densty` (note typo) will pass the string
walker if it simply isn't in the fixture dict — the walker treats absence as
"missing but structurally valid."  OMAS treats it as a `LookupError` because the
IMAS DD 3.41.0 JSON has no entry for that leaf.  Without OMAS, path-string
validation is unverified against the authoritative DD; with OMAS, we know the
paths exist in the IMAS Data Dictionary and are of the correct data type and
physical units.

---

## Validation Protocol (per PRD §L4)

The four canonical paths validated by `OmasValidateSpec` cover the physics
observables required for the L4→L5 handoff:

| Path | DD data\_type | Units | Physics role |
|---|---|---|---|
| `equilibrium.time_slice.0.global_quantities.q_axis` | FLT\_0D | — | Safety factor on axis |
| `equilibrium.time_slice.0.profiles_1d.q` | FLT\_1D | — | Full q profile (radial) |
| `core_profiles.profiles_1d.0.electrons.density` | FLT\_1D | m⁻³ | Electron density profile |
| `core_profiles.profiles_1d.0.electrons.temperature` | FLT\_1D | eV | Electron temperature profile |

These four paths are the minimum required by the L4 IMAS contract before a
`TokamakScenarioSpec` can be constructed with scientifically meaningful inputs.

---

## OMAS API Quirks Observed (version 0.95.2)

* `omas.imas_versions` is a non-callable `IMAS_versions` mapping object, not a
  function — calling it raises `TypeError`.  The adapter reads DD version from
  `ODS().imas_version` instead.
* `omas_info_node` returns `{}` (empty dict) for unknown paths rather than raising
  an exception — callers must check for the presence of `data_type`.
* Integer array-of-structures indices (e.g. `time_slice.0`) must be replaced by
  `:` before querying `omas_info_node` because the DD uses colon-wildcard notation
  for array dimensions.  `ODS[user_path]` accepts integer indices directly.
* OMAS is chatty on import (prints to stdout on first call in some configurations);
  the adapter wraps the import in a bare `try/except ImportError`.

---

## Consequences

* The test suite gains four focused integration tests in
  `tests/integration/test_omas_validation.py` that run in < 3 seconds on CPU.
* The `OmasConverterAdapter` in `l4.py` is **not** modified; it remains as the
  fixture-mode fallback for environments where OMAS is not installed.
* `OmasRealValidatorAdapter` is the promoted L4 path validator for all
  environments where OMAS 0.95.2+ is available.
* Downstream L4 callers should prefer `OmasRealValidatorAdapter` when they need
  `scientific_valid=True`; the fixture adapter remains available for stub-mode
  environments.

---

## References

* [gafusion/omas](https://github.com/gafusion/omas) — OMAS source (MIT License)
* [IMAS Data Dictionary 3.41.0](https://github.com/iterorganization/IMAS-Data-Dictionary) — ITER IMAS DD
* PRD §"Part B - Fusion / Plasma Contracts" §L4 — L4 IMAS validation contract
* `energy_pipeline/adapters/fusion/l4.py` — existing `OmasConverterAdapter` (path-string stub)
* `energy_pipeline/adapters/fusion/imas_fixture.py` — netCDF fixture writer/reader
* ADR 001 — License Policy (OMAS: MIT = Class A; no promotion gate required)
