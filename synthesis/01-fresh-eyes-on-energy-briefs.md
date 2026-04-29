# Fresh-Eyes Synthesis on the Energy Briefs

Synthesis-agent output. Captures the operator-read on the two source briefs (`source-briefs/01-electrochemical-m2s-pipeline.md`, `source-briefs/02-fusion-sa-llm-data-standards.md`) and the research-agent handover note (`source-briefs/00-research-agent-handover-note.md`) by Claude Opus 4.7 (1M context), 2026-04-30. Read by the energy orchestrator as the substrate for their own fresh-eyes augmentation.

## Boundary

Research infrastructure for in silico energy science: electrochemical conversion (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. No regulatory certification claims. No clinical or human-subject use. Defence / weapons applications excluded.

## Acknowledgement

The two briefs and the handover note are exceptionally strong. The handover note's best-of-breed picks per layer for both sub-verticals are right; the four corrections in the underlying briefs are right; the five first-of-kind opportunities (Marcus theory ↔ Shannon channel, TDA-disruption-prediction, PF-PINO as differentiable cellular automaton, IMAS-MCP + LLM fusion reasoning agent, SA PGM dual buyer-investor) are real; the cross-vertical "L6 must be domain-agnostic" principle is correctly identified at the architectural level; the priority build order (battery → green H2 → perovskite → fusion) is defensible. This synthesis does not repeat any of that.

## The architectural reframe — Energy is information theory applied to physical channels

The handover note lists eight intersectional signals (four electrochemistry, four fusion). Read them together and they collapse to one principle:

- Marcus electron transfer = Gaussian communication channel (rate-distortion curve = catalytic volcano).
- Gyrokinetic Vlasov in 5D phase space = continuous-time information processing system (entropy production = information decay).
- Grad-Shafranov equilibrium reconstruction = compressed-sensing inverse problem (same maths as MRI).
- Nuclear cross-section uncertainty = Bayesian channel capacity bound on reactor predictions.
- PF-PINO Allen-Cahn = continuous Turing morphogenesis = continuous cellular automaton.
- Plasma disruption = topological tipping point in a high-dimensional dynamical system (TDA).
- Polarisation curve V(j) = device-response token flowing L4→L5.
- Plasma equilibrium state vector (q-profile, p, J) = device-response token flowing L4→L5.

**The energy vertical is information theory applied to physical channels.** Not metaphor — formal correspondence. Marcus theory IS a Gaussian channel under change of variables. Phonon BTE IS a discrete information channel (already established in the Materials brief). Plasma transport IS mutual-information flow in 5D phase space. Nuclear cross-section evaluation IS Bayesian inference under a noisy measurement channel.

This is the operator's edge over every domain-native player. Domain-native plasma physicists do not have information-theoretic fluency. Domain-native electrochemists do not see Marcus as a channel. **The information-theoretic foundation should be the explicit architectural framing of the entire Energy workstream**, not a bullet list of signals at the back of the doc. The orchestrator's PRD should consider making this load-bearing.

## The deeper unification — V(j) and the plasma equilibrium state vector are the same object

The handover note names the analogy in passing: "the plasma equilibrium state vector is the natural analogue of the polarisation curve V(j) in electrochemistry." It does not draw the consequence:

**Both sub-verticals share an L4-output schema.** A "device response object" — operating-condition vector → response curve + degradation trajectory + uncertainty band — is structurally identical for batteries (V(j) under cycle conditions), electrolysers (V(j) under H2 production rate), fuel cells (V(j) under load), PV (J(V) under irradiance / temperature), thermoelectrics (S(T), σ(T), κ(T)), and tokamaks (q-profile, p, J under heating / shaping). **One L4 output schema serves both sub-verticals.**

That means the L4→L5 contract is unified across electrochemistry AND fusion. The orchestrator can specify a single `DeviceResponseObject` interface that flows from any L4 simulator into any L5 system simulator (PyPSA accepts it for grid integration; SAM accepts it for techno-economic; OMFIT accepts it for plasma scenario). **This is the convergence the handover argues for at L6 — but it actually lives at L4, one layer deeper than the handover sees.**

(Note: this unification is *within* Energy. Health and Materials each have their own response-object analogue; cross-workstream substrate sharing is not permitted under operator policy.)

## Twelve specific things the briefs and handover do not see

### 1. MCP-as-productisation-surface

IMAS-MCP (April 2026) is named in the handover as a fusion-specific tool. But MCP is a protocol pattern. The same pattern applies to:

- `pybamm-mcp` — LLM tool-calling into PyBaMM battery simulation.
- `pvlib-mcp` — LLM tool-calling for PV system performance.
- `alphapem-mcp` — LLM tool-calling for PEM fuel cell dynamics.
- `aiida-mcp` — LLM tool-calling into AiiDA workflow provenance.
- `pypsa-mcp` — LLM tool-calling for grid-system optimisation.

**Zer0pa could be first to publish a complete suite of energy-simulation MCP servers.** This is a free open-source move that captures the LLM-agentic-tooling space before anyone else does, and it generalises to the other workstreams (`pyscf-mcp`, `mace-mcp`, etc.). The MCP pattern itself becomes the productisation moat: vendors will need to be tooling-compatible to reach LLM-orchestrated buyers. Zer0pa publishes the open standard and consults on integration.

### 2. The fusion L6 is the cheapest + highest-moat starting point

The handover orders the priority build as battery → green H2 → perovskite → fusion (months 1-18). That is correct on revenue. But it misses an asymmetry:

- Electrochemistry MVP requires: full L1-L5 stack working + customer relationships + 6-12 months to demonstrate value.
- Fusion L6 demo requires: IMAS-MCP + GyroSwin (already MIT) + a fine-tuned 70B reasoning model (DeepSeek-R1-Distill, ~$500 fine-tune cost) + OMFIT querying. **4 weeks of work for a working "fusion reasoning agent" PoC.**

The fusion L6 PoC produces:
- A publishable demonstration in *Nuclear Fusion* or NeurIPS workshop.
- Open conversations with CFS, UKAEA STEP, EUROfusion, ITER (all of whom just released IMAS).
- A credibility signal that long-precedes any electrochemistry deliverable.
- An MCP-pattern proof that generalises immediately to the other priority sub-verticals.

**The fusion L6 PoC should be Phase 0 of the build, in parallel with the electrochemistry L1-L5 bring-up.** It does not delay the battery MVP; it runs in parallel with the smallest sub-agent allocation and produces credibility months earlier.

### 3. Thermoelectrics is the cleanest end-to-end publishable demo for electrochemistry

The handover treats thermoelectrics as a sub-domain of the converged pipeline. It does not see that thermoelectrics is the only electrochemistry sub-domain where the entire L1→L5 chain (DFT → phonon → ZT → device → system) is open-source and computationally tractable end-to-end. SkyRose-class materials, half-Heuslers, skutterudites are already well-characterised in literature.

**Thermoelectrics is the energy analogue of Materials' battery MVP** — a publishable, end-to-end, no-Class-D-dependency demonstration that closes the loop on a single chemistry. It does not have batteries' commercial urgency, but it has Materials' clean publishability. The orchestrator should consider thermoelectrics as a 6-week parallel publishable target alongside the battery MVP, not as a deferred sub-domain.

(Note: this overlaps with Materials' phonon stack. The orchestrator should explicitly decide: does thermoelectrics live in Energy or in Materials? Operator policy says no cross-workstream sharing, so it must live in *one* workstream and be duplicated in the other if both want it. Surface this to the user.)

### 4. PV pipeline is architecturally cleaner than batteries

The handover prioritises battery first because of revenue. But the open PV stack is more complete than the open battery stack:

- L1: GPAW (GW + BSE) — only open Class B tool combining both.
- L2: MACE-OMol25 for organic absorbers, eSEN-M for inorganic.
- L3: drift-diffusion is mostly L4 in PV.
- L4: Solcore (BSD) — multi-junction, perovskite, tandem, Schrödinger-Poisson all in one Python tool.
- L5: pvlib (BSD) — NREL-maintained, accepts spectral and temperature corrections from L4.
- System: NREL SAM (BSD) for LCOE.

**Every layer is Class A. No Class C dependencies if SCAPS-1D is replaced by Solcore.** Compare to batteries, where COMSOL-class proprietary tools dominate validation and the open chain (PyBaMM + PyBOP) is newer.

The orchestrator should make the call: easier-to-build-correctly (PV) vs faster-to-revenue (batteries). The handover takes batteries; the cleaner architectural reference build is PV.

### 5. The Amplats relationship is platform-buyer, not transaction-buyer

The handover frames it as: "Amplats wants more PEM demand → Pt screening service helps them." That is one product. The deeper structure:

**Zer0pa's pipeline becomes the strategic R&D arm for the entire SA PGM industry.** The product surface includes:
- Pt loading optimisation (less Pt per electrolyser) — a paradoxically aligned-with-buyer outcome because Amplats wants more electrolysers, not more Pt per electrolyser.
- Ir-substitution research (Ir is rarer than Pt in OER catalysts; Sibanye benefits).
- Cross-PGM substitution (Ru, Rh as alternatives) — full PGM portfolio.
- End-of-life Pt recovery from electrolysers — recycling stack.
- Anti-poisoning catalyst design — operational lifetime extension.
- Hydrogen embrittlement of structural alloys (Implats territory).

**This is a platform deal, not a project deal.** Multi-year retainer, not per-campaign pricing. The orchestrator's PRD pricing section should reflect both shapes — campaign pricing ($50K-$250K per discovery) AND platform retainer pricing (annual, multi-product). The Amplats / Sibanye / Implats / AP Ventures relationship is the multi-year anchor; campaign pricing is the per-customer unit. The handover sees the campaign; not the platform.

### 6. TDA early-warning is domain-agnostic, not fusion-specific

The handover's first-of-kind insight #2 (TDA applied to plasma disruption) is genuinely novel. The deeper insight: **persistent homology of pre-failure dynamics applies wherever a multi-physics system approaches a tipping point.**

- Tokamak disruption (handover sees this).
- Battery thermal runaway — voltage / temperature / impedance time series before runaway have growing topological features.
- Fuel cell membrane breakdown — impedance spectra before failure.
- Electrolyser stack catastrophic degradation.
- Solid oxide cell delamination at thermal cycles.

**"TDA for early-warning of multi-physics failure modes" is a domain-agnostic capability across the entire Energy workstream.** Not an electrochemistry-vs-fusion split — a unified capability that applies to both. The orchestrator should specify this as a cross-cutting library that both sub-verticals consume.

### 7. The L4→L5 bridge for PV is incomplete in the briefs

The PV stack stops at Solcore (device-level) and pvlib (system performance). The bridge between them — inverter modelling, MPPT control, grid synchronisation, frequency response — is missing. pvlib has irradiance-to-AC-output but not the dynamic inverter behaviour. OpenModelica has full power electronics; PSCAD / EMTDC is commercial.

**The PV pipeline cannot close to grid revenue without inverter modelling.** The orchestrator should flag this as either a build gap (insert OpenModelica into the L4-L5 bridge) or a deferred concern (use pvlib's static AC model, accept the loss in fidelity).

### 8. Grid frequency response is a missing sub-layer

PyPSA is L5 dispatch on hours-to-days timescale. Grid frequency response (battery providing primary frequency response, grid-forming inverters, inertia from synchronous machines) is on milliseconds-to-seconds timescale. Battery storage commercial pricing is increasingly set by frequency regulation services, not energy arbitrage.

**The L4-L5 bridge for batteries is incomplete the same way it is for PV.** The orchestrator should consider whether the pipeline includes grid-forming / grid-following control simulation. If it does, the toolchain (OpenModelica + Python control libraries + PyPSA) is open. If not, the pipeline cannot price battery storage for the most lucrative market segment.

### 9. Funding triangulation — DOE + EU + DSI + Horizon Europe

The handover names EU Global Gateway €4.7bn and DSI hydrogen roadmap. It does not name DOE Fusion S&T Roadmap (October 2025) which explicitly calls AI a key challenge area, nor Horizon Europe / EERE H2 Hub specific calls. **The orchestrator's PRD should map specific MVP deliverables to specific funding programs.** Not "build the pipeline" — "this thermoelectric demo matches Horizon Europe call X (deadline Y, budget Z)" and "this fusion-reasoning-agent matches DOE FES SciDAC partnership pattern."

The funding triangulation is a research-and-business framing device that scales the pipeline beyond commercial revenue. Ignore it and the lab leaves €5-50M on the table.

### 10. Fusion has a free publishable paper window

The December 2025 IMAS open-source release means: every closed-source-IMAS-tool that has just gone open is a publishable benchmark target. SOLPS-ITER, DINA, HCD-WF — these were ITER-Member-only until Q4 2025. **Anyone publishing a credible benchmark or extension in 2026 has automatic citation from every fusion lab that just got access for the first time.**

Specifically, the orchestrator should consider this paper sequence:
- *"GyroSwin cross-machine generalisation: training on DIII-D, validation on KSTAR, transfer to ITER geometry"* — uses open data (December 2025), open architecture (NeurIPS 2025), publishable in *Nuclear Fusion* in 6 months.
- *"Persistent homology of pre-disruption magnetic fluctuations: a TDA approach to disruption prediction"* — uses the open disruption data standard (FED 2025), no published precedent, immediately citable.
- *"IMAS-MCP + fine-tuned reasoning agent: natural language interface to integrated plasma modelling"* — first-mover paper on LLM agents for fusion.

**Three publishable papers on a 6-12 month timeline. None require GPU beyond fine-tuning. None require physical hardware.** This is the credibility signal that opens fusion conversations long before the electrochemistry MVP delivers revenue.

### 11. The handover's "one PRD, two parts" recommendation should be confirmed by the orchestrator

Within Energy, the two sub-verticals share L6 design. They do not share L1-L4 substrate. The user's parallel-exploration principle (no cross-workstream substrate sharing) does not prohibit within-workstream sharing. **One PRD with Part A (electrochemistry) and Part B (fusion) is correct; the orchestrator should commit.**

Practically: two parallel sub-vertical sub-agents work simultaneously, each owning its L1-L4 stack, both contributing to a shared L6 design discussion and a shared L4-output schema. The redundancy at L6 design (two domains stress-testing the same orchestration abstraction) is a feature, not a cost — it's exactly the parallel-exploration principle applied within Energy. The PRD specifies parallel work, not sequential.

### 12. The handover's cross-vertical recommendation is in tension with operator policy

The handover note says: "Shared with Materials: MACE architecture is the same model family across all three verticals. AiiDA + Atomate2 + BoTorch is the same L6 stack — deliberate, must be preserved. ... Do not build two separate PINN frameworks."

**The user's parallel-exploration principle has explicitly rejected cross-workstream substrate sharing.** The Materials handoff captured this as an operator override on the synthesis agent's recommendation. The Energy handoff captures the same override on the research agent's cross-vertical recommendation.

To restate the policy precisely:

- **Cross-workstream (Health ↔ Materials ↔ Energy):** No substrate sharing. Each builds its own L6 implementation, even if conceptually domain-agnostic in API shape.
- **Within Energy (Electrochemistry ↔ Fusion):** Shared L6 design and shared L4-output schema (DeviceResponseObject). One PRD, two parts.

The orchestrator's PRD should capture both halves of this and not let the within-Energy convergence drift into across-workstream convergence.

## What the orchestrator should pressure-test before locking the PRD

Same shape as Materials — pressure-test points, not pre-baked answers:

- **Is information theory the right architectural framing for the entire workstream?** The synthesis argues yes; the orchestrator may have a stronger frame.
- **Is the unified L4 DeviceResponseObject schema the right cross-sub-vertical abstraction?** Or should L4 outputs stay sub-vertical-specific?
- **Is the fusion L6 PoC the right Phase-0 starting point in parallel with the electrochemistry build?** Or is the handover's sequential battery-first ordering correct?
- **Is thermoelectrics in Energy or in Materials?** This is an explicit open question — orchestrator decides and documents, or surfaces to the user.
- **Is PV the architectural reference build (cleaner) or is batteries (faster revenue) the right anchor?** Or both in parallel.
- **Does the MCP-as-productisation-surface argument hold, and should the PRD specify a complete suite of energy MCP servers as a deliverable?**
- **Should TDA early-warning be specified as a cross-cutting capability that serves both sub-verticals?**

## What the synthesis agent recommends and the operator should override

The research-agent handover note recommends: "Shared with Materials: MACE architecture is the same model family across all three verticals. AiiDA + Atomate2 + BoTorch is the same L6 stack — deliberate, must be preserved." If the user's parallel-exploration principle holds — and I expect it does, having seen the principle applied at Materials — this cross-workstream recommendation must be captured-and-overridden. **Energy builds its own MACE deployment, its own AiiDA instance, its own BoTorch loop, even though they are architecturally identical to the Materials and Health equivalents.** This is the cost of parallel exploration. Within Energy, the two sub-verticals (electrochemistry + fusion) are permitted to share L6 and the L4 device-response object schema; that is intra-workstream and explicitly allowed.

## Provenance

- Synthesis agent: Claude Opus 4.7 (1M context).
- Source: `source-briefs/00-research-agent-handover-note.md`, `source-briefs/01-electrochemical-m2s-pipeline.md`, `source-briefs/02-fusion-sa-llm-data-standards.md`. Reference reading of sibling repos `Zer0pa/Health` and `Zer0pa/Materials` permitted at the orchestrator level for cross-workstream pattern observation only.
- Date: 2026-04-30.
- Operator override on cross-workstream substrate sharing: 2026-04-30. Captured here and in `HANDOFF-TO-ORCHESTRATOR.md` § Operator override.
- Next role: energy orchestrator (writes `PRD.md`).
