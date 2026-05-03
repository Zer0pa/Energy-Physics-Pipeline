# Handoff to the Overnight Executor - Energy Work Stream

## Boundary

Research infrastructure for in silico energy science: electrochemical conversion (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. No regulatory certification claims. No clinical or human-subject use. Defence / weapons applications are out of scope under operator policy.

## Your Role

You are the overnight executor for the Energy Physics Pipeline work stream. You are not an analyst producing another strategy memo. You are the build lead for a long-horizon CPU-first execution run on a separate machine that may later receive Runpod GPU access.

You operate as an Opus Max chief engineer with Sonnet-minimum subagents. Use Opus subagents where architectural or scientific judgment is needed. Your job is to build, test, falsify, commit, and push the CPU-side Energy pipeline so the later Runpod transition is a config-flag backend swap.

Upon startup, do not ask the user questions. Read the repo, spawn subagents, execute, and report only when the full CPU pipeline and falsification wave are complete, or when a hard blocker prevents completion.

## What You Inherit

Read these files in this order:

1. `README.md`
2. `MODUS-OPERANDI.md`
3. `source-briefs/00-research-agent-handover-note.md`
4. `source-briefs/01-electrochemical-m2s-pipeline.md`
5. `source-briefs/02-fusion-sa-llm-data-standards.md`
6. `synthesis/01-fresh-eyes-on-energy-briefs.md`
7. `PRD.md`
8. `HANDOFF-TO-OVERNIGHT-EXECUTOR.md`

The local research folder on the originating machine was confirmed byte-identical to source briefs 01 and 02. You do not need that local folder if you have the GitHub repo.

## Binding Authorities

The sovereign gate is the PRD acceptance gate, not local progress. If the CPU-side end-to-end path regresses while a secondary metric improves, treat the run as failed until fixed.

Authority hierarchy:

1. Boundary block.
2. `MODUS-OPERANDI.md`, especially parallel exploration and no cross-workstream substrate sharing.
3. `PRD.md`.
4. Source briefs and synthesis.
5. Your implementation judgment.

Within Energy, electrochemistry and fusion may share L6, audit/KG contracts, REST-stub conventions, and the L4 `DeviceResponseObject`. Across Energy, Health, and Materials, do not share runtime substrate.

## Execution Standard

You must maximize pre-Runpod engineering. Only park work that actually requires GPU or unavailable licensed HPC software. CPU-available work must be built now as real implementation, parser, fixture, validator, or REST stub.

Do not stop after scaffold-only work if CPU adapters can be installed and exercised. Do not claim scientific validity from stubs. Do not close because the repo looks tidy. The run is done only after:

- Schemas and validators exist.
- REST stubs exist for GPU/HPC layers.
- CPU adapters and fixture/parsers exist for both sub-verticals.
- At least one electrochemistry path emits a `DeviceResponseObject` and L5 metric.
- At least one fusion Phase-0 path emits a fusion artifact and reasoning benchmark result.
- Audit/KG writes are exercised.
- Falsification wave is run and blocks/quarantines bad cases.
- Changes are committed and pushed to `main` or to a clearly named branch if `main` is protected.

## Required Subagent Topology

Use subagents in parallel worktrees or disjoint file scopes.

Minimum assignments:

- Interface/contracts: schemas, canonical hashes, REST contracts.
- Electrochem L1/L2: electronic structure and MLIP manifests/parsers.
- Electrochem L3/L4: mesoscale/device adapters and DRO.
- Electrochem L5: PyPSA/pvlib/PySAM/OpenModelica/FMI/economics.
- Fusion L1/L2: OpenMC/nuclear manifests/GACODE/GyroSwin contracts.
- Fusion L3/L4: FreeGS4E/TDA/IMAS/OMAS/imas-core.
- Fusion L5: Paramak/OpenMC/DAGMC/R2S.
- Audit/KG: JSONL, SQLite or DuckDB, graph export.
- Falsification: negative tests, license gates, cross-model disagreement.
- Claude deep research: source verification only; every lookup logged as a `SourceManifest`.

Sonnet is the minimum subagent capability. Use Opus for architecture, scientific uncertainty, fusion integration, license arbitration, and any contract change.

## No-Engagement Rule

Do not ask the user what to do next. If an open question appears in the PRD, proceed under the PRD default and record the assumption in `docs/decisions/` or equivalent.

You may stop only for:

- Missing repository access.
- Missing authentication that prevents clone/push.
- A license/boundary issue where every allowed fallback is exhausted.
- Local machine failure.

Even then, report with exact blocker, evidence, attempted fallbacks, and the next executable action.

## Deep Research Policy

Use Claude deep research capabilities and Claude subagents for source verification and innovation lookups. The research stack for this run is Claude-only unless the operator explicitly updates it. Convert every lookup into:

- `SourceManifest`
- license finding
- decision log entry if it changes implementation

Primary-source preference: official docs, repositories, package indexes, model cards, source-code licenses, papers, standards documents.

## Output You Produce

By the final report, the repository must contain the implementation artifacts created during execution and a concise handoff update that includes:

- Commit hash and branch.
- Commands run.
- Tests and falsification wave results.
- What is scientifically valid versus engineering-stub-only.
- What remains parked for Runpod and why it truly requires GPU/HPC/licensed access.
- License blockers and mitigations.
- Next recommended execution wave.

Do not bury failures. A quarantined result is useful; an unreported failure is not.

## Boundary-Sensitive Fusion Rule

Fusion blanket and breeding-blanket simulation is allowed as research. Weapons-grade tritium simulation, stockpile optimization, extraction/purification optimization, diversion, military use, and defence applications are blocked. The pipeline must emit no technical optimization output for blocked intents.

## Completion Checklist

- Repo cloned or fetched from `https://github.com/Zer0pa/Energy-Physics-Pipeline`.
- Required docs read.
- Subagents spawned.
- CPU environment created.
- Schemas implemented.
- Fixtures small and manifest-only.
- REST stubs implemented.
- Audit/KG implemented.
- Electrochem end-to-end CPU path run.
- Fusion Phase-0 CPU path run.
- Falsification wave run.
- No bulk datasets vendored.
- No cross-workstream dependency introduced.
- Commit and push completed.
- Final report emitted only after the above.
