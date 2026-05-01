# H100 Enterprise Completion Plan

## Boundary

Research infrastructure for in silico energy science: electrochemical conversion (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. No regulatory certification claims. No clinical or human-subject use. Defence / weapons applications are out of scope under operator policy.

## Current status

Wave 4 made the CPU substrate ready for Runpod migration. It did not complete the enterprise Energy pipeline.

The current repo can now accept GPU backends without an architectural rewrite:

- public endpoints route through the L6 backend resolver;
- `ENERGY_L?_BACKEND=runpod_rest` is the cutover control;
- accepted outputs pass through production falsifiers and audit/KG enforcement;
- source manifests are honest: authority entries are verified or demoted;
- parallel runtime paths exist for audit/KG isolation.

That is the minimum precondition for H100 work. It is not the final authority metric.

## Enterprise completion definition

The pipeline is complete only when a GPU-backed execution wave has produced real, auditable research artifacts across both Energy sub-verticals and survived a falsification/regression wave.

Completion requires:

1. **Runpod production backend**
   - Containerized H100 service with pinned CUDA/Python/model/tool versions.
   - Health, readiness, and structured failure endpoints.
   - `UniversalLayerEnvelope` JSON responses with byte-identical boundary block.
   - Artifact storage with checksums and no bulk repo commits.
   - Budget cap, timeout, and kill switch.

2. **Live same-endpoint cutover**
   - Existing public endpoints, not special demo routes, must switch via config.
   - `ENERGY_RUNPOD_BASE_URL` plus `ENERGY_L?_BACKEND=runpod_rest` must be sufficient.
   - Golden fixtures must preserve schema, DRO shape, boundary, falsifier IDs, and allowed output projections.

3. **GPU-backed scientific lanes**
   - At least one electrochemistry GPU lane: MACE / fairchem / eSEN inference or fine-tune path against material manifests.
   - At least one fusion GPU lane: GyroSwin / CGYRO-facing surrogate lane using public DIII-D / KSTAR / IMAS-shaped scenarios.
   - L4/L6 reasoner lane: domain reasoner via vLLM or equivalent, with refusal, provenance, and science-bench evaluation.
   - Optional high-value expansions: OpenMC GPU transport, GPAW/GW, OpenMC R2S, larger PyBaMM/PyBOP sweeps.

4. **Dataful execution**
   - Use source manifests, authoritative small slices, and object-store/HF private pointers.
   - No canned-only fixtures as the completion evidence.
   - No bulk local datasets in git.
   - Every data artifact has a `SourceManifest`, checksum, license/rights status, and audit/KG provenance.

5. **Falsification and regression**
   - Production falsifier wave passes against GPU outputs.
   - CPU vs GPU golden fixture regression passes.
   - Cross-model disagreement gates run and record disagreement, not just pass/fail.
   - TDA early-warning is run where a multi-physics trajectory exists.
   - Boundary, license, and forbidden-use gates remain hard gates.

6. **Enterprise handoff**
   - Exact environment, model versions, data pointers, checksums, commands, failure modes, and recovery steps are committed.
   - Final report distinguishes scientific-valid, engineering-stub, manifest-only, and blocked work.
   - No readiness claim is made unless the full gate passes.

## H100 work packages and hours

The estimates below are H100-hours unless stated otherwise. Wall-clock assumes one provisioned H100 running continuously, with normal dependency failures and reruns.

| Work package | H100-hours | Purpose |
|---|---:|---|
| Runpod image/service/bootstrap | 8-20 | Container, CUDA stack, API, health checks, envelope return shape. |
| Live same-endpoint cutover | 8-16 | Set `ENERGY_RUNPOD_BASE_URL`, flip one layer, pass golden fixture and structured-failure tests. |
| vLLM domain reasoner lane | 30-80 | Serve selected domain reasoner; run fusion/electrochem reasoning bench, refusal tests, provenance. |
| Electrochem GPU lane | 40-120 | MACE/fairchem/eSEN inference or fine-tune; material-manifest ingestion; audit/KG outputs. |
| Fusion GPU lane | 60-180 | GyroSwin / CGYRO-facing surrogate; public DIII-D/KSTAR/IMAS scenario curation; calibration metrics. |
| Cross-model/TDA/falsification wave | 20-60 | CPU vs GPU regression, disagreement thresholds, TDA early warning, production falsifiers. |
| Audit/KG/artifact hardening | 10-30 | Object-store pointers, checksums, parallel runtime paths, replayable provenance. |
| Final full regression and handoff | 12-24 | Full strict gate, report, Runpod operating runbook, next-wave backlog. |

## Completion bands

| Band | Definition | H100-hours | One-H100 wall clock |
|---|---|---:|---:|
| Not acceptable as completion | Service smoke test or one endpoint returning a shaped envelope. Useful only as setup evidence. | 8-24 | 0.5-1 day |
| Minimum enterprise completion | One serious electrochem GPU lane, one serious fusion or reasoner lane, live same-endpoint cutover, audit/KG, falsification, regression, handoff. | 180-500 | 8-21 days |
| Full multi-lane Energy completion | Multiple electrochem + fusion GPU lanes, calibrated dataful campaigns, cross-model/TDA coverage, repeatable operational handoff. | 600-1500 | 25-63 days |

## Recommended first H100 mandate

The first H100 agent should not stop at a smoke test. Its mandate is:

1. Build and deploy the Runpod H100 service.
2. Prove live same-endpoint cutover for one electrochem endpoint and one fusion endpoint.
3. Complete one GPU-backed electrochem lane.
4. Complete one GPU-backed fusion or reasoner lane.
5. Run the full falsification/regression wave against GPU outputs.
6. Commit a final enterprise readiness report or a precise next hardening brief.

Expected first serious wave: **180-500 H100-hours**.

## Operating constraints

- No regulatory, certification, clinical, human-subject, defence, or weapons claims.
- Fusion blanket / breeding-blanket research is allowed; weapons-grade tritium simulation is not.
- No cross-workstream substrate sharing with Health or Materials during build.
- Within Energy, electrochemistry and fusion may share L6 and the L4 `DeviceResponseObject`.
- No bulk datasets in git. Use manifests, small fixtures, and private object storage / private Hugging Face where needed.
- Class C/D/E or unresolved licenses stay blocked unless a `kg://license-grant/...` evidence node exists.
