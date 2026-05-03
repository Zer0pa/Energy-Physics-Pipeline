# Handoff from Overnight Executor — Energy Physics Pipeline

> **Wave 4 closes the readiness gate.** Same-shape `/v1/<sub>/<layer>/<op>`
> endpoints honor `ENERGY_L?_BACKEND` end-to-end (live test:
> `tests/integration/test_runpod_same_endpoint.py`). Audit/KG is mandatory on
> every accepted REST + parser + adapter + MCP path. Audit/KG runtime is
> parallel-safe via `ENERGY_AUDIT_DIR` / `ENERGY_AUDIT_DB_PATH` / `ENERGY_KG_DIR`.
> Production falsifier set is 13 gates applied centrally. The Runpod
> migration role can proceed at the Wave 4 commit.

**Boundary:** Research infrastructure for in silico energy science: electrochemical conversion (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. No regulatory certification claims. No clinical or human-subject use. Defence / weapons applications are out of scope under operator policy.

**From:** Overnight executor (Opus Max chief engineer + Sonnet/Opus subagents)
**To:** Runpod migration role
**Repo:** https://github.com/Zer0pa/Energy
**Final commit hash:** _filled in at run completion_

## Status post Wave 3

Three waves shipped. Wave 3 closes every gap in `CPU-HARDENING-BRIEF.md` (see
`FINAL-REPORT.md` § Wave 3 table). The repo is **ready for Runpod**: cutover is
a config-flag swap, audit/KG are mandatory, falsifiers are production-applied,
and a `httpx.MockTransport` test proves golden-fixture invariance across
`local_cpu` ↔ `runpod_rest`.

## What you inherit

A complete CPU-side Energy pipeline:

- Schemas, audit, KG, REST stubs, L6 control plane (foundation).
- Electrochem L1-L5 adapter stack with deterministic CPU paths.
- Fusion L1-L5 adapter stack with FreeGS4E / IMAS netCDF / OpenMC tiny-fixture paths.
- 50-task fusion reasoning benchmark (rule-based scoring stub, ready for LLM swap).
- 9 MCP servers via FastMCP (`pybamm`, `pvlib`, `solcore`, `cantera`, `pypsa`, `pysam`, `openmc`, `imas-codex`, `aiida`).
- TDA early-warning library (ripser+persim) with cross-domain detectors.
- 12-test falsification wave (boundary mutation, license promotion, stub validity, units, COCOS, T<0, n<0, fill-factor>1, above-Carnot, SoC out-of-range, missing IDS, cross-model disagreement).
- 41 source manifests + 41 license findings.
- Decision log: 6 decisions covering architecture, license policy, MCP product surface, falsification wave, data sovereignty, deviations.
- ENERGY_* env flags for layer-by-layer backend selection.

## What is scientifically valid vs engineering-stub

See FINAL-REPORT.md for the per-adapter table.

## Runpod cutover — the only thing you should do

The architectural invariant is: changing `ENERGY_L?_BACKEND` from `gpu_rest_stub` (or `stub`) to `runpod_rest` triggers a config-only swap. The contracts above MUST be preserved:

1. Same `UniversalLayerEnvelope` schema version.
2. Same `DeviceResponseObject` schema version.
3. Same REST endpoint shape — stubs at `energy_physics_pipeline/rest/app.py` are the contract.
4. Same audit/KG writes (every Runpod call must emit the same envelope shape).
5. Same falsifier IDs (re-route to `energy_physics_pipeline.l6.router.run` in the Runpod handler).
6. Cross-model disagreement records emitted with the same metric and thresholds.

The `/v1/runpod/{layer}/{domain}` endpoint is the placeholder you replace. It currently returns 503. Wire your Runpod-side function under that route and remove the `raise HTTPException(503)`.

## Cutover gates (PRD)

- Same schemas as stubs.
- Golden fixture passes before AND after backend swap (output_hash invariant).
- Only provenance/runtime fields may change.
- Budget cap and kill switch configured.
- Artifact checksums recorded.
- No Class C/D/E licensed tool enters product path without `kg://license-grant/...` evidence.

## Parked for Runpod

| Layer | Adapter | Reason |
|---|---|---|
| L2 | CGYRO nonlinear | GPU production sweeps |
| L2 | GyroSwin training + large inference | GPU training |
| L2 | MACE/eSEN large MD + fine-tune | GPU |
| L3 | JOREK / BOUT++ full nonlinear MHD | HPC wall time |
| L3 | PF-PINO training | GPU + Class E pending license |
| L4 | Reasoning agent (DeepSeek-R1-Distill-Llama-70B) inference | Runpod vLLM |
| L5 | Large OpenMC GPU transport | GPU |
| L5 | OpenMC R2S full activation | HPC |
| L1 | Large GW spectra (GPAW) | HPC |

## License blockers (must resolve before scientific promotion)

- AlphaPEM (GPL-3): isolate behind subprocess boundary or replace with permissive PEM (executor delivered Butler-Volmer fixture for product path).
- PF-PINO (no top-level LICENSE visible): blocked at Class E until verified.
- GENE (academic-only): blocked.
- AQCat25 (CC-BY-NC-SA-4.0): non-commercial only.
- eSEN-M (FAIR Chemistry License): ZA acceptance verification required before production deploy.
- DeepSeek-R1-Distill-Llama-70B: inherits Llama license; research/prototype only.

## Audit-trail joint access

Customer can audit its campaign; Zer0pa retains redacted operational provenance for reproducibility. See `docs/decisions/004-data-sovereignty.md`.

## Quick smoke test

```bash
git clone https://github.com/Zer0pa/Energy
cd Energy-Physics-Pipeline
python3.13 -m venv .venv
.venv/bin/pip install -e '.[test,electrochem,fusion,tda,mcp]'
./scripts/full_check.sh
```

Expected: contract tests + falsification wave + scientific bounds + integration tests all green; 12-of-12 falsification wave; CLI health and registry render.
