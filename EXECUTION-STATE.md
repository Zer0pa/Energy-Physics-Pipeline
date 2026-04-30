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

Operator paused after Wave 1 with the question: "have you done absolutely everything that can be done without a GPU?" The honest answer is **no** — there is meaningful CPU-side work remaining. See `NEXT-WAVE-PLAN.md`. Newly installed during the pre-pause audit: PyBOP 26.3, Pyrokinetics 0.8.0, OMAS 0.95.2, qiskit 2.4.1. Did not install on Python 3.13 darwin (deferred to Runpod-Linux): mace-torch, fairchem-core, botorch, ax-platform — all blocked by torch having no 3.13-darwin-arm wheel yet.

Wakeup scheduled for ~1h (system clamp at 3600s; user requested 2h, will re-schedule on first wake). On wake: read `NEXT-WAVE-PLAN.md`, execute Waves A→D in order, commit + push, then re-evaluate.

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
