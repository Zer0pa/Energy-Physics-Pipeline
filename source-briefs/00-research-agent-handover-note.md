# Handover Note — Energy Vertical
**From: Architect Prime / Perplexity Research Layer**
**To: Workstream Startup Agent → Energy Orchestrator**
**Date: April 30, 2026 | Sandton, ZA**
**Re: Setup of Energy Orchestrator — context, best-of-breed picks, and first-of-kind signals**

***

## What You Are Receiving

Two deep research documents are attached:

1. **Converged Electrochemical Energy Conversion — M2S Pipeline (First Pass):** Full six-layer pipeline for batteries, green hydrogen electrolysis, PEM fuel cells, solid oxide cells, photovoltaics, and thermoelectrics. Tool catalogue, dataset catalogue, ML model catalogue, licensing classification, frontier watch, and cross-domain connections.

2. **Energy Vertical Second Pass — Fusion, South Africa, Electrochemistry LLMs, and Data Standards:** Extension covering (a) a complete fusion/plasma six-layer pipeline equivalent; (b) South Africa PGM/green hydrogen strategic context; (c) current state of electrochemistry reasoning LLMs; (d) battery data standards and device data formats.

Together these are the research foundation. The Energy Orchestrator's job is to turn them into a PRD. This note is my read-out of what is sharp, what is best-of-breed, what is genuinely first-of-kind, and what needs attention before the PRD is written.

***

## The Core Physical Thesis — Hold This Throughout

The unifying equation for the electrochemical sub-vertical is the **Butler-Volmer equation** — the same master equation governs every device (batteries, electrolysers, fuel cells, PV via the semiconductor diode analogy). This is not a convenience — it is the actual physics. The pipeline is a single physical system running under different boundary conditions, not a collection of separate tools.

For the fusion sub-vertical, the unifying equation shifts to the **Grad-Shafranov equation** (MHD equilibrium) + **gyrokinetic Vlasov-Maxwell** (plasma turbulence). The information token at Layer 4 is the **plasma equilibrium state vector** (q-profile, pressure, current density) — directly analogous to the polarisation curve V(j) in electrochemistry.

Both sub-verticals follow the same six-layer scale hierarchy. The orchestration layer (L6) is domain-agnostic. This is the design principle the Energy Orchestrator must preserve in the PRD.

***

## Best-of-Breed Picks — By Layer

### Electrochemical Sub-Vertical

| Layer | Best-of-Breed Pick | License | Why |
|-------|-------------------|---------|-----|
| L1 Electronic Structure | **PySCF 2.8** | A (Apache 2.0) | Only open Class A tool with CDFT for Marcus parameters — the kinetics anchor |
| L1 (PV/optical) | **GPAW 24.x** | B (GPL v3) | Only open tool combining GW band gaps + BSE optical spectra — essential for perovskite |
| L1 (interface dynamics) | **CP2K 2025.1** | B (GPL v2) | Best for AIMD at solid-liquid electrode interfaces — MLIP training data generation |
| L2 MLIP (molecular) | **MACE-OMol25** | A (MIT) | Trained on 100M+ DFT at ωB97M-V. 96.6% TS success rate. Best for electrolyte MD |
| L2 MLIP (solid-liquid catalysis) | **eSEN-M via fairchem** | A† (Apache 2.0) | Best on OC25 solid-liquid benchmark. Energy MAE 0.060 eV. Verify SA geography before deploy |
| L3 Mesoscale | **MOOSE + RACCOON** | B (LGPL) | Electrode fracture mechanics. PF-PINO (March 2026) is the future but license still Class E — wait |
| L4 Battery | **PyBaMM v25 + PyBOP** | A (BSD-3) | Production-ready. Matches COMSOL for 1D. Only full open-source battery + Bayesian-inference stack |
| L4 Fuel Cell / Electrolyser | **AlphaPEM** | A (MIT) | Only open MIT-licensed 1D PEM dynamic simulator validated experimentally |
| L4 SOFC | **Cantera 3.2** | A (BSD) | Best for elementary kinetics SOFC/SOEC — no semi-empirical hacks |
| L4 PV | **Solcore 6** | A (BSD) | Only open full-stack PV tool: QW → optical → transport → system. SCAPS-1D is Class C — do not use |
| L4 Surrogate | **NREL PINN Battery** | Open (NREL) | 1,000× speedup on P2D. Open-source. This is the L4→production bridge |
| L5 Systems | **PyPSA 0.31** | A (MIT) | Dominant open platform. MIT licensed. Sector-coupled. PyPSA-Earth has SA scenarios |
| L5 PV Yield | **pvlib-python 0.15** | A (BSD-3) | NREL-maintained. Direct integration with Solcore and NSRDB/ERA5 resource data |
| L5 TEA | **NREL SAM / pySAM** | A (BSD) | LCOE/LCOH financial modelling. Python API. BSD licensed |
| L6 Orchestration | **AiiDA 2.8 + Atomate2** | A (MIT/Apache) | Same stack as Materials vertical — deliberate. Domain-agnostic by design |
| L6 Bayesian opt | **BoTorch + Ax** | A (MIT) | Same stack as Health and Materials verticals |
| L6 Active learning | **PyBaMM + PyBOP loop** | A (BSD) | Closes battery design loop entirely in open-source Python |

### Fusion Sub-Vertical

| Layer | Best-of-Breed Pick | License | Why |
|-------|-------------------|---------|-----|
| L1 Nuclear | **OpenMC v0.15.2** | A (MIT) | Only open GPU-accelerated Monte Carlo. Python API. Validated for fusion geometry |
| L1 Data | **ENDF/B-VIII.0** | Public Domain | Primary US nuclear data library. Via OpenMC HDF5 |
| L2 Gyrokinetic | **GACODE (CGYRO/TGLF)** | A (Apache 2.0) | Only production-grade gyrokinetic code under a commercial-friendly license. GENE is Class C |
| L2 Surrogate | **GyroSwin** | A (MIT) | NeurIPS 2025. First 5D gyrokinetic neural surrogate. 1,000×+ speedup. MIT license |
| L2 Translation | **Pyrokinetics** | B (LGPL) | Converts between all gyrokinetic codes — the universal adapter |
| L3 MHD | **JOREK** | B (LGPL) | Leading nonlinear MHD for disruption / ELM / VDE. GPU-accelerated. ITER-validated |
| L3 Equilibrium | **FreeGS4E** | B (LGPL) | Python-native, pip-installable Grad-Shafranov with time evolution. Active April 2026 |
| L3 Boundary | **BOUT++** | B (LGPL) | Scrape-off layer / divertor fluid plasma. xBOUT Python interface |
| L4 Integrated | **OMFIT** | A (MIT) | Framework used at DIII-D/JET. Python. IMAS-compatible via OMAS |
| L4 Data exchange | **IMAS-Python v2.0 + OMAS** | B/A (LGPL/MIT) | Programmatic layer for ITER data infrastructure. Released open-source December 2025 |
| L4 UQ | **duqtools** | A (MIT) | IMAS-native UQ workflow. Ran 2,000 plasma simulations for JINTRAC validation |
| L4 CFS workflow | **MITIM** | A (MIT) | MIT/CFS integrated modelling. Used for SPARC design. pip-installable |
| L5 Neutronics | **OpenMC + DAGMC** | A (MIT) | CAD-native neutronics for blanket design. Same OpenMC as L1 — unified stack |
| L5 Geometry | **Paramak** | A (MIT) | Automated parametric CAD for fusion reactor components. DAGMC-compatible |
| L6 LLM interface | **IMAS-MCP** | A (MIT) | April 2026, brand new. ITER Organization's MCP server — LLM tool-calling into IMAS data |

***

## First-of-Kind Opportunities — Where Zer0pa Has No Competitor

### 1. Marcus Theory ↔ Shannon Information Theory — The Catalytic Volcano as a Rate-Distortion Curve
The Marcus electron transfer rate expression is mathematically identical to a Gaussian communication channel. The thermal bath is the noise source; reorganisation energy λ is noise variance; reaction free energy ΔG⁰ is signal amplitude; rate k_et is channel capacity. The volcanic curve (Sabatier principle) that governs optimal catalyst design is a rate-distortion curve. Information-theoretic optimisation methods — capacity-achieving distributions, minimum description length — map directly onto electrocatalyst design. This has been recognised in the literature but never computationally implemented. **Zer0pa's information theory tooling applied here = first-of-kind research contribution + defensible IP.**

### 2. TDA Applied to Plasma Disruption Prediction
A tokamak disruption is a fold bifurcation. Critical slowing down and growing variance before a bifurcation are well-known topological signatures in complex systems science. Persistent homology (TDA) of magnetic fluctuation time series before a disruption should reveal growing topological features. **No published application of TDA to disruption prediction exists as of April 2026.** The DIII-D open data platform and the new open disruption data standard (FED 2025) provide the training data. Zer0pa's intersectional physics toolkit makes this obvious; it is not obvious to plasma physicists.

### 3. PF-PINO as Differentiable Cellular Automaton
Allen-Cahn equation = continuous Turing morphogenesis = continuous cellular automaton. PF-PINO (March 2026) is a differentiable neural operator that solves Allen-Cahn without a mesh. SPPARKS (Sandia, GPL) is a discrete kMC cellular automaton for the same microstructure phenomena. Training PF-PINO on SPPARKS-generated trajectories would produce the first continuous, differentiable cellular automaton model for electrochemical degradation — directly usable as a gradient-based optimisation target for electrolyte composition. The connection is invisible to electrochemists; it is trivial to anyone who has worked with cellular automata and reaction-diffusion systems.

### 4. IMAS-MCP + LLM — The Fusion Reasoning Agent
ITER Organization released IMAS-MCP in April 2026 — an MCP server providing LLM tool-calling access to the entire IMAS data infrastructure. Combined with a fusion-fine-tuned reasoning LLM (DeepSeek-R1-Distill-Llama-70B, MIT license, ~$500 compute cost for fine-tuning), this is the architecture for a fusion reasoning agent that no one else is building. The IMAS open-source release (December 2025) is the enabling event — before December 2025 this was legally impossible for a non-ITER-member institution. **Zer0pa is in the first window where this is both legally and technically feasible.**

### 5. SA PGM Context — Dual Buyer-Investor Relationship
Anglo American Platinum (Amplats) and AP Ventures have stated commercial interest in expanding PEM electrolyser demand, which requires platinum. An in silico PEM OER catalyst screening service identifies platinum-optimised catalyst compositions. Amplats is simultaneously a potential buyer of the screening service and a potential investor via AP Ventures. South Africa controls 80–87% of global platinum reserves. The EU Global Gateway (€4.7bn, March 2025) is committed specifically to SA green hydrogen and the PGM value chain. **The lab is sitting on top of the raw material that every PEM electrolyser in the world depends on.**

***

## Licenses to Verify Before Build Starts

| Item | Issue | Action |
|------|-------|--------|
| **eSEN-M / fairchem** | Meta ToS may include geographic restrictions | Verify Apache 2.0 applies from South Africa before production deploy |
| **PF-PINO** | March 2026 preprint; GitHub license not confirmed | Check repo — if MIT/Apache proceed; otherwise use MOOSE+RACCOON as L3 |
| **GENE** | Class C (request to MPG) | Use GACODE/CGYRO (Apache 2.0) for commercial path; negotiate MPG separately |
| **PEMD polymer electrolyte** | License unconfirmed on GitHub | Check before incorporating into solid-state battery workflow |
| **IMAS imas_core** | Not yet publicly released | Use netCDF interface in IMAS-Python v2.0; wait for full core release |
| **SCAPS-1D** | Class C (academic only) | Do not use anywhere. Solcore (BSD) is the replacement |
| **AQCat25** | Class C (SandboxAQ, non-commercial) | Use eSEN-M + OC25 for commercial path; initiate SandboxAQ dialogue separately |

***

## Cross-Vertical Architecture — Do Not Break These

**Shared with Materials:** MACE architecture is the same model family across all three verticals. AiiDA + Atomate2 + BoTorch is the same L6 stack — deliberate, must be preserved. MatterGen/DiffCSP feeds electrode active material candidates into energy at L1.

**Shared with Health:** PINN surrogate architecture is identical across battery degradation and PKPD — only the physics equations differ. Do not build two separate PINN frameworks. PyBOP (battery) and BayBE/DrugBug (health) both wrap BoTorch — same acquisition functions, same experimental design loop.

**The principle:** The L6 orchestration engine must be domain-agnostic. It should be impossible to tell from the orchestration code whether it is proposing a drug candidate, an electrode material, or a plasma scenario. Domain-specific knowledge lives entirely in L1–L5 tool adapters.

***

## Priority Build Order

1. **Battery Digital Twin (Months 1–4):** PyBaMM + PyBOP + NREL PINN. Shortest path to revenue. $2.22B market. Buyers exist today.
2. **Green Hydrogen Catalyst Screener (Months 3–7):** eSEN-M + OC25 + AlphaPEM + PyPSA. SA PGM strategic anchor. Amplats/Sibanye as natural first commercial conversation.
3. **Perovskite PV Absorber Design (Months 5–9):** GPAW GW + Solcore + pvlib. Fastest-growing PV sub-market. No open commercial-grade alternative to SCAPS-1D.
4. **Fusion Reasoning Agent (Months 9–18):** IMAS-MCP + GyroSwin + OMFIT + fine-tuned LLM. Longest horizon, highest moat. IMAS open-source release is the enabling event.

***

## One Decision the Energy Orchestrator Must Make

The electrochemical and fusion sub-verticals share the same six-layer pattern and L6 spine but diverge completely at L1–L4. **Decision:** One PRD with Part A (Electrochemical) and Part B (Fusion) sharing the L6 specification, or two separate PRDs? Recommendation: one PRD, two parts, shared L6 — because architecture decisions made for electrochemical L6 must be fusion-compatible from day one.

***

*Two research documents are attached. This note is the lens. Hand both documents and this note to the Energy Orchestrator.*
