# Energy Physics Pipeline PRD - Overnight CPU-First Execution Mandate

## Boundary

Research infrastructure for in silico energy science: electrochemical conversion (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. No regulatory certification claims. No clinical or human-subject use. Defence / weapons applications are out of scope under operator policy.

## Executive Decision

This repository uses one PRD with two execution parts:

- Part A: electrochemical conversion.
- Part B: fusion and plasma physics.
- Shared inside Energy only: L6 orchestration, audit/KG contracts, REST-stub conventions, and the L4 `DeviceResponseObject`.
- Forbidden: substrate sharing with Health or Materials. Comparable patterns may be read; no dependency, copied runtime, shared database, or shared service may be introduced.

The overnight executor is not being briefed to write another plan. It is being briefed to build the CPU-complete Energy pipeline scaffold, prove it with tests and fixtures, run a falsification wave, commit, and push. The governing objective is: when Runpod GPU access arrives, only GPU-dependent backends are swapped behind existing interfaces by config flag. A Runpod migration that requires an architectural rewrite is a failure.

## Operating Mandate For The Overnight Executor

The lead agent is Opus Max acting as chief engineer. It must preserve its context for architecture, scientific judgment, interface control, and on-the-fly invention. It must use subagents aggressively:

- Sonnet level is the minimum for implementation subagents.
- Opus level is required for architecture, cross-layer scientific uncertainty, fusion reasoning, license-risk arbitration, and any decision that changes the interface contract.
- The lead may make executive decisions without user engagement when those decisions move the system toward more performant, more dataful, more falsifiable, and more powerful engineering outcomes within the boundary.
- Claude deep research capability and Claude subagents are the research mechanism. Every lookup becomes a `SourceManifest`; no unlogged web claim may become an authority.
- On receipt of the startup prompt, the overnight executor must proceed immediately. It must not ask the user clarifying questions. It reports only after the end-to-end CPU pipeline and falsification wave have completed, or after a hard blocker makes completion impossible.

The lead must keep docs and handover artifacts frozen until the real gate is met. It must not turn partial evidence into a pass narrative.

## Source Basis

The local research folder `/Users/Zer0pa/Energy-Physics-Pipeline Portfolio/Energy-Physics-Pipeline Research` was checked and is byte-identical to:

- `source-briefs/01-electrochemical-m2s-pipeline.md`
- `source-briefs/02-fusion-sa-llm-data-standards.md`

The executor must read, in order:

1. `README.md`
2. `MODUS-OPERANDI.md`
3. `source-briefs/00-research-agent-handover-note.md`
4. `source-briefs/01-electrochemical-m2s-pipeline.md`
5. `source-briefs/02-fusion-sa-llm-data-standards.md`
6. `synthesis/01-fresh-eyes-on-energy-briefs.md`
7. `PRD.md`
8. `HANDOFF-TO-OVERNIGHT-EXECUTOR.md`

## Scope And MVP Wedges

The PRD mandates parallel MVP tracks. The lead may reorder local tasks for dependency efficiency, but all four tracks must be represented in code, fixtures, tests, and audit before final report.

| Track | Purpose | CPU-first deliverable | GPU parking rule |
| --- | --- | --- | --- |
| Control plane | The invariant substrate for all Energy work | Python package skeleton, schemas, validators, audit/KG writer, REST stubs, CLI smoke runner, golden fixtures | No GPU dependency allowed |
| Battery digital twin | Fastest revenue wedge | L1/L2/L3 manifest inputs into PyBaMM/PyBOP/BDF L4, L5 dispatch/economics fixture, battery `DeviceResponseObject` | Large MLIP MD and fine-tuning only |
| Fusion L6 PoC | Highest-moat early credibility wedge | IMAS/OMAS/imas-core fixture layer, 50-task reasoning benchmark, read-only IMAS Codex gateway wrapper, fusion DRO fixture | 70B local inference/fine-tune and GyroSwin training only |
| Green hydrogen / SA PGM | Strategic platform-buyer wedge | Catalyst-screening contract, eSEN/fairchem gated adapter stub, PEM electrolyser/fuel-cell DRO fixtures, platform-retainer package | eSEN/large model inference until rights and GPU are available |
| PV/thermoelectric reference | Clean architecture proof | Solcore/pvlib/PySAM fixture path and thermoelectric schema/gates | Heavy DFT/phonon production sweeps only |

Thermoelectrics remain an open ownership question between Energy and Materials. In this repo, thermoelectrics must be supported as a schema and fixture path because the boundary includes it, but not elevated above the battery/fusion/green-hydrogen MVPs unless the operator later assigns it primary ownership here.

## Architecture Invariants

### UniversalLayerEnvelope

Every adapter, stub, simulator, MCP server, and LLM-assisted tool must accept or emit a `UniversalLayerEnvelope`. Tool-native objects may not cross layer boundaries.

```yaml
UniversalLayerEnvelope:
  schema_version: "energy.envelope.v0.1"
  boundary: "Research infrastructure for in silico energy science: electrochemical conversion (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. No regulatory certification claims. No clinical or human-subject use. Defence / weapons applications are out of scope under operator policy."
  envelope_id: "sha256:<canonical-json>"
  campaign_id: string
  run_id: uuid
  sub_vertical: electrochemistry | fusion
  layer: L1 | L2 | L3 | L4 | L5 | L6
  domain: battery | green_h2 | fuel_cell | sofc | soec | pv | thermoelectric | fusion
  mode: scientific | engineering_stub | replay | validation
  backend:
    adapter: string
    tool: string
    tool_version: string
    execution_mode: local_cpu | isolated_cpu | gpu_rest_stub | runpod_rest | external_service
    license_class: A | B | C | D | E
    license_evidence_uri: string
  inputs:
    refs: [{type, uri, sha256, schema_version}]
    payload: object
  outputs:
    refs: [{type, uri, sha256, schema_version}]
    payload: object
  uncertainty:
    distribution: none | normal | lognormal | empirical | ensemble | posterior
    p05: object
    p50: object
    p95: object
    contributors: [L1, L2, L3, L4, L5, data, surrogate]
  falsification:
    gate_status: pass | warn | fail | quarantine
    scientific_valid: boolean
    cross_model_disagreement: object
    unit_check_passed: boolean
    conservation_check_passed: boolean
    boundary_check_passed: boolean
    failures: [{gate_id, severity, message, evidence_uri}]
  provenance:
    agent_id: string
    model_id: string
    git_sha: string
    created_at: ISO-8601
    input_hash: sha256
    output_hash: sha256
    config_hash: sha256
    artifact_hashes: [sha256]
    source_refs: [uri]
```

Required tests:

- Missing or altered boundary fails.
- Canonical JSON roundtrip preserves hashes.
- Stub, CPU, and Runpod response bodies validate against the same schema.
- Class C/D/E backends cannot be promoted to product mode without an explicit license grant record.
- Stubs can satisfy engineering acceptance only; they cannot set `scientific_valid=true`.

### Unified DeviceResponseObject

The L4 to L5 handoff is the `DeviceResponseObject`. It covers batteries, electrolysers, fuel cells, SOFC/SOEC, PV, thermoelectrics, tokamaks, stellarators, and research fusion devices.

```yaml
DeviceResponseObject:
  schema_version: "energy.dro.v0.1"
  dro_id: "sha256:<canonical-json>"
  boundary: "Research infrastructure for in silico energy science: electrochemical conversion (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. No regulatory certification claims. No clinical or human-subject use. Defence / weapons applications are out of scope under operator policy."
  sub_vertical: electrochemistry | fusion
  device_family: battery | pem_electrolyzer | pem_fuel_cell | sofc | soec | photovoltaic | thermoelectric | tokamak | stellarator | spherical_tokamak
  operating_conditions:
    axes: [{name, unit, values}]
    fixed: object
  response:
    curves:
      - curve_type: V_vs_j | J_vs_V | voltage_time | capacity_cycle | impedance | ZT_vs_T | power_deltaT | q_profile | pressure_profile | current_density_profile | confinement_time
        x: {quantity, unit, values}
        y: {quantity, unit, values}
        uncertainty: {lower, upper, method}
    scalar_metrics:
      ocv_V: number|null
      overpotential_V_at_target_j: number|null
      capacity_Ah: number|null
      pce_fraction: number|null
      fill_factor: number|null
      zt: number|null
      q95: number|null
      beta_N: number|null
      H98: number|null
      neutron_wall_loading_MW_m2: number|null
  degradation_or_stability:
    modes: [string]
    trajectory: [{t_s, state, uncertainty}]
    invalid_regions: [string]
  handoff:
    l5_targets: [pypsa, pvlib, pysam, openmodelica_fmi, imas, omas, openmc]
    required_fields_satisfied: boolean
    missing_fields: [string]
  audit:
    envelope_id: string
    dro_source_layer_run_ids: [uuid]
    kg_nodes: [string]
    artifact_refs: [{type, uri, sha256}]
```

### Plug-Replaceability

Any layer backend may be replaced only if it preserves:

- The same `UniversalLayerEnvelope`.
- The same domain payload schema version.
- The same REST endpoint shape.
- The same artifact manifest format.
- The same audit/KG writes.
- The same falsifier IDs.

Runpod cutover is accepted only when changing a config flag from `gpu_rest_stub` to `runpod_rest` preserves golden fixture behavior except for runtime/provenance fields.

## Falsification Framework

### CrossModelDisagreementRecord

Cross-model disagreement is a first-class quantity, not an explanation after the fact.

```yaml
CrossModelDisagreementRecord:
  record_id: string
  object_id: string
  quantity: string
  unit: string
  models_compared: [string]
  values: [number]
  uncertainties: [number]
  metric: absolute | relative | sigma_normalized | distributional
  pass_threshold: number
  warn_threshold: number
  fail_threshold: number
  status: pass | warn | fail | quarantine
  resolution_action: rerun | add_reference_model | block_handoff | escalate
```

Rules:

- Never average away a failed disagreement.
- `fail` blocks downstream L5 and L6 optimization.
- `warn` may continue only with uncertainty inflation and explicit audit note.
- Any output without units, uncertainty, source manifest, and falsifier status is invalid.

### TDA Early-Warning

Persistent homology is a cross-cutting early-warning capability for multi-physics failure modes: plasma disruption, battery thermal runaway, membrane failure, electrolyser stack degradation, SOFC delamination, and thermoelectric degradation.

Default CPU path: `ripser.py` plus `persim`. GUDHI requires module-level license whitelist. `giotto-tda` is AGPL and may not be embedded in product code without explicit approval.

```yaml
EarlyWarningSignal:
  signal_id: string
  source_object_id: string
  domain: battery | electrolyser | fuel_cell | sofc | pv | thermoelectric | fusion
  window_spec: {length_s, stride_s, embedding_dim, delay_s}
  features: {persistence_entropy, max_lifetime_h0, max_lifetime_h1, bottleneck_delta, landscape_delta}
  warning_score: float
  lead_time_estimate_s: float
  false_positive_rate_estimate: float
  status: normal | watch | warn | fail
```

No disruption or runaway warning may be accepted from a scalar classifier alone. It must preserve persistence diagrams or derived topological artifacts and pass no-leakage checks.

## Required Repository Outcome

The overnight executor must create or complete this repository shape unless a better equivalent is justified in `DECISIONS.md`:

```text
energy_physics_pipeline/
  schemas/
  adapters/
    electrochem/
    fusion/
    shared/
  audit/
  kg/
  rest/
  cli/
fixtures/
  electrochem/
  fusion/
  negative/
tests/
  contract/
  falsification/
  integration/
docs/
  decisions/
```

Minimum commands by final report:

- Install CPU dependencies in a local virtual environment or project-native environment.
- Run schema generation/validation.
- Run REST stub smoke tests.
- Run layer handoff tests.
- Run at least one electrochemistry end-to-end CPU path to a DRO and L5 metric.
- Run at least one fusion Phase-0 path to a DRO and L6 reasoning benchmark result.
- Run the falsification wave.
- Commit and push.

## Part A - Electrochemical Conversion Contracts

### L1 Electronic Structure

CPU mandate:

- Implement `L1JobSpec`, `L1Result`, `ElectronicStructureAdapter`.
- Support parser/manifest inputs for CIF, xyz, extxyz, SMILES, OPTIMADE, Materials Project, NOMAD, and local tiny fixtures.
- Implement a PySCF smoke path for molecule/small-cell calculations where installable.
- Implement GPAW, CP2K, Wannier90, and Z2Pack input/output parsers or manifests before real production runs.
- REST stubs: `/v1/electrochem/l1/singlepoint`, `/relax`, `/adsorption-profile`, `/marcus`, `/optical-spectrum`, `/topology`.

Falsifiers:

- Units and electrode-reference conventions required.
- Marcus reorganization energy must be positive.
- PV band gap must be in `[0, 5] eV` unless explicitly invalid.
- Cross-model energy disagreement: `<0.25 eV` pass, `0.25-0.50 eV` warn, `>0.50 eV` fail for ranking.

### L2 Atomistic / MLIP

CPU mandate:

- Implement `AtomisticSystemSpec`, `L2ObservableBundle`, `MLIPAdapter`, `TransportCoefficientAdapter`.
- Build manifest-only support for MACE, fairchem/eSEN, LAMMPS, PEMD, PiNN/PiNet2.
- Build trajectory parsers and small synthetic MSD/RDF fixtures.
- Use MACE/fairchem weights only when license and access are recorded. No silent weight downloads.
- Keep eSEN/OC25 gated until South Africa acceptance is verified from the deployment identity.

Falsifiers:

- MSD fit `R2 >= 0.95`.
- Diffusion exponent in `[0.8, 1.2]` for normal diffusion fixtures.
- Reaction ranking invalid if uncertainty reorders candidates or disagreement exceeds `0.15 eV`.
- No model checkpoint may run without a `ModelCheckpoint` KG node and license evidence.

### L3 Mesoscale

CPU mandate:

- Implement `MesoscaleGeometrySpec`, `EffectiveTransportResult`, `PhaseFieldRunSpec`, `MesoscaleAdapter`.
- Use MOOSE/RACCOON and OpenLB/LBPM as authority lanes where available. Treat PF-PINO as disabled pending license.
- Build parser-first fixtures for pore geometry, VTK/HDF5 outputs, phase-field trajectories, tortuosity, effective diffusivity, and degradation maps.

Falsifiers:

- OpenLB/LBPM agreement within 10 percent for shared fixtures.
- Mass drift `<= 1e-5`.
- Charge residual `<= 1e-4`.
- Grid refinement change `<= 5 percent`.
- Free-energy and phase-field conservation checks required for degradation fixtures.

### L4 Device Scale

CPU mandate:

- Implement PyBaMM and PyBOP adapters for battery.
- Implement Solcore adapter for PV.
- Implement Cantera adapter for SOFC/SOEC chemistry fixtures.
- Keep AlphaPEM isolated because it is GPL-3, or replace with a permissive PEM fuel-cell fixture path.
- Emit `DeviceResponseObject` for every L4 run.
- Support BDF and EIS fixtures.

Falsifiers:

- PyBaMM voltage must remain within physical envelope for fixture chemistry.
- State of charge in `[0, 1]`.
- Capacity fade finite and nonnegative.
- EIS residual logged.
- PV fill factor and PCE fraction in `[0, 1]`.
- Thermoelectric efficiency below Carnot.

### L5 Stack, Grid, System, Economics

CPU mandate:

- Split L5 into `L5a` planning/dispatch/TEA and `L5b` dynamic controls/frequency response.
- Implement PyPSA, pvlib, PySAM, and OpenModelica/FMI stubs.
- Every LCOE/LCOH output carries P5/P50/P95.
- Do not claim grid-forming inverter or frequency-response validity from static PyPSA alone.

Falsifiers:

- Energy balance residual `<= 1 percent`.
- PV AC power does not exceed inverter rating except recorded clipping.
- PyPSA/PySAM LCOE agreement within 10 percent for PV fixture.
- Static-vs-dynamic limitations written into the DRO and audit log.

## Part B - Fusion / Plasma Contracts

### L1 Nuclear / Plasma-Wall

CPU mandate:

- Implement OpenMC 0.15.3 manifest and tiny fixed-source transport fixture.
- Build nuclear-data manifests for ENDF/B-VIII.1, JEFF-4.0, JENDL-5, FENDL-3.2c, TENDL, IRDFF-II, and decay libraries. No bulk local data.
- Implement a boundary classifier before any tritium-related output.

Falsifiers:

- No output without library version, checksum, tally uncertainty, and boundary decision.
- Allowed: blanket and breeding-blanket research artifacts.
- Blocked: weapons-grade tritium, stockpile, extraction/purification optimization, diversion, military or defence framing.

### L2 Gyrokinetic Transport

CPU mandate:

- Implement `FusionProfileState`, `GyrokineticCaseSpec`, `GyrokineticTransportBundle`, and `GyroSwinTrainingTuple`.
- Use GACODE/TGLF/CGYRO as primary commercializable authority path where available.
- Use Pyrokinetics for interchange and parser validation.
- Keep GENE execution disabled unless a specific license grant permits commercial service execution, remote/cloud execution, derivative surrogate training, generated-label ownership, publication, and no-redistribution boundaries.
- Treat GyroSwin as a surrogate until calibrated.

Falsifiers:

- Unit and gyroBohm normalization roundtrip residual `<1e-8` for scalar fixtures.
- TGLF vs CGYRO disagreement: `<25 percent` pass, `25-50 percent` warn, `>50 percent` quarantine.
- GyroSwin acceptance: same-machine heat-flux MAPE `<15 percent`, cross-machine MAPE `<25 percent`, Spearman `>=0.8`, ECE `<=0.1`, OOD uncertainty increases outside training envelope.

### L3 Equilibrium / MHD / Disruption

CPU mandate:

- Split authority into equilibrium, nonlinear MHD evidence, and TDA early warning.
- Implement FreeGS4E/FreeGSNKE CPU fixtures.
- Implement JOREK and BOUT++ dry-run/parser/stub adapters. Full runs are GPU/HPC parked.
- Implement `FusionL3HandoffPatch`.

Falsifiers:

- Grad-Shafranov residual finite and below fixture tolerance.
- `psi`, `q`, `p`, and `J_phi` share coordinate system and units.
- Flux topology identifies axis, separatrix, X-points, limiter contact, and failed reconstruction states.
- TDA no-leakage checks: no future samples, no pulse-level split leakage, no normalization fitted across train/test boundaries.

### L4 Integrated Scenario / IMAS

CPU mandate:

- Implement IMAS-Python/`imas_core` netCDF fixtures first; add HDF5/MDSplus only after import and hash tests.
- Implement OMAS path validators and converters.
- Implement `ReducedTransportCpuAdapter` for 0D/1D smoke scenarios.
- Implement duqtools config-generation and merge parsers.
- Emit fusion `DeviceResponseObject`.

Falsifiers:

- IDS bundle declares Data Dictionary version, backend, URI, occurrence, hash, source, and access class.
- COCOS/coordinate convention required.
- Profiles nonnegative where physical, `rho` and time grids monotonic, `q > 0` unless invalid reconstruction is declared.
- CPU fixture power balance residual `<=10 percent`; production promotion target `<=5 percent`.
- P5/P50/P95 required or `scientific_valid=false`.

### L5 Reactor Engineering

CPU mandate:

- Implement Paramak geometry fixture and CSG fallback.
- Implement DAGMC validation when `.h5m` is present.
- Implement OpenMC CSG fixed-source transport.
- Implement OpenMC R2S activation when available; otherwise analytic/stub activation with `scientific_valid=false`.
- FISPACT-II remains license-isolated and optional.

Falsifiers:

- DAGMC material tags required.
- OpenMC tally relative error required; design-ranking fixture default `<=10 percent`.
- Particle balance closes within configured tolerance.
- TBR allowed only as `tbr_dimensionless_research_only` and never as sole optimization target.
- Cross-library disagreement: TBR `>5 percent`, heating `>10 percent`, activation proxy `>20 percent` quarantines ranking outputs.

## Shared L6 Orchestration

L6 is the Energy Control Plane:

- Adapter registry for every simulator, MCP server, model, and dataset.
- Typed execution graph.
- Audit/KG writer.
- Objective proposer.
- Falsifier router.
- Human-independent overnight decision log.
- Config-only backend selection.

Reference stack: LangGraph, Prefect, Parsl, AiiDA, Atomate2, BoTorch, Ax. The executor may choose a smaller first implementation if it preserves the contracts and proves end-to-end execution.

## Agent Topology For Overnight Execution

Minimum subagents:

| Agent | Minimum model | Ownership |
| --- | --- | --- |
| Chief engineer | Opus Max | Architecture, decisions, context, integration, final falsification |
| Interface/contracts | Opus or Sonnet | Schemas, validators, canonical hashes, REST contracts |
| Electrochem L1/L2 | Sonnet | Quantum/MLIP manifests, parsers, fixtures |
| Electrochem L3/L4 | Sonnet | Mesoscale and device adapters, DRO emission |
| Electrochem L5 | Sonnet | PyPSA/pvlib/PySAM/OpenModelica/FMI and economics |
| Fusion L1/L2 | Opus or Sonnet | OpenMC, nuclear manifests, GACODE/GyroSwin contracts |
| Fusion L3/L4 | Opus or Sonnet | FreeGS4E, TDA, IMAS/OMAS/imas-core |
| Fusion L5 | Sonnet | Paramak/OpenMC/DAGMC/R2S |
| Audit/KG | Sonnet | JSONL, SQLite/DuckDB, GraphML/RDF export |
| Falsification wave | Opus or Sonnet | Negative tests, license gates, cross-model disagreement |
| Claude deep research | Opus or Sonnet | Source verification only, logged as manifests |

Subagents must work in parallel worktrees or non-overlapping file scopes. They must not revert each other's changes. The lead integrates and owns final consistency.

## Audit, KG, And Data Sovereignty

### Provenance Modes

Electrochemistry:

```text
campaign_id -> candidate_id -> layer_run_id -> artifact_id
```

Fusion:

```text
scenario_id -> facility -> pulse_id/shot_id -> time_window -> IDS_path -> layer_run_id
```

Minimum KG nodes:

```text
CandidateMaterial, DeviceResponseObject, FusionScenario, PulseWindow,
SourceManifest, ToolAdapter, ModelCheckpoint, SimulationRun,
FalsifierResult, DisagreementRecord, LicenseFinding, RightsPolicy,
GroundTruthObservation, ReasonerTuple
```

Minimum KG edges:

```text
DERIVED_FROM, USED_TOOL, USED_MODEL, USED_SOURCE, PRODUCED,
VALIDATED_BY, FAILED_BY, DISAGREES_WITH, FEEDS_L4, FEEDS_L5,
OWNED_BY, RIGHTS_CONSTRAINED_BY
```

Build CPU-first as JSONL plus SQLite or DuckDB. Neo4j is optional and not a blocker.

### SourceManifest

```yaml
SourceManifest:
  source_id: string
  uri: string
  retrieval_method: api | git | hf | manual | fixture | claude_deep_research
  retrieved_at: iso8601
  license_spdx_or_text: string
  allowed_use: research | commercial | noncommercial | unknown
  geography_restrictions: string | null
  checksum: string
  local_slice_size_mb: number
  bulk_data_stored: false
  citation: string
  rights_notes: string
```

### Data-Sovereignty Defaults

- Customer owns proprietary input structures, pulse/scenario configs, customer lab data, and campaign-specific outputs.
- Zer0pa owns orchestration code, generic schemas, adapter abstractions, non-customer-specific priors, and anonymized method improvements only where contract permits.
- Fine-tunes default to customer-isolated artifacts unless the customer opts into shared-core improvement.
- Audit trails are jointly accessible: customer can audit its campaign; Zer0pa retains redacted operational provenance for reproducibility.
- Fusion raw public pulse data remains governed by source facility terms. Customer-specific IMAS scenario optimizations are customer-controlled.
- No bulk datasets on Mac. Store manifests and small slices locally; offload approved private artifacts to Hugging Face under Architect-Prime.

Open question for operator: whether MLIP fine-tunes and posterior distributions are customer-owned by default or licensed back to Zer0pa for cross-campaign improvement.

## Self-Bootstrapping Reasoner

Every meaningful run emits:

```yaml
ReasonerTuple:
  tuple_id: string
  problem_context: string
  input_spec_ref: string
  tool_plan: object
  simulation_request_ref: string
  raw_result_ref: string
  reduced_observables_ref: string
  falsifier_results: [string]
  disagreement_records: [string]
  ground_truth_ref: string | null
  outcome_label: pass | fail | inconclusive | superseded
  rights_label: public | internal | customer_confidential | restricted
  next_action: string
```

Fusion GyroSwin curation:

- Public DIII-D manifests first; KSTAR only after rights approval.
- Convert pulse metadata to IMAS-compatible manifests.
- Extract time windows and map equilibrium/profile IDS paths.
- Use CGYRO/TGLF or licensed GENE outputs as solver-state labels. Raw shots are validation/scenario context, not direct labels.
- Hold out entire machines and campaigns for validation.
- No customer or restricted facility data enters shared training without written rights.

## MCP Server Suite

Adopt MCP as product surface, not authority surface. MCP tools call registered adapters and emit normal artifacts. Default mode is read-only. Mutation requires a signed plan and audit event.

Required suite:

- `pybamm-mcp`
- `pvlib-mcp`
- `solcore-mcp`
- `cantera-mcp`
- `aiida-mcp`
- `pypsa-mcp`
- `pysam-mcp`
- `openmc-mcp`
- `imas-codex` gateway, read-only until license metadata is clarified
- `alphapem-mcp` only if isolated behind GPL boundaries; otherwise replace with a permissive PEM fuel-cell adapter

## Lab And Cloud Integration

Electrochemistry:

- AlabOS/cloud-lab integration is recipe and result-manifest first.
- Closed-loop synthesis is allowed only after in silico gates pass and customer/lab rights are recorded.
- No regulatory, certification, or safety claims.

Fusion:

- Experimental-device collaboration is manifest-first.
- DIII-D, UKAEA, EUROfusion, ITER, CFS, and KSTAR links are data-rights dependent.
- No mutation of facility data from MCP tools.

## Quantum Slot

Electrochemistry L1 gets a narrow quantum slot:

- PySCF CDFT for Marcus parameters.
- Tiny VQE smoke fixtures for H2/LiH or similar only if CPU-simulatable and useful for interface discipline.
- No quantum advantage claims.

Fusion does not get a near-term quantum simulator slot. It may log frontier watch items, but no overnight work is blocked on quantum capability.

## Runpod Migration Plan

Config flags:

```env
ENERGY_EXECUTION_PROFILE=local_cpu_first
ENERGY_ARTIFACT_MODE=manifest_only
ENERGY_ALLOW_BULK_DATA=false
ENERGY_AUDIT_REQUIRED=true
ENERGY_BOUNDARY_GATE=strict

ENERGY_L1_BACKEND=local_cpu|gpu_rest_stub|runpod_rest
ENERGY_L2_BACKEND=stub|local_cpu|gpu_rest_stub|runpod_rest
ENERGY_L3_BACKEND=stub|local_cpu|gpu_rest_stub|runpod_rest
ENERGY_L4_BACKEND=local_cpu|gpu_rest_stub|runpod_rest
ENERGY_L5_BACKEND=local_cpu|stub_fmi|runpod_batch
ENERGY_L6_BACKEND=local_cpu|runpod_orchestrator

ENERGY_FUSION_GYROSWIN_BACKEND=stub|runpod_rest
ENERGY_REASONER_BACKEND=hosted_claude|runpod_vllm|local_stub
ENERGY_DRO_SCHEMA_VERSION=energy.dro.v0.1
ENERGY_ENVELOPE_SCHEMA_VERSION=energy.envelope.v0.1
```

Runpod-only parking list:

- 70B local inference/fine-tuning.
- GyroSwin training and large inference.
- CGYRO nonlinear production sweeps.
- Large OpenMC GPU transport.
- Large MLIP MD and fine-tuning.
- PF-PINO training.

Everything else must be built CPU-side now as real implementation, parser, fixture, or REST stub.

Cutover gates:

- Same schemas as stubs.
- Golden fixtures pass before and after backend swap.
- Only provenance/runtime fields may change.
- Budget cap and kill switch configured.
- Artifact checksums recorded.
- No Class C/D/E licensed tool enters product path without license grant.

## Acceptance Gates

### Scientific

- Every numeric physical output carries units.
- Every accepted scientific output carries uncertainty or is invalid.
- Cross-model disagreement is logged and enforced.
- Domain-specific physics bounds pass.
- No stub can be `scientific_valid=true`.

### Engineering

- Tests pass from a clean clone.
- No bulk datasets vendored.
- No Docker required on the originating Mac.
- REST stubs exist for all future GPU endpoints.
- Config-only Runpod cutover is proven by tests.
- Audit/KG writes happen before adapter outputs are accepted.

### Brain Functionality

- The Opus Max lead preserves enough context to make scientific cross-connections.
- Subagents free the lead from local implementation load.
- Every stuck point is resolved by a decision, subagent, or logged blocker; not by asking the user mid-run.
- The final report includes what was built, what failed, falsification evidence, decision log, commit hash, and next GPU swap list.

### Falsification Wave

Before final report, run a deliberate falsification wave:

- Boundary mutation test.
- License promotion test.
- Stub scientific-validity test.
- Unit omission test.
- Bad coordinate convention test.
- Negative-temperature and negative-density tests.
- PV fill-factor >1 test.
- Thermoelectric above-Carnot test.
- Battery SoC outside `[0,1]` test.
- Fusion missing COCOS/IDS version test.
- TDA leakage test.
- Cross-model disagreement fail test.

The wave passes only if the system blocks or quarantines each bad case.

## License And Status Findings

| Item | PRD status |
| --- | --- |
| eSEN-M / fairchem | fairchem code MIT. OC25/eSEN checkpoints use FAIR Chemistry License. Hugging Face availability says global except comprehensively sanctioned jurisdictions plus China, Russia, and Belarus. South Africa is not publicly excluded, but production deploy requires ZA-side gated acceptance verification. |
| PF-PINO | No visible root license in GitHub API/content check. Class E pending. Disabled by default. |
| PEMD | No top-level `LICENSE`; `setup.py` says MIT. MIT-indicated but productization-gated pending top-level license or maintainer confirmation. |
| IMAS `imas_core` | Public `imas-core` 5.6.0, released 2026-02-12, LGPL-3.0. Use behind LGPL boundary. |
| GENE | Academic/evaluation/testing access; non-academic entities must approach GDT for a specific license. Disabled by default. |
| SCAPS replacement | Solcore confirmed as replacement path, but LGPL-3.0-or-later, not permissive. SCAPS remains excluded without negotiated rights. |
| AQCat25 | Non-commercial CC-BY-NC-SA-4.0. Optional SandboxAQ dialogue only if spin-aware full-periodic-table catalysis becomes strategic. Not MVP-gating. |

Additional corrections:

- AlphaPEM is GPL-3; isolate or replace.
- LBPM is GPL-3, not Apache.
- DAGMC is Simplified BSD, not MIT.
- MACE code may be permissive while specific weights can be non-commercial or research-gated. Weights need separate manifests.
- `imas-codex`/IMAS MCP metadata must be verified before embedding; treat as read-only gateway until cleared.
- DeepSeek-R1-Distill-Llama-70B inherits Llama licensing constraints. Use as research/prototype only with compliance; keep Qwen-family Apache alternatives available.

Primary status sources checked by the orchestrator:

- fairchem code license: <https://github.com/facebookresearch/fairchem/blob/main/LICENSE.md>
- OC25/eSEN model-card terms and geography note: <https://huggingface.co/facebook/OC25>
- PF-PINO repository: <https://github.com/NanxiiChen/PF-PINO>
- PEMD setup metadata: <https://github.com/HouGroup/PEMD/blob/main/setup.py>
- IMAS-Core release: <https://github.com/iterorganization/IMAS-Core/releases/tag/5.6.0>
- IMAS-Core PyPI: <https://pypi.org/project/imas-core/>
- GENE license pathway: <https://www.genecode.org/license.html>
- Solcore license: <https://github.com/qpv-research-group/solcore5/blob/develop/LICENSE.txt>
- AQCat25 dataset card: <https://huggingface.co/datasets/SandboxAQ/aqcat25-dataset>
- IMAS Codex metadata: <https://github.com/iterorganization/imas-codex/blob/main/pyproject.toml>

## Productisation And Pricing

Product motions:

- Campaign: USD 50k to 250k per discovery or screening campaign.
- Paid pilot: smaller scoped pilot if needed to create buyer trust.
- Platform retainer: SA PGM / green hydrogen strategic R&D relationship, year-1 floor USD 500k to 1.5M, year-3 ceiling USD 5M to 10M/year if it covers PEM catalyst screening, durability, recycling, and system economics.

Funding triangulation:

- Fusion L6/TDA/GyroSwin: DOE Fusion S&T Roadmap, Euratom, Horizon fusion calls.
- SA PGM hydrogen stack: EU Global Gateway South Africa package, EERE/HFTO hydrogen opportunities, South Africa DSI hydrogen roadmap.
- AI-for-energy toolchain/MCP suite: Horizon Europe AI-in-science and clean-industry calls.

No pricing section may imply certification, regulatory approval, plant safety approval, or operational guarantees.

## Open Questions

1. Thermoelectrics: primary ownership in Energy, Materials, or duplicated by design?
2. `imas-codex`: read-only hosted PoC only, or negotiate rights for a modifiable product substrate?
3. SA PGM anchor: PEM electrolyser catalysts first, battery/grid storage first, or a paired campaign?
4. MLIP fine-tunes and posteriors: customer-owned isolated artifacts by default, or shared-core improvement with opt-in?
5. Should the first public paper target be fusion L6 reasoning, TDA disruption warning, thermoelectric end-to-end, or PV reference pipeline?

The overnight executor must not wait for these answers. It proceeds under the defaults in this PRD and logs decisions.
