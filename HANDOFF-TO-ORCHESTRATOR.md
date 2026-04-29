# Handoff to the Energy Orchestrator — Energy Work Stream

You are the energy orchestrator for the Zer0pa Energy work stream. This document briefs you on what you inherit, what is expected of you, and what you produce. It does not pre-bake the structure of your PRD — that is your job. The substrate is on the table; shape it with your fresh eyes.

## Boundary

Research infrastructure for in silico energy science: electrochemical conversion (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. No regulatory certification claims. No clinical or human-subject use. Defence / weapons applications excluded under operator policy.

## What you inherit

### Source briefs (`source-briefs/`)

- **`00-research-agent-handover-note.md`** — Read first. The prior research agent's (Perplexity) self-assessment of Briefs #1 and #2. Lists best-of-breed picks per layer for both sub-verticals (electrochemical + fusion); five first-of-kind opportunities (Marcus theory ↔ Shannon channel; TDA-disruption-prediction; PF-PINO as differentiable cellular automaton; IMAS-MCP + LLM fusion reasoning agent; SA PGM dual buyer-investor); license risk flags; priority build order (battery → green H2 → perovskite → fusion); and the one decision flagged for you about PRD structure (one PRD with two parts, or two separate PRDs — the agent recommends one).
- **`01-electrochemical-m2s-pipeline.md`** — Brief #1. ~91 KB. Full six-layer M2S pipeline for batteries, green hydrogen electrolysers, PEM fuel cells, solid oxide cells, photovoltaics, and thermoelectrics. Tool catalogue, dataset catalogue, ML model catalogue, licensing classification, frontier watch. Establishes Butler-Volmer as the unifying master equation across the electrochemical sub-vertical.
- **`02-fusion-sa-llm-data-standards.md`** — Brief #2. ~76 KB. (a) Full six-layer fusion / plasma pipeline equivalent — OpenMC at L1, GACODE / GENE / Pyrokinetics / GyroSwin at L2, JOREK / FreeGS4E / BOUT++ at L3, OMFIT + IMAS-Python + duqtools + MITIM at L4, OpenMC + DAGMC + Paramak at L5, IMAS-MCP at L6. (b) South Africa PGM / green hydrogen strategic context. (c) Electrochemistry reasoning LLMs (DeepSeek-R1-Distill-Llama-70B for fine-tuning). (d) Battery data standards.

### Synthesis (`synthesis/`)

- **`01-fresh-eyes-on-energy-briefs.md`** — Fresh-eyes reading of the two briefs plus the handover note by the prior synthesis agent (Claude Opus 4.7, 2026-04-30). Surfaces:
  - The architectural reframe: the Energy vertical IS information theory applied to physical channels. The eight intersectional signals (four electrochemistry, four fusion) collapse to one principle. Marcus theory as Gaussian channel; gyrokinetic transport as 5D mutual-information flow; nuclear cross-sections as Bayesian channel capacity; disruption prediction as topological tipping point. Information-theoretic foundation should be the load-bearing architectural framing of the entire workstream.
  - The unified L4 device-response object: V(j) (electrochemistry) and the plasma equilibrium state vector (fusion) are the same kind of token — operating-condition vector → response curve + degradation trajectory + uncertainty band. **Within Energy, both sub-verticals share an L4 output schema.** This is the convergence the handover argues for at L6 — but it actually lives at L4, one layer deeper than the handover sees.
  - Twelve specific things the briefs do not see: MCP-as-productisation-surface (a complete suite of energy MCP servers as a deliverable); fusion L6 as the cheapest highest-moat starting point (4-week PoC, publishable papers); thermoelectrics as the cleanest end-to-end publishable demo (overlap with Materials surfaced for orchestrator decision); PV pipeline as architecturally cleaner than batteries (all Class A, Solcore-anchored); Amplats relationship as platform-buyer not transaction-buyer (multi-year retainer alongside campaign pricing); TDA early-warning as domain-agnostic cross-sub-vertical capability; PV L4-L5 inverter modelling gap; grid frequency-response as a missing sub-layer; funding triangulation across DOE Fusion S&T Roadmap, EU Global Gateway, Horizon Europe; fusion's free publishable-paper window in the wake of December 2025 IMAS open-source release; the within-Energy "one PRD, two parts" structure should be confirmed; the handover's cross-vertical L6 recommendation must be overridden across workstreams while preserved within Energy.
  - Pressure-test points for the orchestrator (six explicit).

## Operator override — keep workstreams independent

The research-agent handover note recommends shared L6 architecture across Health, Materials, and Energy ("MACE architecture is the same model family across all three verticals. AiiDA + Atomate2 + BoTorch is the same L6 stack — deliberate, must be preserved. ... Do not build two separate PINN frameworks").

**The operator has rejected this cross-workstream sharing recommendation.** The binding policy is the *Parallel-exploration principle* in `MODUS-OPERANDI.md`:

- Build Energy end-to-end as an independent pipeline with its own MACE deployment, its own AiiDA instance, its own BoTorch loop, its own audit log, its own KG. Architecturally identical to Materials and Health is fine; substrate-shared is not.
- Do not propose cross-workstream substrate sharing in your PRD.
- Do not depend on `Zer0pa/Health` or `Zer0pa/Materials` for any architectural component.
- Cross-pollination is allowed at the *fresh-eyes* level — you may *read* the sibling repos as reference for how parallel orchestrators approached comparable engineering problems — but the Energy pipeline is an independent build.
- The deliberate redundancy across Health, Materials, and Energy is the point.

**Within Energy the policy differs.** The research-agent handover note recommends one PRD with Part A (electrochemistry) and Part B (fusion) sharing the L6 spine. The synthesis adds: the L4 device-response object schema is also unified across both sub-verticals. **Within-workstream sharing is permitted and recommended where physics warrants it.** Two parallel sub-vertical sub-agents work simultaneously, each owning its L1-L4 stack, both contributing to a shared L6 design discussion and a shared L4-output schema. This is intra-workstream and is the structural recommendation from both the research agent and the synthesis agent.

## What you must do

Write `PRD.md` at the top of this repo. The PRD specifies a long-horizon overnight execution by a separate set of overnight-executor agents on a different machine that will eventually have Runpod GPU access. The PRD must front-load every CPU-side build before GPU bring-up.

You are expected to:

- **Apply recursive fresh eyes.** Where the prior synthesis is incomplete, close gaps. Where it sketches, lock interface contracts. Where it gestures, specify falsifiers and acceptance gates. Where it notes a frontier development, evaluate whether deeper specification is warranted. **Augment and innovate; do not paraphrase.** If your PRD is not substantively richer than the synthesis it inherited from, you have not done your job.
- **Spawn sub-agents** in parallel worktrees per pipeline layer (L1 / L2 / L3 / L4 / L5 / L6) for each sub-vertical (electrochemistry and fusion run as parallel tracks within Energy) and per cross-cutting concern you identify (falsification ledger; audit-trail schema; interface contracts; the unified L4 device-response object schema; the suite of energy MCP servers if you adopt it; the fusion L6 PoC; the cardiac-analogue MVP evidence packet; cloud-lab / wet-lab integration patterns where applicable; data-sovereignty schema; SA PGM platform-relationship pricing model).
- **Use Perplexity Pro / Gemini Advanced deep research** at the points the prior agents left open. The handover note flags seven license-verification items — three of those (eSEN-M geographic verification from South Africa; PF-PINO GitHub license; PEMD GitHub license) are deep-research lookups before any production deploy. Surface strategic lookups to the user; resolve tactical ones in the PRD itself.
- **Resolve the one decision the handover note explicitly flagged for you:** one PRD with two parts (electrochemistry + fusion sharing L6) or two separate PRDs. The handover recommends one PRD; the synthesis adds that L4 device-response object also unifies across sub-verticals. Confirm or override with reasoning.
- **Maximally front-load pre-Runpod engineering.** The PRD must specify what every overnight-executor agent does without GPU access. Acceptance criterion: when the Runpod machine comes online, the entire CPU-side of the pipeline is complete and GPU layers are stubs ready to be swapped. The cutover must be a config-flag-shaped change, not an architectural rewrite.

## Shape of the PRD

The structure is yours. Mirror the sibling Health PRD or Materials PRD if either has been written and published; depart where your fresh eyes warrant. The PRD must cover at minimum:

- **Scope and boundary** with the verbatim research-only block and the explicit MVP wedge selection (the handover recommends battery digital twin first; fusion L6 PoC may be parallel Phase 0 per the synthesis).
- **Architecture** that the overnight executor can decompose into parallel sub-streams without further user input. Specify interface contracts (CIF / SMILES / mmCIF / xyz / extxyz / FMI / SBML / IMAS-IDS / OPTIMADE / JSON Schema function calls; plus the unified L4 device-response object schema if you adopt it). Plug-replaceability invariant ("swap any layer's tool in <1 day with no downstream breakage").
- **Falsification framing** with cross-model disagreement specified as a first-class quantity flowing through the audit log; TDA-based early-warning of multi-physics failure modes as a cross-cutting capability if you adopt the synthesis recommendation.
- **Build sequence** that front-loads CPU work and stubs GPU layers; explicit parallel sub-vertical sub-agent allocation; layer order; gating test cases; the fusion L6 PoC as Phase 0 if you adopt the synthesis recommendation.
- **Agent topology** — Opus + GPT-5+ + domain LLMs (DeepSeek-R1-Distill-Llama-70B fine-tuned for fusion; what you choose for electrochemistry domain reasoner) + Perplexity / Gemini + KG with episodic memory.
- **Audit-trail spec** — campaign-grade per-discovery provenance log for electrochemistry; per-pulse / per-scenario provenance for fusion; KG schema; per-layer log shape.
- **MVP first deliverable(s)** — concrete chemistry / device choices with named systems, pre-registered acceptance thresholds, and target publishable paper(s) where applicable. The synthesis offers candidates: battery digital twin (revenue track), thermoelectric end-to-end demo (publishable track), fusion L6 reasoning-agent PoC (moat track) — you decide which, in what order, in parallel.
- **Self-bootstrapping reasoner** — how (input, simulation, output, falsifier, ground-truth) tuples flow from each campaign / scenario into a private dataset that compounds the moat. For fusion specifically, how GyroSwin fine-tuning data is curated from public DIII-D / KSTAR data.
- **AlabOS / cloud-lab / wet-lab integration plan** where applicable — for electrochemistry, this is the closed-loop synthesis layer; for fusion, this is the experimental device collaboration layer (CFS, UKAEA STEP, EUROfusion).
- **Quantum slot specification** — at the variational-engine abstraction layer or at L1 specifically; for fusion, quantum simulation of plasma physics is far-horizon and may not warrant specification.
- **Runpod migration plan** — exact stub-swap procedure; per-layer GPU requirements; cost shape; cutover acceptance gates.
- **Acceptance gates** — scientific, engineering, brain-functionality.
- **Productisation and pricing** — campaign vs platform-retainer (the synthesis flags Amplats / Sibanye / Implats / AP Ventures as platform-buyer relationships, not transaction-buyer); year-1 floor and year-3 ceiling; cross-domain transfer story; funding triangulation across DOE Fusion S&T Roadmap, EU Global Gateway, Horizon Europe, EERE H2 Hub.
- **Data-sovereignty schema** — contract structure for who owns customer DFT outputs, MLIP fine-tunes, posteriors, audit trails; for fusion, the analogous question for IMAS-IDS plasma scenario data and customer-specific scenario optimisations. Surface as open question for user if you cannot resolve.
- **The MCP server suite** — if you adopt the synthesis recommendation, specify which MCP servers Energy ships (pybamm-mcp, pvlib-mcp, alphapem-mcp, aiida-mcp, pypsa-mcp, in addition to the existing IMAS-MCP) as deliverables.
- **Open questions for the user / for the next agent** — explicitly. Things you could not resolve. Things that require user innovation input. Things the overnight executor needs that you could not prefigure. The thermoelectric scope question (Energy or Materials) is one explicit open question.

Be granular. The overnight executor is a separate agent on a separate machine with no conversation context. Every interface, every contract, every threshold, every fallback must be readable from the PRD alone.

## Constraints

- Mac storage bounded on the originating machine (~35 GiB free at last check); bulk artifacts go to private Hugging Face under Architect-Prime when offload is needed.
- HF token at `~/.cache/huggingface/token` on the originating machine. Cross-machine, the user provides.
- eSEN-M / fairchem geographic restrictions must be verified from South Africa before production deploy (handover license risk flag).
- No Docker on the originating Mac. Overnight executor on Runpod may use Docker.
- No bulk local datasets — manifests + metadata + small slices only. OPTIMADE / Materials Project API / IMAS-Python / DIII-D open-access platform are sufficient CPU-side.
- GitHub canonical. All sub-agent work commits back to `Zer0pa/Energy` before PRD finalisation.
- No regulatory or clinical claims. No human-subject inference.
- Defence / weapons applications excluded. Fusion blanket / breeding-blanket simulation is permitted as research; weapons-grade tritium simulation is not.
- **No cross-workstream substrate sharing.** See § Operator override. Within Energy, the two sub-verticals may share L6 and the L4 device-response object schema.

## Authorities and tooling

- `gh` CLI authenticated as Zer0pa-Architect-Prime on the originating machine; cross-machine, the user provides.
- HF token at `~/.cache/huggingface/token` on the originating machine; cross-machine, the user provides. eSEN-M weight access requires geographic verification first.
- Anthropic Opus 4.7 + Claude Code SDK or Anthropic Console — primary planning + code review at maximum reasoning effort.
- OpenAI GPT-5+ at xhigh reasoning — primary heavy-code generator.
- Perplexity Pro / Gemini Advanced — stuck-point and innovation deep research. Use specifically for: eSEN-M geographic verification; PF-PINO and PEMD GitHub license checks; the IMAS imas_core release status; the GENE MPG license negotiation pathway (if needed); the SandboxAQ AQCat25 dialogue (if relevant).
- LangGraph + Prefect + Parsl as a reference orchestration stack. The handover does not lock you to it.
- AiiDA 2.8 + Atomate2 0.5 + BoTorch + Ax for the L6 substrate (handover-recommended; you build your own deployment per operator override).
- IMAS-MCP (April 2026, MIT) for the fusion L6 LLM tool-calling layer.
- Combined Master Tool Selection Tables in source-briefs/01 (electrochemistry Executive Map) and source-briefs/02 (fusion executive map) — the canonical L1 → L6 tool roster for each sub-vertical.

## Where the PRD lands and what comes next

Commit `PRD.md` to the top level of `Zer0pa/Energy`. Push to GitHub. After the PRD is final, write `HANDOFF-TO-OVERNIGHT-EXECUTOR.md` describing what the next role inherits, what they produce, and the constraints / authorities they operate under. Mirror the structure of this document.

The user will then trigger the overnight execution on a separate Runpod-bound machine using a startup prompt analogous to `ORCHESTRATOR-STARTUP-PROMPT.md`.

## Success criteria

- A PRD that the overnight executor can decompose into parallel sub-streams without further user input.
- Every interface contract locked. Every falsifier specified. Every acceptance gate measurable.
- A clear MVP first-deliverable (or set of parallel deliverables) with publishable-paper targets where applicable.
- The one PRD-structure decision (one PRD two parts, or two PRDs) explicitly resolved with reasoning.
- The seven license-verification items (eSEN-M geographic, PF-PINO, PEMD, IMAS imas_core, GENE, SCAPS-1D-replacement, AQCat25) resolved or escalated to user.
- A clear plug-replaceability test that proves the architecture survives the next four frontier-model releases.
- Open questions explicitly listed so the user can innovate on the strategic ones without re-reading everything.
- No cross-workstream substrate dependency.

## What you should pressure-test before locking the PRD

The synthesis agent committed to several positions that you should pressure-test with your fresh eyes:

- **Is information theory the right architectural framing for the entire workstream?** The synthesis argues yes; you may have a stronger frame.
- **Is the unified L4 device-response object schema the right cross-sub-vertical abstraction?** Or should L4 outputs stay sub-vertical-specific?
- **Is fusion L6 PoC the right Phase-0 starting point in parallel with the electrochemistry build?** Or do you commit fully to the handover's sequential battery-first build order?
- **Is thermoelectrics in Energy or in Materials?** The synthesis flags this as an open question — you decide and document, or surface to the user.
- **Is PV the architectural reference build (cleaner) or is batteries (faster revenue) the right anchor?** Or do you build both in parallel, electrochemistry-first being the orchestrator's existing recommendation.
- **Does the MCP-as-productisation-surface argument hold, and should the PRD specify a complete suite of energy MCP servers as a deliverable?**
- **Should TDA early-warning be specified as a cross-cutting capability that serves both sub-verticals?**

These are pressure-test points, not pre-baked answers. Take them or override them with reasoning.
