# Zer0pa Energy — Workstream Repository

Canonical home for the Zer0pa Energy work stream. Multi-agent handoff: synthesis → orchestrator → overnight executor → Runpod migration. Repo is the source of truth across machines.

## Boundary

Research infrastructure for in silico energy science: electrochemical conversion (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. No regulatory certification claims. No clinical or human-subject use. Defence / weapons applications excluded under operator policy.

## Two sub-verticals, one workstream

Energy spans two physically distinct sub-verticals that share the six-layer scale hierarchy and L6 orchestration spine:

- **Electrochemical** — Butler-Volmer master equation; polarisation curve V(j) is the device-response token; buyers exist today (battery digital twins, PEM catalyst screening, perovskite PV); SA PGM strategic anchor.
- **Fusion / plasma** — Grad-Shafranov equilibrium + gyrokinetic Vlasov-Maxwell master equations; plasma equilibrium state vector is the device-response token; first commercial window (IMAS open-sourced December 2025); IMAS-MCP enables LLM agentic interface (April 2026).

The orchestrator's working assumption per the research-agent handover note: **one PRD with Part A (electrochemistry) and Part B (fusion) sharing the L6 spine**. Within Energy, sharing is permitted and recommended. Across workstreams (Health, Materials, Energy), no substrate is shared — see § Parallel-exploration principle in `MODUS-OPERANDI.md`.

## What is in here

| Path | Purpose | Author role |
|---|---|---|
| `MODUS-OPERANDI.md` | Reusable multi-agent pattern + parallel-exploration principle (Health, Materials, Energy run independently in parallel; convergence happens after all complete, not during) | Synthesis agent |
| `HANDOFF-TO-ORCHESTRATOR.md` | Energy-specific brief for the next agent (the energy orchestrator) — defines what they inherit and what they must produce | Synthesis agent |
| `ORCHESTRATOR-STARTUP-PROMPT.md` | The exact prompt the user pastes into a fresh agent session to spin up the energy orchestrator | Synthesis agent |
| `source-briefs/` | Inherited research input — the research-agent handover note plus two technology-landscape briefs (electrochemical M2S; fusion + SA + LLM + data standards) | External (consumer of synthesis) |
| `synthesis/` | Fresh-eyes reading of the briefs and handover note — what is not yet seen, the information-theoretic foundation reframe, the unified L4 device-response object, twelve specific things the briefs do not see | Synthesis agent |
| `PRD.md` (to be written) | The PRD that drives the overnight long-horizon execution on a Runpod-bound machine | Energy orchestrator |

## Read order for the next agent

1. `MODUS-OPERANDI.md` — how the role chain works and why these workstreams stay independent.
2. `HANDOFF-TO-ORCHESTRATOR.md` — what you (energy orchestrator) inherit and produce.
3. `source-briefs/00-research-agent-handover-note.md` — the prior research agent's self-assessment, best-of-breed picks per layer for both sub-verticals, five first-of-kind opportunities, license risk flags, priority build order, the one decision flagged for you.
4. `source-briefs/01-electrochemical-m2s-pipeline.md` — Brief #1 — full six-layer M2S pipeline for batteries, electrolysers, fuel cells, PV, thermoelectrics.
5. `source-briefs/02-fusion-sa-llm-data-standards.md` — Brief #2 — fusion / plasma six-layer pipeline; SA PGM context; electrochemistry reasoning LLMs; battery data standards.
6. `synthesis/01-fresh-eyes-on-energy-briefs.md` — synthesis-agent reframe; this is the substrate for your own fresh-eyes augmentation.

## Provenance

- Initial commit: 2026-04-30.
- Research agent: Perplexity (electrochemical M2S brief; fusion second-pass brief; handover note).
- Synthesis agent: Claude Opus 4.7 (1M context), 2026-04-30.
- Next agent: energy orchestrator (writes `PRD.md`).
- Following: overnight executor on a Runpod-bound machine.

## Cross-workstream principle (deliberate)

This workstream runs in parallel with `Zer0pa/Health` and `Zer0pa/Materials`. Each workstream is built end-to-end as an independent pipeline. **No substrate is shared during build.** Redundancy across workstreams is a deliberate asset — surplus coding capacity buys diversity of architecture, not duplicated cost. Convergence (if any) happens in a separate merge step after all parallel workstreams complete. See `MODUS-OPERANDI.md` § Parallel-exploration principle. The research-agent handover note recommends cross-vertical L6 sharing across Health, Materials, and Energy; that recommendation is captured in `synthesis/01-fresh-eyes-on-energy-briefs.md` and explicitly overridden in `HANDOFF-TO-ORCHESTRATOR.md` § Operator override. Within Energy, the two sub-verticals (electrochemistry + fusion) may share L6 design and the L4-output schema — that is intra-workstream and explicitly permitted.

---

## Executor build state (2026-04-30)

Overnight CPU-first build delivered. See [`FINAL-REPORT.md`](./FINAL-REPORT.md) and [`HANDOFF-FROM-OVERNIGHT-EXECUTOR.md`](./HANDOFF-FROM-OVERNIGHT-EXECUTOR.md).

Repo layout (post-build):

```
energy_pipeline/
  schemas/                — UniversalLayerEnvelope, DeviceResponseObject, Falsification, Source, Reasoner
  audit/                  — JSONL + DuckDB writer with mandatory boundary check
  kg/                     — JSONL + NetworkX KG store; GraphML export
  rest/                   — FastAPI stubs for L1-L5 endpoints (electrochem + fusion)
  l6/                     — Adapter registry, ENERGY_* config, falsifier router
  tda/                    — Persistent-homology early-warning (ripser + persim)
  cli/                    — Typer CLI: health, registry, smoke, serve-rest, falsification-wave, etc.
  adapters/electrochem/   — L1-L5 (PyBaMM, Solcore, Cantera, PEM, ThermoElectric)
  adapters/fusion/        — L1-L5 (OpenMC, GACODE/TGLF, FreeGS4E, IMAS netCDF, Paramak)
  adapters/shared/        — Source log + license gate + reasoner curator
  mcp_servers/            — 9 FastMCP servers (pybamm, pvlib, solcore, cantera, pypsa, pysam, openmc, imas-codex, aiida)
fixtures/{electrochem,fusion,negative}/
tests/{contract,falsification,scientific,integration}/
sources_log/seed.jsonl + license_findings.jsonl
docs/decisions/000-005
scripts/{full_check.sh, clean_runtime.sh, quick_demo.py}
tools/{show_audit.py, show_kg.py, build_summary.py, runpod_cutover_checklist.py}
```

Quick start:

```bash
git clone https://github.com/Zer0pa/Energy
cd Energy
python3.13 -m venv .venv
.venv/bin/pip install -e '.[test,electrochem,fusion,tda,mcp]'
make full
```

The Runpod cutover plan is `tools/runpod_cutover_checklist.py` and the `/v1/runpod/{layer}/{domain}` REST shape in `energy_pipeline/rest/app.py`.
