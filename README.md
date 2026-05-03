# Energy Physics Pipeline

> Live window into the Zer0pa lab. Energy Physics Pipeline is an active in-silico pipeline workstream, not a finished commercial service.

Boundary: Research infrastructure for in silico energy science: electrochemical conversion (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. No regulatory certification claims. No clinical or human-subject use. Defence / weapons applications are out of scope under operator policy.

## What This Is

Energy Physics Pipeline is an in-silico electrochemistry and fusion pipeline: CPU authority is Runpod-ready; enterprise H100 completion remains active.

This repo is the canonical workstream surface for Energy Physics Pipeline: a six-layer research pipeline spanning electrochemical conversion and fusion / plasma physics. It contains the PRD, source briefs, CPU-first execution artifacts, falsification tests, Runpod readiness evidence, and the H100 completion plan.

The current state is deliberately WIP-visible. Wave 4 made the CPU substrate ready to accept GPU backends through the same public endpoints. It did not complete the enterprise GPU-backed pipeline. The remaining authority metric is the H100 execution wave described in [`H100-ENTERPRISE-COMPLETION-PLAN.md`](./H100-ENTERPRISE-COMPLETION-PLAN.md).

## Pipeline Mechanics

| Field | Value |
| --- | --- |
| Architecture | Six-layer in-silico energy pipeline: L1 electronic structure, L2 atomistic/MLIP, L3 mesoscale, L4 device, L5 stack/system, L6 orchestration |
| Sub-verticals | Electrochemical conversion and fusion / plasma physics |
| L6 spine | `EnergyConfig`, adapter registry, backend resolver, production falsifier set, audit/KG enforcement |
| Device object | Shared L4 `DeviceResponseObject` for device-response artifacts |
| Current runtime | CPU-first substrate with Runpod cutover hooks; H100 enterprise completion active |
| Cutover control | `ENERGY_RUNPOD_BASE_URL` plus `ENERGY_L?_BACKEND=runpod_rest` |

Within Energy Physics Pipeline, the two sub-verticals may share L6 design and the L4 response schema. Across Health, Materials, and Energy Physics Pipeline, substrate sharing remains disallowed during build; redundancy is part of the parallel-exploration strategy.

## Key Metrics

| Metric | Value | Baseline |
| --- | --- | --- |
| Strict CPU gate | `475 passed`, `0 failed`, `STRICT FULL CHECK OK`, `79.72%` coverage | `RUNPOD-READINESS.md`; Wave 4 |
| Source manifests | `39 ok`, `0 fail`, `2 non_authority skipped` | `tools/verify_sources.py --dry-run` |
| Runpod cutover substrate | Same public endpoint flips by config flag | `tests/integration/test_runpod_same_endpoint.py` |
| Enterprise H100 completion | `180-500` H100-hours minimum; `600-1500` H100-hours full multi-lane | `H100-ENTERPRISE-COMPLETION-PLAN.md` |

## Repo Identity

| Field | Value |
| --- | --- |
| Identifier | Energy Physics Pipeline |
| Repository | https://github.com/Zer0pa/Energy-Physics-Pipeline |
| Portfolio | Energy workstream |
| Visibility | INTERNAL |
| Default Branch | main |
| Authority Source | `RUNPOD-READINESS.md`; `H100-ENTERPRISE-COMPLETION-PLAN.md`; `PRD.md` |
| License | Proprietary - Zer0pa internal research artifact |
| Last Verified | 2026-05-03 |

## Readiness

| Field | Value |
| --- | --- |
| CPU substrate | PASS - Wave 4 closes same-endpoint Runpod cutover, mandatory audit/KG, parallel runtime, source verification, and pointer manifests |
| Runpod migration | STAGED - repo can begin H100 work without architectural rewrite |
| Enterprise pipeline completion | ACTIVE - GPU-backed scientific lanes and falsification wave still required |
| Public/lab posture | WIP window - evidence-forward, not finished-product language |

### Honest Blocker

No GPU-backed enterprise completion wave has passed yet. A service smoke test, shaped envelope, or single endpoint flip is not completion. The first serious H100 mandate is one electrochem GPU lane, one fusion or reasoner lane, live same-endpoint cutover, audit/KG provenance, and full falsification/regression.

## What We Prove

- Wave 4 same-endpoint cutover is wired: public `/v1/<sub>/<layer>/<op>` routes through `energy_physics_pipeline.l6.backend_resolver.resolve_and_dispatch`.
- Accepted envelopes go through central `accept_envelope` / `accept_envelope_and_dro` enforcement with production falsifiers, audit JSONL/DuckDB, and KG writes.
- The CPU-first suite is strict enough to reject overclaiming: full check, Runpod same-endpoint tests, mandatory audit/KG tests, and parallel audit/KG safety tests are present.
- Source evidence is content-addressed or demoted: current authority sources report 39 verified entries, zero authority failures, and two non-authority skips.
- The H100 completion plan names the real remaining work: dataful GPU-backed lanes, CPU-vs-GPU regression, cross-model disagreement, TDA where applicable, and enterprise handoff.

## What We Don't Claim

- We do not claim the enterprise Energy Physics Pipeline is complete.
- We do not claim a Runpod smoke test, single shaped envelope, or one endpoint flip is sufficient completion evidence.
- We do not claim regulatory certification, deployable product readiness, clinical/human-subject use, or defence/weapons applicability.
- We do not claim all GPU/HPC tools are integrated; MACE/fairchem/eSEN, GyroSwin/CGYRO, vLLM reasoner, OpenMC/GPAW/R2S remain H100 work.
- We do not claim blocked or conditional licenses are cleared without `kg://license-grant/...` evidence.
- We do not commit bulk datasets to git; dataful execution must use manifests, small fixtures, checksums, and private object storage where needed.

## Verification Status

| Code | Check | Verdict |
| --- | --- | --- |
| V_01 | Wave 4 strict CPU gate: 475 passed, 0 failed, 79.72% coverage | PASS |
| V_02 | Same-endpoint Runpod cutover tests | PASS |
| V_03 | Mandatory audit/KG and parallel runtime tests | PASS |
| V_04 | Source manifest authority verification: 39 ok / 0 fail / 2 non-authority skipped | PASS |
| V_05 | H100 enterprise GPU completion wave | UNTESTED |

## Proof Anchors

| Path | State |
| --- | --- |
| `RUNPOD-READINESS.md` | VERIFIED |
| `H100-ENTERPRISE-COMPLETION-PLAN.md` | VERIFIED |
| `FINAL-REPORT.md` | VERIFIED |
| `PRD.md` | VERIFIED |
| `tests/integration/test_runpod_same_endpoint.py` | VERIFIED |
| `sources_log/verification_summary.md` | VERIFIED |

## Repo Shape

| Field | Value |
| --- | --- |
| Proof Anchors | 6 display anchors |
| Portfolio | Energy workstream |
| Package | `energy_physics_pipeline` |
| Authority Source | `RUNPOD-READINESS.md`; `H100-ENTERPRISE-COMPLETION-PLAN.md`; `PRD.md` |
| Source | `energy_physics_pipeline/` |
| Tests | `tests/contract/`; `tests/falsification/`; `tests/scientific/`; `tests/integration/` |
| Evidence | `FINAL-REPORT.md`; `RUNPOD-READINESS.md`; `sources_log/`; `docs/decisions/` |
| H100 Plan | `H100-ENTERPRISE-COMPLETION-PLAN.md` |
| Support Sections | Sub-verticals; Front Door Receipts; Agent Read Order; Provenance; Cross-workstream Principle; Executor Build State; Quick Start |

## Sub-verticals

Energy Physics Pipeline spans two physically distinct sub-verticals that share the six-layer scale hierarchy and L6 orchestration spine:

- **Electrochemical** - Butler-Volmer master equation; polarisation curve V(j) is the device-response token; buyer context includes battery digital twins, PEM catalyst screening, perovskite PV, and SA PGM strategy.
- **Fusion / plasma** - Grad-Shafranov equilibrium plus gyrokinetic Vlasov-Maxwell master equations; plasma equilibrium state vector is the device-response token; IMAS-MCP enables an LLM agentic interface.

The orchestrator resolved the PRD structure as one PRD with Part A for electrochemistry and Part B for fusion, sharing L6 and the L4 output schema inside Energy Physics Pipeline only.

## Front Door Receipts

| Receipt | Value |
| --- | --- |
| Alignment Source | `/Users/Zer0pa/orchestration-state/ZER0PA_LANE_AGENT_FRONT_DOOR_GUIDANCE_2026-05-02.md` |
| Front Door Profile | `Pipeline Mechanics` |
| Canonical Zones | `What This Is`; `Pipeline Mechanics`; `Key Metrics`; `Repo Identity`; `Readiness`; `What We Prove`; `What We Don't Claim`; `Verification Status`; `Proof Anchors`; `Repo Shape` |
| Current GitHub Target | `main` |

## Agent Read Order

For full execution context, read:

1. [`MODUS-OPERANDI.md`](./MODUS-OPERANDI.md) - role chain and parallel-exploration principle.
2. [`PRD.md`](./PRD.md) - long-horizon product requirements and interface contracts.
3. [`RUNPOD-READINESS.md`](./RUNPOD-READINESS.md) - Wave 4 CPU substrate readiness for Runpod migration.
4. [`H100-ENTERPRISE-COMPLETION-PLAN.md`](./H100-ENTERPRISE-COMPLETION-PLAN.md) - H100 enterprise completion gates and hour budget.
5. [`source-briefs/00-research-agent-handover-note.md`](./source-briefs/00-research-agent-handover-note.md) - prior research handover.
6. [`synthesis/01-fresh-eyes-on-energy-briefs.md`](./synthesis/01-fresh-eyes-on-energy-briefs.md) - fresh-eyes synthesis substrate.

## Provenance

- Initial commit: 2026-04-30.
- Research input: electrochemical M2S brief; fusion / plasma second-pass brief; research-agent handover note.
- Synthesis/orchestration: fresh-eyes synthesis, PRD, Handoff-to-Overnight-Executor.
- Overnight execution: CPU-first build, Wave 2, Wave 3, Wave 4 hardening.
- Rename: Clean pre-public rename to Energy Physics Pipeline (2026-05-03).
- Current next role: H100 Runpod enterprise completion wave.

## Cross-workstream Principle

This workstream runs in parallel with `Zer0pa/Health` and `Zer0pa/Materials`. Each workstream is built end-to-end as an independent pipeline. No substrate is shared during build. Redundancy across workstreams is deliberate: surplus coding capacity buys diversity of architecture. Any convergence happens later as a separate merge step after parallel workstreams complete.

Within Energy Physics Pipeline, electrochemistry and fusion may share L6 design and the L4 `DeviceResponseObject`; that is intra-workstream sharing and explicitly permitted.

## Executor Build State

Overnight CPU-first build delivered. See [`FINAL-REPORT.md`](./FINAL-REPORT.md), [`RUNPOD-READINESS.md`](./RUNPOD-READINESS.md), and [`HANDOFF-FROM-OVERNIGHT-EXECUTOR.md`](./HANDOFF-FROM-OVERNIGHT-EXECUTOR.md).

Repo layout:

```text
energy_physics_pipeline/
  schemas/                - UniversalLayerEnvelope, DeviceResponseObject, Falsification, Source, Reasoner
  audit/                  - JSONL + DuckDB writer with mandatory boundary check
  kg/                     - JSONL + NetworkX KG store; GraphML export
  rest/                   - FastAPI endpoints for L1-L5 electrochem + fusion
  l6/                     - config, backend resolver, registry, production falsifiers, enforcement
  tda/                    - persistent-homology early warning
  cli/                    - health, registry, smoke, serve-rest, falsification-wave
  adapters/electrochem/   - L1-L5 CPU, manifest, pointer, and Runpod-ready paths
  adapters/fusion/        - L1-L5 CPU, parser, manifest, reasoning, and Runpod-ready paths
  adapters/shared/        - source log, license gate, reasoner curator, Runpod dispatch
  mcp_servers/            - FastMCP servers for energy tool-calling
fixtures/
tests/
sources_log/
docs/decisions/
scripts/
tools/
```

## Quick Start

```bash
git clone https://github.com/Zer0pa/Energy-Physics-Pipeline
cd Energy-Physics-Pipeline
python3.13 -m venv .venv
.venv/bin/pip install -e '.[test,tda,mcp]'
.venv/bin/pip install pybamm pybop pypsa pvlib cantera pyscf netCDF4 freegs omas pyrokinetics qiskit mcp ripser persim
ENERGY_AUDIT_DIR=$(mktemp -d) ENERGY_KG_DIR=$(mktemp -d) bash scripts/full_check.sh
energy-physics --help
```

Runpod migration starts by setting `ENERGY_RUNPOD_BASE_URL` and flipping the target layer with `ENERGY_L?_BACKEND=runpod_rest`. The enterprise completion standard is in [`H100-ENTERPRISE-COMPLETION-PLAN.md`](./H100-ENTERPRISE-COMPLETION-PLAN.md).

## What's Next

The CPU substrate is complete. The enterprise completion wave is GPU-backed scientific execution on H100 via Runpod.

### First mandate

Minimum enterprise completion requires one serious electrochem GPU lane, one fusion or reasoner lane, live same-endpoint cutover, audit/KG provenance, full falsification/regression, and a committed handoff. A smoke test or single shaped envelope is not completion.

### H100 work plan

| Phase | Instances | Approx H100-hours | Wall clock | Notes |
| --- | --- | ---: | --- | --- |
| Runpod service bootstrap + cutover proof | 1× H100 SXM5 | 8–20 h | Day 1 | Container, CUDA stack, `UniversalLayerEnvelope` return shape, golden fixture pass |
| Electrochem GPU lane | 1× H100 SXM5 | 40–120 h | Days 2–7 | MACE-MP-0 or fairchem eSEN inference; material-manifest ingestion; audit/KG outputs |
| Fusion / reasoner lane | 1× H100 SXM5 | 60–180 h | Days 2–7 (parallel) | GyroSwin/CGYRO-facing surrogate against public DIII-D/KSTAR/IMAS scenarios; vLLM domain reasoner |
| Falsification + regression + handoff | 1× H100 SXM5 | 22–54 h | Days 8–10 | CPU vs GPU golden fixture regression, cross-model disagreement, TDA where applicable, final strict gate |
| **First wave total** | **2× H100 SXM5 (parallel)** | **180–500 H100-hours** | **~4–10 days** | **Budget cap: $2,500 at ~$4.50/hr per H100** |

Full multi-lane completion (multiple electrochem + fusion lanes, calibrated dataful campaigns): 600–1,500 H100-hours.

### Model and data dependencies

| Dependency | Source | Lane |
| --- | --- | --- |
| MACE-MP-0 universal potential | [HuggingFace `mace-mp`](https://huggingface.co/mace-community/mace-mp-0) | Electrochem L2 |
| fairchem eSEN / EquiformerV2 | [HuggingFace `fairchem`](https://huggingface.co/fairchem) | Electrochem L2 alternative |
| Domain reasoner (≥70B) | HuggingFace private pointer or vLLM-served | L4/L6 reasoner lane |
| DIII-D / KSTAR equilibrium scenarios | Public IMAS-shaped datasets; see `sources_log/` | Fusion L3–L4 |
| OQMD / Materials Project slices | Manifest-only; `energy_physics_pipeline/adapters/electrochem/data_pointers.py` | Electrochem L1 |

No bulk datasets commit to git. All data artifacts need a `SourceManifest`, checksum, and audit/KG provenance before entering the pipeline.

### Three decisions before provisioning

1. **Electrochem model:** MACE-MP-0 (faster, broad materials coverage) vs fairchem eSEN (heavier, battery-specific). MACE is faster to bootstrap the first lane.
2. **Reasoner:** vLLM-served 70B on the same H100 (needs the full 80 GB HBM) vs a smaller domain model. Decide before the fusion/reasoner pod spins up — it drives instance count.
3. **Data pointers first:** Resolve source manifests (DIII-D scenarios, OQMD slices) CPU-side before GPU time starts. See `tools/runpod_cutover_checklist.py` and `tools/verify_sources.py`.

### Operating constraints (GPU wave)

- Same boundary, falsifier, license, and audit/KG gates as CPU. No gate waivers for GPU speed.
- No Class C/D/E licensed tool enters the product path without `kg://license-grant/...` evidence.
- No bulk datasets in git; use manifests, small fixtures, checksums, private Hugging Face where needed.
- Set a 2-hour idle timeout on each pod and a hard budget kill switch before starting.
- Runpod operating runbook and artifact checksums must be committed before claiming enterprise completion.

Full gate definition: [`H100-ENTERPRISE-COMPLETION-PLAN.md`](./H100-ENTERPRISE-COMPLETION-PLAN.md).
