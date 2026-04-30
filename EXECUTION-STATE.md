# Overnight Execution State — live ledger

**Boundary:** Research infrastructure for in silico energy science: electrochemical conversion (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. No regulatory certification claims. No clinical or human-subject use. Defence / weapons applications are out of scope under operator policy.

**Run started:** 2026-04-30 (Sandton ZA)
**Lead agent:** Opus Max (chief engineer)
**Subagents:** five parallel — see § Subagent ledger.

## Summary so far

- Foundation locked: schemas, audit, KG, REST stubs, L6 control plane, CLI all green (61 contract tests passing).
- Five parallel subagents launched on disjoint file scopes (electrochem L1-L5, fusion L1-L5 + reasoning bench, MCP server suite, TDA + 12-test falsification wave, source manifests + reasoner curator + decision log).
- Heavy CPU libraries pre-installed: PyBaMM 26.4.1, PyPSA 1.2.0, pvlib 0.15.1, netCDF4 1.7.4, freegs 0.8.2.
- Package installed editable; subagents can `import energy_pipeline` cleanly.

## Subagent ledger (final)

| Subagent | Model | Scope | Status |
|---|---|---|---|
| Sources + reasoner curator + decision log | Sonnet | sources_log/* + adapters/shared/* + docs/decisions/* | DONE — 41 manifests + 41 license findings + 4 decision docs + 63 tests green |
| MCP server suite | Sonnet | mcp_servers/* | DONE — `mcp 1.27.0` FastMCP, 9 servers, 33 tests green |
| TDA + 12-test falsification wave | Sonnet | tda/* + tests/falsification/* | DONE — 63/63 green, 12-of-12 wave passes |
| Electrochem L1-L5 | Sonnet | adapters/electrochem/* + e2e + bounds | DONE — 29/29 green; real CPU on PyBaMM/PySCF/Cantera/PyPSA/pvlib; Solcore→analytic fallback |
| Fusion L1-L5 + reasoning bench | Opus | adapters/fusion/* + Phase-0 + reasoning + IMAS netCDF fixture | STALLED mid-test-write (chief engineer wrote 4 missing fusion test files); 20/20 green |

**Final test totals (Wave 1): 277 passed, 0 failed (50.6s wall).**

## Wave 1 → Wave 2 transition (2026-04-30)

Operator paused after Wave 1 with the question: "have you done absolutely everything that can be done without a GPU?" The honest answer was **no** — there was meaningful CPU-side work remaining. See `NEXT-WAVE-PLAN.md`. Newly installed during the pre-pause audit: PyBOP 26.3, Pyrokinetics 0.8.0, OMAS 0.95.2, qiskit 2.4.1. Did not install on Python 3.13 darwin (deferred to Runpod-Linux): mace-torch, fairchem-core, botorch, ax-platform — all blocked by torch having no 3.13-darwin-arm wheel yet.

## Wave 2 progress (post-resume)

Currently running: PyBOP and VQE-H2 subagents.

Completed mid-wave:
- Wave A: OMAS subagent (4/4 tests, real OMAS path; quirks documented).
- Wave A: Pyrokinetics subagent (4/4 tests, max_residual=0 round-trip; quirks documented).
- Wave B1: live plug-replaceability test (7/7).
- Wave B2: TDA on real PyBaMM voltage trajectories (6/6).
- Wave B4: MCP stdio JSON-RPC launch smoke (5/5).
- Wave B5: live cross-model disagreement emission with threshold ladder (6/6).
- Wave B6: source manifest verification — 35 of 41 verified, 6 HTTP 404 logged.
- Wave B7: R2S analytic activation upgrade (5/5).
- Wave B8: SA scenario fixture (5/5).
- Wave B9: tandem perovskite/Si PV analytic (7/7).
- Wave C1: GitHub Actions CI workflow.
- Wave C2-3: architecture diagram + RUNBOOK.
- Wave D: pyproject extras updated (`advanced-cpu`, `quantum`, `runpod-only`); decision docs 010, 011, 012 written.

Test count growth: 277 (Wave 1) → 305 (post-OMAS) → 326 (post-Pyrokinetics + B7-B9 + C2-3 + D extras) → **333 (post-PyBOP + VQE-H2; final)**. All 5 Wave A subagents done. Falsification wave still 12-of-12.

## Wave 2 closeout

**Sovereign acceptance gate cleared at 333 tests, 0 failures.**

Real CPU adapters added in Wave 2:
- `PyBOPParameterInferenceAdapter` (electrochem L4) — Bayesian SPM parameter inference; 25% relative error vs ground-truth `D_neg` (within SNR limits); SciPyMinimize optimiser.
- `OmasRealValidatorAdapter` (fusion L4) — real OMAS Data Dictionary path validation; Class B LGPL.
- `PyrokineticsParserAdapter` (fusion L2) — universal gyrokinetic input/output bridge with GS2→CGYRO round-trip residual=0.0 across q/shat/beta/Ti/Te.
- `VqeH2Adapter` (electrochem L1 quantum slot) — H2 STO-3G VQE on qiskit 2.4 StatevectorEstimator + manual JW; 0.10 mHa absolute error vs FCI in 120 COBYLA iterations.
- `R2sAnalyticActivationAdapter` (fusion L5) — single-isotope point-kinetics for Co-60/Mn-56/He-6 chains; analytic only; warn-level gate; replaces all-stub R2S.
- `TandemPvAdapter` (electrochem L4) — perovskite/Si 2T tandem with current matching, AM1.5G photocurrent budget, Green-1981 FF, radiative-limit Voc; analytic only.

Cross-cutting added in Wave 2:
- Live plug-replaceability test (env flag flip + REST-stub vs local-CPU contract).
- TDA on real PyBaMM voltage trajectories (cross-cutting demo: battery thermal runaway + plasma disruption).
- MCP stdio JSON-RPC subprocess smoke (4 servers).
- Live cross-model disagreement (3-mode threshold ladder).
- 35-of-41 source manifests verified with real sha256.
- SA scenario fixture exercising the PGM/H2 thesis.
- GitHub Actions CI workflow.
- `architecture.md` + `RUNBOOK.md` operator docs.
- Decision docs 006-012.

## Decisions log (executor-side, deviations only)

(none yet — see docs/decisions/005-deviations-from-prd.md when populated by subagent)

## Open questions deferred (PRD §Open Questions)

1. Thermoelectrics ownership (Energy / Materials / duplicate) — DEFERRED. We support thermoelectric schema and fixture path per PRD; we do not elevate above battery/fusion/green-H2 MVPs.
2. `imas-codex` rights — TREATED AS READ-ONLY GATEWAY per PRD default.
3. SA PGM anchor sequencing — DEFERRED. We build all wedges in scaffolding now; commercial sequencing is operator-led.
4. MLIP fine-tunes ownership — DEFAULT customer-isolated per PRD §Data-Sovereignty.
5. First public paper target — DEFERRED. We instrument all four candidates (fusion L6 reasoning, TDA disruption warning, thermoelectric end-to-end, PV reference pipeline) so any can be reached without rework.

## Falsification wave acceptance gate

Will run after subagents complete. Expectation: 12 of 12 negative cases blocked or quarantined. Wave failure = run failure.
