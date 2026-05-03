# Next Wave — CPU-side completion plan (pre-Runpod)

**Boundary:** Research infrastructure for in silico energy science: electrochemical conversion (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. No regulatory certification claims. No clinical or human-subject use. Defence / weapons applications are out of scope under operator policy.

**Status at pause:** 2026-04-30; commit `b8eb19b` on `main`; 277 tests green; foundation + 5 subagent waves complete and pushed. Allocation throttle requires 2-hour pause (operator instruction).

**Context lost across pause is recoverable from this file + git state. Read this first on resume, then re-read `FINAL-REPORT.md` and `HANDOFF-FROM-OVERNIGHT-EXECUTOR.md`.**

## Honest gap audit — what is left CPU-side

Several CPU-feasible adapters still ship as stubs because they were not on the first-wave subagent allocation. The Runpod cutover should be a config-flag flip, but right now the Runpod-side will inherit our analytic / manifest-only paths for several layers where a real CPU library exists.

### Newly-installed packages that need integration

These were installed during the audit just before the pause; they are present in `.venv/` and ready to wire:

| Package | Version | What it unlocks | Layer |
|---|---|---|---|
| `pybop` | 26.3 | Bayesian battery parameter inference; the L4-revenue MVP per PRD priority order | electrochem L4 |
| `pyrokinetics` | 0.8.0 | Gyrokinetic input/output adapter, the universal parser between TGLF/CGYRO/GENE | fusion L2 |
| `omas` | 0.95.2 | IMAS path validators in pure Python beyond our netCDF fixture | fusion L4 |
| `qiskit` | 2.4.1 | PRD quantum slot — tiny VQE smoke for H2/LiH on PySCF integrals | electrochem L1 |

### Packages that did NOT install on Python 3.13 darwin (Runpod-Linux gets them)

| Package | Reason | Fallback strategy |
|---|---|---|
| `mace-torch` | torch wheels not yet shipped for 3.13 darwin-arm | Stay manifest-only; Runpod-Linux can install. Add a CPU smoke that runs only when torch is importable. |
| `fairchem-core` | inherits torch dependency | Same. |
| `botorch` | inherits torch dependency | Use `scipy.optimize` with Gaussian-process surrogate as a lighter L6 active-learning loop until Runpod. |
| `ax-platform` | failed sklearn build | Same as botorch. |

## Comprehensive next-wave list (no GPU required)

### Wave A — Real adapter wiring on installed packages

A1. **PyBOP integration** (electrochem L4, real CPU)
   - New module `energy_physics_pipeline/adapters/electrochem/l4_pybop.py`.
   - Class `PyBOPParameterInferenceAdapter` wrapping the PyBaMM Chen2020 cell.
   - Inference target: a small subset of SPM parameters (positive-electrode-diffusivity, electrolyte-conductivity, etc.) given a synthetic CC discharge trajectory plus added Gaussian noise.
   - Emit envelope + DRO with the recovered posterior P5/P50/P95 in `scalar_metrics`.
   - Tests in `tests/integration/test_pybop_inference.py`: 200-step inference completes <60s; recovered posterior mean within ±20% of ground truth; envelope `mode=scientific`.
   - License A (BSD-3); add a `LicenseFinding` for PyBOP.

A2. **OMAS adapter** (fusion L4, real CPU)
   - Replace stub `OmasConverterAdapter` body with a real call to `omas.ODS()` + `omas.omas_validate(...)`.
   - Add `tests/integration/test_omas_validation.py` against our IMAS netCDF fixture.

A3. **Pyrokinetics adapter** (fusion L2, real CPU parser)
   - New module `energy_physics_pipeline/adapters/fusion/l2_pyrokinetics.py`.
   - Class `PyrokineticsParserAdapter` that round-trips a tiny GS2 / TGLF input deck through Pyrokinetics' `Pyro` object and emits an envelope.
   - Test: round-trip preserves reference values within numerical noise.

A4. **Quantum slot** (electrochem L1, real CPU)
   - New module `energy_physics_pipeline/adapters/electrochem/l1_quantum.py`.
   - Class `VqeH2Adapter` that builds the H2 Hamiltonian via PySCF integrals (already installed), maps to qubits via Jordan-Wigner, and runs a 4-qubit VQE with `qiskit.primitives` and `scipy.optimize.minimize`.
   - Acceptance: bond energy within 5% of FCI reference (-1.137 Ha at d=0.74 Å). Mark `mode=scientific` only if reference matched; PRD note says "no quantum advantage claims" — that constraint is honored, this is a smoke test.
   - Test in `tests/integration/test_vqe_h2.py`.

### Wave B — Cross-cutting CPU work

B1. **Live plug-replaceability integration test** — flip `ENERGY_L4_BACKEND` env var between `local_cpu` and `gpu_rest_stub`, run the same battery spec through both, assert `output_hash` invariance + envelope `schema_version` invariance + DRO `device_family` invariance. File `tests/integration/test_plug_replaceability_live.py`.

B2. **TDA on real PyBaMM trajectories** — engineer a synthetic thermal-runaway battery scenario from PyBaMM voltage data (impose a sudden internal-resistance jump at t=200s); run the cross-domain `battery_thermal_runaway` detector and assert a `warn` or `fail` `EarlyWarningSignal` is emitted. File `tests/integration/test_tda_pybamm_runaway.py`.

B3. **Cross-vertical TDA demo** — same test runs the plasma-disruption detector on a synthetic Hopf-bifurcation magnetic-fluctuation series. Demonstrates the cross-cutting capability.

B4. **MCP stdio launch smoke** — actually `subprocess.Popen` one of the MCP servers in stdio mode, send a `tools/list` JSON-RPC request, parse the response, assert tool count + boundary-block presence. File `tests/integration/test_mcp_stdio.py`.

B5. **Cross-model disagreement live emission** — during `tests/integration/test_fusion_phase0.py`, compare TGLF reduced output vs CGYRO stub vs GyroSwin stub for `Q_GB_ion`; emit `CrossModelDisagreementRecord` with thresholds 25%/50%; assert appropriate `status` per the synthetic divergences. Currently this only happens in falsification tests — wire it as a real artifact in the e2e path.

B6. **Source-manifest verification wave** — for each entry in `sources_log/seed.jsonl`, fetch the URL, compute real sha256 of the response body, update the entry from placeholder. File a new `tools/verify_sources.py`. Requires WebFetch (no GPU; allowed). Skip URLs that return 4xx/5xx; record verdict.

B7. **R2S analytic activation** (fusion L5) — replace `OpenmcR2sAdapter` stub with a simple ALARA-style analytic: given a tritium-breeding-layer geometry and an irradiation history, compute decay heat and contact dose with single-isotope decay constants. Document as research-only.

B8. **PyPSA-Earth SA scenario fixture** — tiny SA-specific generation/load fixture. Load it in the L5 PyPSA adapter as an alternative scenario. Demonstrates the SA-PGM hydrogen story end-to-end on synthetic data.

B9. **Tandem PV analytic** — Si + perovskite tandem; more ambitious than single-junction Shockley-Queisser. Replace the Solcore-fallback path with a tandem analytic that handles two-junction current matching.

### Wave C — Repository polish (no GPU)

C1. **CI workflow** — `.github/workflows/ci.yml` running `pytest -q tests/contract tests/falsification tests/scientific tests/integration` on push and PR. Use Python 3.13 on ubuntu-latest. Pin no heavy deps; install only `[test]` extras + the small `[tda]` extras.

C2. **Coverage report** — pytest-cov is already installed. Add `pytest --cov=energy_physics_pipeline --cov-report=xml` to a `make coverage` target. Don't enforce a threshold yet.

C3. **Architecture diagram** — `docs/architecture.md` with an ASCII / mermaid diagram of L1→L6 + the L4 DRO bridge between sub-verticals + the L6 falsifier router.

C4. **RUNBOOK.md** — operator manual: how to spin a campaign, which env flags to set, where audit/KG land, how to read DuckDB rows, how to export GraphML.

C5. **Clean remaining 13 ruff F841 unused-locals** — manually since `--unsafe-fixes` could change behavior in subagent code.

C6. **Coverage gates in pyproject.toml** — add a soft 80% coverage gate (warn-only).

### Wave D — Small-but-load-bearing things often forgotten

D1. **`docs/decisions/006-pybop-integration.md`** — record the decision to integrate PyBOP and the parameter subset chosen for inference.

D2. **`docs/decisions/007-quantum-slot-vqe.md`** — record the quantum-slot scope (H2 only; no quantum-advantage claim; CPU simulator only).

D3. **`docs/decisions/008-cpu-package-failures.md`** — record the torch-on-3.13-darwin gap and the fallback strategy.

D4. **Update `pyproject.toml`** optional extras: add `pybop`, `pyrokinetics`, `omas`, `qiskit` to a new `[advanced-cpu]` extra.

D5. **Update `tools/runpod_cutover_checklist.py`** to recognize the new adapter records.

D6. **Update `EXECUTION-STATE.md` and `FINAL-REPORT.md`** with the new metrics.

## Wakeup prompt (for `<<autonomous-loop-dynamic>>`)

Resume autonomous execution per `NEXT-WAVE-PLAN.md`. Do not ask questions; proceed through Waves A → B → C → D in order, gated only on real blockers (license, missing GPU). Keep the boundary block byte-identical in every artifact. Re-run the full pytest suite after each wave; commit + push at the end of every successful wave. Final state target: every CPU-feasible item in this file is shipped or explicitly marked impossible-on-3.13-darwin with the Runpod-Linux migration path documented.

## Acceptance for "absolutely everything CPU-side done"

The pipeline is CPU-side complete when:

- [x] Foundation, MCP, TDA, Sources, Electrochem, Fusion subagent waves shipped.
- [x] Wave A (4 real-CPU adapter integrations) shipped.
- [x] Wave B (9 cross-cutting items) shipped.
- [x] Wave C (6 polish items) shipped.
- [x] Wave D (6 small items) shipped.
- [x] Full pytest suite green (>=320 tests projected after Wave A+B). **Actual: 333 after Wave 2; 452 after Wave 3.**
- [x] Falsification wave still 12-of-12.
- [x] CI workflow runs green on a fresh ubuntu-latest checkout.
- [x] Source manifest sha256 placeholders replaced with real digests. **40 of 41; 1 demoted to non_authority.**
- [x] Plug-replaceability live test green.

All boxes flipped after Wave 2.

## Wave 3 — CPU hardening (added after team review of `wave2-cpu-complete`)

Team reviewer flagged 11 readiness gaps in `CPU-HARDENING-BRIEF.md`. All addressed:

- [x] **H1** Strict install/check path (no `|| true`)
- [x] **H2** Runpod backend resolver + `httpx.MockTransport` golden-fixture invariance test
- [x] **H3** Mandatory audit/KG via `accept_envelope` enforcement layer
- [x] **H4** Production falsifier module; default set applied centrally
- [x] **H5** Recursive unit enforcement on physical leaves
- [x] **H6** GPL Class B isolation gate; 14 promotion tests across all classes
- [x] **H7** Widened forbidden-intent matcher; 55 paraphrase tests
- [x] **H8** Source manifest cleanup (40 verified, 1 demoted)
- [x] **H9** MCP wrappers call real typed adapter APIs; `dispatch_path` reported
- [x] **H10** Parser/manifest adapters for CIF/xyz/SMILES + 12 tools
- [x] **H11** Reports rewritten to drop overclaim; this entry is the audit trail

Verdict: **READY FOR RUNPOD.**
