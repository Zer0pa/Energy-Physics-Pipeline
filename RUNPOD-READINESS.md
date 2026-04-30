# Runpod Readiness — Zer0pa Energy (Wave 4)

**Status:** READY for Runpod migration at the Wave 4 commit.

**Boundary:** Research infrastructure for in silico energy science:
electrochemical conversion (batteries, green hydrogen electrolysis, fuel
cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma
physics. Outputs are research artifacts. No regulatory certification claims.
No clinical or human-subject use. Defence / weapons applications are out of
scope under operator policy.

## What was built

A complete CPU-first Energy pipeline:

  * **Same-shape REST surface** — every public layer endpoint
    (`/v1/<sub>/<layer>/<op>`) routes through
    `energy_pipeline.l6.backend_resolver.resolve_and_dispatch`. Setting
    `ENERGY_L?_BACKEND=runpod_rest` flips that endpoint to forward through
    `RunpodRestAdapter`; clients never need to call `/v1/runpod/...` directly.
  * **Mandatory audit/KG** — every accepted envelope (REST, parser, adapter,
    MCP) goes through `accept_envelope` / `accept_envelope_and_dro`. Under
    `ENERGY_AUDIT_REQUIRED=true` the writer + store are required; under
    `ENERGY_BOUNDARY_GATE=strict`, fail/quarantine raises `EnvelopeRejected`.
  * **Parallel-safe runtime** — `ENERGY_AUDIT_DIR`, `ENERGY_AUDIT_DB_PATH`,
    `ENERGY_KG_DIR` env overrides isolate each subagent/worktree. Subprocess
    collision test green.
  * **Production falsifier authority** — 13-gate `DEFAULT_FALSIFIER_SET`
    applied centrally. Falsification wave (12 cases) tests now reference
    production gates, not test-local helpers.
  * **License gate hardened** — GPL/conditional-license tools require
    `kg://license-grant/...` or `file:///etc/zer0pa/license-grants/...`
    evidence. Bare HTTPS LICENSE URLs are explicitly rejected.
  * **Forbidden-intent matcher** — regex+stem+NFKD normalisation; 55
    paraphrase tests; "delivery system" alone now caught.
  * **Source manifests** — 39/41 verified with real sha256; 2 demoted to
    `non_authority=True` (gyroswin, jorek). `verification_summary.md` has
    explicit verified/failed/non_authority/non-fetchable buckets.
  * **Pointer manifests** — OPTIMADE / Materials Project / NOMAD pointer
    adapters; manifest-only; no bulk data ever.
  * **MCP suite** — 9 servers, each tool calls the real typed adapter API
    (`dispatch_path` reports `real_adapter` vs `stub_fallback`).

## Architecture

Six-layer hierarchy preserved:

  * **L1** electronic structure — PySCF (real CPU), GPAW/CP2K/Wannier90/Z2Pack manifests.
  * **L2** atomistic / MLIP — MACE/fairchem-eSEN/PEMD/PiNet2 manifests; CGYRO/GyroSwin Runpod-parked.
  * **L3** mesoscale — MOOSE+RACCOON parsers; OpenLB/LBPM manifests; FreeGS4E (real CPU) for fusion equilibrium.
  * **L4** device — PyBaMM (real CPU, Chen2020 DFN), PyBOP, Solcore, Cantera, IMAS-Python (netCDF4 fixture), `ReducedTransportCpuAdapter` (ITER H98(y,2)) — all emit `DeviceResponseObject`.
  * **L5** stack/system — PyPSA + HiGHS, pvlib, PySAM analytic, Paramak/OpenMC.
  * **L6** orchestration — `EnergyConfig`, adapter registry, **backend resolver**,
    **production falsifier set**, **enforcement layer**.

Datasets / manifests:

  * 41 source manifests under `sources_log/seed.jsonl`, 39 with real sha256.
  * 12 license findings in `sources_log/license_findings.jsonl`.
  * `imas_demo.nc` (netCDF4) IDS-shaped fixture (COCOS=11, DD=3.41.0).
  * 50 fusion reasoning bench tasks (`fixtures/fusion/reasoning_bench/`).
  * OPTIMADE / Materials Project / NOMAD pointer manifests (no bulk).

Process:

  1. Every public REST call → resolver → adapter (real CPU / runpod / stub).
  2. Every adapter output → `accept_envelope_and_dro` (production falsifier
     set) → audit JSONL + DuckDB + KG nodes/edges.
  3. Strict gate refuses to return failed envelopes; surfaces structured 503
     with the audited body.

## Differentiators by layer

| Layer | What sets us apart |
|---|---|
| L1 | Quantum slot real CPU: VQE on H2 STO-3G with qiskit 2.4 manual JW reaching 0.10 mHa vs FCI in 120 COBYLA iter — proves the differentiable-quantum-channel substrate without a "quantum advantage" claim. |
| L2 | Universal gyrokinetic round-trip via Pyrokinetics: GS2↔CGYRO max-residual=0.0 across q/shat/beta/Ti/Te. |
| L3 | Real FreeGS4E diverted single-null equilibrium fixture; NetCDF4-backed IMAS surrogate independent of imas_core. |
| L4 | PyBaMM Chen2020 DFN P2D + PyBOP Bayesian inference loop; ITER H98(y,2) reduced-transport scenario solver emitting fusion DRO. |
| L5 | PyPSA single-bus Monte-Carlo LCOE with P5/P50/P95; pvlib Ineichen clear-sky on Sandton coordinates; perovskite/Si tandem analytic; Co-60/Mn-56/He-6 R2S point-kinetics activation. |
| L6 | `backend_resolver` makes Runpod a pure config flag; `production_falsifiers` is 13-gate authority, no test-local helpers; `accept_envelope` is the only acceptance path. |

## Parked GPU-only work (Runpod migration scope)

| Layer | Adapter | Reason |
|---|---|---|
| L1 | Large GW spectra (GPAW) | HPC wall time |
| L1 | OpenMC large transport with GPU | GPU |
| L2 | CGYRO nonlinear gyrokinetic | GPU production |
| L2 | GyroSwin training + large inference | GPU |
| L2 | MACE/fairchem-eSEN large MD + fine-tune | GPU + torch on linux |
| L3 | JOREK / BOUT++ full nonlinear MHD | HPC |
| L3 | PF-PINO training | GPU + Class E pending license |
| L4 | Reasoning agent (DeepSeek-R1-Distill-Llama-70B) inference | Runpod vLLM |
| L5 | Large OpenMC GPU transport | GPU |
| L5 | OpenMC R2S full activation | HPC + ALARA / FISPACT-II rights |

## Strict gate transcript

```bash
# Reproduce on a fresh clone
git clone https://github.com/Zer0pa/Energy
cd Energy
git checkout wave4-cpu-hardening
python3.13 -m venv .venv
.venv/bin/pip install -e '.[test,tda,mcp]'
.venv/bin/pip install pybamm pybop pypsa pvlib cantera pyscf netCDF4 freegs omas pyrokinetics qiskit mcp ripser persim

ENERGY_AUDIT_DIR=$(mktemp -d) ENERGY_KG_DIR=$(mktemp -d) bash scripts/full_check.sh
.venv/bin/python tools/verify_sources.py --dry-run
.venv/bin/python tools/runpod_cutover_checklist.py
```

Expected:

  * `ruff check energy_pipeline tests scripts` — passes.
  * `pytest tests` — 475 passed, 0 failed.
  * `bash scripts/full_check.sh` — STRICT FULL CHECK OK.
  * `verify_sources.py --dry-run` — 39 ok / 0 fail / 2 skipped (non-authority).
  * `git status --short` — clean.

## What the Runpod role does next

1. Set `ENERGY_RUNPOD_BASE_URL` to the upstream URL.
2. Set `ENERGY_L?_BACKEND=runpod_rest` for layers being migrated.
3. The same `/v1/<sub>/<layer>/<op>` endpoints automatically forward.
4. The Runpod side must:
   * Emit `UniversalLayerEnvelope`-shaped JSON (the dispatcher rejects
     mutated boundary, malformed envelopes, and 4xx/5xx with structured
     `runpod_dispatch_error` envelopes).
   * Honor the production falsifier set's gate IDs on its own envelopes if
     it does its own pre-acceptance.
5. Run the live golden-fixture invariance test against the upstream:
   `pytest tests/integration/test_runpod_same_endpoint.py -v`.
