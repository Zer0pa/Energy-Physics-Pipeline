# Architecture — Energy Physics Pipeline

**Boundary:** Research infrastructure for in silico energy science: electrochemical conversion (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. No regulatory certification claims. No clinical or human-subject use. Defence / weapons applications are out of scope under operator policy.

## The six-layer scale hierarchy

Both sub-verticals share the same six-layer pattern. They diverge at L1-L4 (different physics) and converge at L4-output (same `DeviceResponseObject`) and L6 orchestration (domain-agnostic).

```
                  Electrochemistry                      Fusion / Plasma
                  ─────────────────                     ───────────────
L1  Quantum       PySCF (CDFT, Marcus, H2 RHF)          OpenMC (transport, manifest)
    Electronic    GPAW, CP2K, Wannier90                  Nuclear data manifests
                  Quantum slot: VQE H2 (qiskit)          ENDF/B-VIII.1 etc

L2  Atomistic     MACE, fairchem (manifest-only)         GACODE/CGYRO/TGLF
    MLIP/         PiNN/PiNet2, LAMMPS                    GyroSwin (surrogate)
    Gyrokinetic   trajectory parsers                     Pyrokinetics (universal parser)

L3  Mesoscale     MOOSE+RACCOON (parser-only)            FreeGS4E (real CPU)
    Pore/         OpenLB/LBPM                            JOREK/BOUT++ (parser-only)
    Equilibrium   phase-field stubs                      TDA disruption early-warn

L4  Device        PyBaMM (battery, real CPU) ─┐          IMAS-Python (netCDF)
                  Solcore (PV, fixture)        ├─→ DRO ←─ OMAS path validators
                  Cantera (SOFC, real CPU)     │          ReducedTransport (0D)
                  PEM Butler-Volmer (analytic) │          duqtools, MITIM
                  Thermoelectric (analytic)    │
                  PyBOP inference ─────────────┘

L5  Stack/        PyPSA (real CPU dispatch)              Paramak (geometry)
    System/       pvlib (real CPU clear-sky)             OpenMC CSG fixed-source
    Reactor       PySAM (analytic LCOE)                  R2S activation (analytic)
                  OpenModelica/FMI                        DAGMC manifest validation

L6  Orchestration  AdapterRegistry (17 seeds across both sub-verticals)
    (shared)       EnergyConfig (ENERGY_* env flags)
                   Falsifier router (boundary, license, units, stubs, cross-model)
                   AuditWriter (DuckDB + JSONL)
                   KGStore (NetworkX + JSONL + GraphML export)
                   FastAPI REST stubs at /v1/{electrochem,fusion}/l{1..5}
                   9 FastMCP servers as product surface
                   ReasonerTuple curation -> 50-task fusion reasoning bench
```

## The DeviceResponseObject — the L4 → L5 bridge

This is the unification the synthesis agent surfaced. Both sub-verticals emit the *same* `DeviceResponseObject` at L4. Downstream L5 consumers (PyPSA for grid, PySAM for TEA, OpenMC for neutronics) accept the same shape. The contract:

- `sub_vertical` ∈ {electrochemistry, fusion}
- `device_family` ∈ {battery, pem_electrolyzer, pem_fuel_cell, sofc, soec, photovoltaic, thermoelectric, tokamak, stellarator, spherical_tokamak}
- `operating_conditions.axes` — vector of {name, unit, values}
- `response.curves[]` — V_vs_j, J_vs_V, voltage_time, capacity_cycle, impedance, ZT_vs_T, power_deltaT, q_profile, pressure_profile, current_density_profile, confinement_time
- `response.scalar_metrics` — type-checked range constraints (fill_factor ∈ [0,1], pce_fraction ∈ [0,1], etc.)
- `degradation_or_stability.modes/trajectory/invalid_regions`
- `handoff.l5_targets` — pypsa | pvlib | pysam | openmodelica_fmi | imas | omas | openmc

`dro_id` is a content-addressable `sha256:<hex>` of the canonical-JSON payload (sorted keys, no whitespace). Reordering keys does not change `dro_id`.

## Falsifier router

Every envelope passes through `energy_physics_pipeline.l6.router.run`, which composes:

1. **Boundary falsifier** — boundary block must be byte-identical (Pydantic-enforced; backstop falsifier).
2. **Stub validity falsifier** — `mode=engineering_stub` cannot have `scientific_valid=True`.
3. **Units falsifier** — `outputs.payload.quantities[k]` must have a `unit` field.
4. **License promotion falsifier** — Class C/D/E in scientific mode requires `kg://license-grant/*` or `https://...` or `file://...` evidence URI.

Plus per-domain falsifiers:

- COCOS / IDS-version / monotonic-rho/time / q>0 (fusion L4).
- PV fill_factor ∈ [0,1] (electrochem L4 PV).
- Battery SoC ∈ [0,1] (electrochem L4 battery).
- Thermoelectric efficiency below Carnot (electrochem L4 TE).
- Cross-model disagreement < 0.25 (pass), 0.25-0.50 (warn), >0.50 (quarantine) (fusion L2).

Aggregator: `gate_status` is the highest severity any falsifier flags. `pass_ < warn < fail < quarantine`.

## The audit + KG sovereignty trail

```
   adapter.run(spec) ──> envelope.finalize() ──> AuditWriter.write_event()
                                              ──> KGStore.add_node(SimulationRun, ...)
                                              ──> KGStore.add_node(DeviceResponseObject, ...)
                                              ──> KGStore.add_edge(USED_TOOL, ..., ToolAdapter)
                                              ──> KGStore.add_edge(PRODUCED, SimulationRun, DRO)
                                              ──> KGStore.add_edge(FEEDS_L5, DRO, ...)
                                              ──> ReasonerTuple per meaningful run
                                              ──> CrossModelDisagreementRecord per L2 cmp
                                              ──> EarlyWarningSignal per TDA window
```

Every artifact carries `boundary` byte-identical, `provenance.{agent_id, model_id, git_sha, input_hash, output_hash, config_hash}`, and a content-addressable id.

## Backend selection — Runpod cutover

```
ENERGY_L?_BACKEND = stub | local_cpu | gpu_rest_stub | runpod_rest | …
```

Per layer. The Runpod cutover is a config-flag flip from `gpu_rest_stub` to `runpod_rest`; the REST endpoint shape at `/v1/{electrochem,fusion}/l{1..5}/{op}` is the contract. The placeholder `/v1/runpod/{layer}/{domain}` returns 503 until Runpod handlers land.

Acceptance: same DRO `output_hash` (on the canonical projection) before and after the swap. Live test: `tests/integration/test_plug_replaceability_live.py`.

## Cross-cutting capabilities

- **TDA early-warning** — `energy_physics_pipeline.tda` (ripser+persim). Cross-domain detectors for battery thermal runaway, fuel-cell membrane breakdown, electrolyser stack degradation, SOFC delamination, plasma disruption. No-leakage guard. Demonstrated end-to-end on real PyBaMM voltage trajectories.
- **MCP product surface** — 9 FastMCP servers, JSON-RPC over stdio. In-process and subprocess-spawn smoke tests both green. Read-only by default; mutation requires a signed plan + audit event.
- **50-task fusion reasoning benchmark** — rules-based scorer; refusal_recall=1.0 on the 10 forbidden-intent tasks. Wired for `hosted_claude` / `runpod_vllm` reasoner backend swap.

## What stays Runpod-only

| Capability | Reason |
|---|---|
| MACE / fairchem large MD + fine-tune | torch wheels not on Python 3.13 darwin yet; install on Linux |
| CGYRO nonlinear gyrokinetic sweeps | GPU production runs |
| GyroSwin training + large inference | GPU |
| JOREK / BOUT++ full nonlinear MHD | HPC wall time |
| OpenMC large GPU transport | GPU |
| OpenMC R2S full activation (FISPACT-II) | HPC + license isolation |
| 70B reasoner inference (DeepSeek-R1-Distill-Llama) | GPU |
| BoTorch + Ax | torch dependency on 3.13 darwin |
| PF-PINO training | GPU + Class E license pending |
| GPAW GW spectra (large supercell) | HPC |
