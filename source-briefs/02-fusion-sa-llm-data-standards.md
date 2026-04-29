# Energy Vertical — Second Pass: Fusion, South Africa, Electrochemistry LLMs, and Data Standards
**Companion to the Converged Electrochemical Energy Conversion M2S Pipeline | Zer0pa Frontier AI Orchestration Lab | April 2026**

***
## How to Use This Document
This brief extends, not replaces, the first-pass M2S pipeline survey. Gap 1 (Fusion and Plasma Physics) is treated as a full pipeline equivalent — the same six-layer structure, full tool catalogue, datasets, ML models, frontier watch, intersectional signals, and commercial value map as the electrochemical brief. Gaps 2–4 (South Africa energy context, electrochemistry reasoning LLMs, and battery data standards) are focused sections. Read the first-pass brief for the electrochemical pipeline context; use this document as the precision complement.

***
# Part 1: Fusion and Plasma Physics Simulation Stack
## 1.1 Executive Map — Top-3 Tools Per Layer
| Layer | Role | Tool 1 | Tool 2 | Tool 3 | License Class |
|-------|------|--------|--------|--------|---------------|
| L1 — Nuclear/Atomic | Monte Carlo neutron/photon transport | OpenMC v0.15.2 | ENDF/B-VIII.0 (data) | JEFF-3.3 (data) | A / Public Domain |
| L2 — Gyrokinetic | Plasma microturbulence, anomalous transport | GACODE (CGYRO, TGLF) | Pyrokinetics | GENE | A / B / C |
| L3 — MHD/Equilibrium | Magnetohydrodynamics, plasma equilibrium, disruption | JOREK | FreeGS / FreeGS4E | BOUT++ | B / B / B |
| L4 — Integrated Transport | Full plasma scenario modelling, IMAS data exchange | OMFIT | IMAS + IMAS-Python | duqtools | A / B / A |
| L5 — Reactor Engineering | Neutronics, tritium breeding, activation | OpenMC + DAGMC | Paramak | FusionCat/TENDL | A / A / Open |
| L6 — Orchestration | Workflow management, Bayesian optimisation, active control | OMFIT (modules) | OMAS | MITIM | A / A / A |

***
## 1.2 The Unifying Physical Substrate
The governing equations of fusion plasma physics span five decades of length scale and a corresponding hierarchy of approximations. At the nuclear level, the Boltzmann transport equation governs neutron and photon propagation through matter. At the kinetic level, the gyrokinetic Vlasov-Maxwell system — a 5-dimensional phase-space description obtained by averaging over fast gyro-motion — governs plasma microturbulence. At the fluid level, the magnetohydrodynamic (MHD) equations govern macroscopic plasma equilibrium and large-scale instabilities. At the engineering level, the integrated 0D/1D transport equations govern radial power balance and plasma scenario evolution.[^1][^2][^3][^4]

The **plasma equilibrium state vector** is the natural analogue of the Butler-Volmer polarisation curve in electrochemistry. It is the q-profile (safety factor profile, \( q(r) = rB_\phi / (R B_\theta) \)), pressure profile \( p(r) \), current density distribution \( J(r) \), and plasma shape parameters (elongation \(\kappa\), triangularity \(\delta\), Shafranov shift). These form the boundary conditions that connect all six layers: L1 provides neutron/photon sources and material activation; L2 provides anomalous heat and particle transport coefficients; L3 provides the MHD equilibrium consistent with those profiles; L4 integrates them into a self-consistent scenario; L5 assesses breeding blanket and materials performance; L6 optimises the whole system.[^5]

**The data exchange standard for the equilibrium state vector is the IMAS Interface Data Structures (IDS) format** — specifically the `equilibrium` IDS within the IMAS Data Dictionary. Every simulation code in the ITER ecosystem that exchanged equilibrium data does so via this IDS. The IDS is a device-agnostic, hierarchical data structure with formally specified units and coordinate conventions. IMAS-Python v2.0.0 (LGPL-3.0) provides the Python interface.[^6][^7]

***
## 1.3 Layer-by-Layer Resource Map
### L1 — Nuclear/Quantum: Cross-Section Data and Monte Carlo Transport
**OpenMC** (v0.15.2, MIT license, `openmc.org`, `openmc-dev/openmc`) is the primary open-source code for Monte Carlo neutron and photon transport. It is GPU-accelerated (CUDA, ROCm, SYCL) achieving performance portability across AMD, NVIDIA, and Intel GPU architectures, validated at scale on Frontier, Polaris, and Aurora supercomputers. OpenMC has a full Python API (`pip install openmc`), supports CAD geometry via DAGMC, and is validated for fusion-specific applications including FNG-streaming benchmark cases.[^8][^9][^10][^11]

A critical November 2024 extension demonstrates **OpenMC for atomic transport and plasma-wall interaction**, showing compatibility with the DEGAS2 code commonly used for neutral particle transport in fusion boundary plasmas. This bridges L1 and L5 — the same code framework handles neutron transport for blanket design and atomic physics for plasma-facing materials.[^8]

**Nuclear cross-section databases (all public domain):**
- ENDF/B-VIII.0 (US, NNDC): the primary US evaluated nuclear data library[^12]
- JEFF-3.3 (Europe, NEA): covers actinides and fission products relevant to D-T fusion activation
- JENDL-5 (Japan, JAEA): strong coverage of activation products relevant to structural materials
- TENDL (EUROfusion): fusion-specific activation library; open access via NEA

**ML cross-section emulation:** The January 2026 Nature Scientific Reports paper evaluates machine-learning-based reduction of cross-sections and energy grid for OpenMC transport calculations. The FECSG-ML approach (Feature Engineering for Cross Section Generation with ML) demonstrates that ML surrogate cross-sections can replicate full pointwise results with significantly reduced memory and computation. These approaches are viable for fast activation screening and uncertainty propagation but are not yet production-grade replacements for evaluated nuclear data libraries.[^13][^12]

| Tool | License Class | Python API | GPU Support | Key Limitation |
|------|---------------|------------|-------------|----------------|
| OpenMC v0.15.2 | A (MIT) | Yes (`pip install openmc`) | Yes (CUDA/ROCm/SYCL) | Continuous-energy mode memory-intensive for full core |
| ENDF/B-VIII.0 | Public Domain | Via OpenMC | N/A | Data, not code |
| JEFF-3.3 | Public Domain (NEA) | Via OpenMC | N/A | Data, not code |
| JENDL-5 | Public Domain (JAEA) | Via OpenMC | N/A | Data, not code |

***
### L2 — Kinetic/Gyrokinetic: Plasma Microturbulence and Transport
The gyrokinetic equation is the most computationally expensive component of the fusion simulation stack. It evolves a 5-dimensional distribution function \( f(x, y, z, v_\parallel, \mu, t) \) — three real-space and two velocity-space dimensions — describing ion and electron perturbations around a guiding centre drift. A single nonlinear gyrokinetic simulation can take weeks on a modern HPC cluster, making it the dominant ML surrogate target in fusion.[^3][^14]

**GACODE** (General Atomics, Apache 2.0, `gafusion/gacode`, `pip install gacode`): The complete fusion transport simulation suite including GYRO, CGYRO (optimised successor), TGLF (reduced quasilinear turbulent transport model), NEO (neoclassical transport), and PROFILES_GEN. CGYRO is a global-spectral code solving the 5-D gyrokinetic-Maxwell equations. GACODE is released under Apache 2.0 — fully commercialisable. Released by General Atomics as of 2024.[^15][^16]

**GENE** (Gyrokinetic Electromagnetic Numerical Experiment, MPI/LRZ, `genecode.org`): One of the most widely validated gyrokinetic codes. The March 2025 Nature Communications paper presents "an unprecedented comparison of plasma turbulence between experiment and simulation, proving that the gyrokinetic model GENE accurately predicts measured turbulence characteristics". However, GENE uses a **"Free Customised Licence (request to MPG)"** — it is not open-source in any commercial sense. Class C: academic/non-commercial only. Cannot be deployed in a commercial pipeline without explicit MPG licence negotiation.[^17][^18][^4]

**GS2** (Culham, maintained): Well-established gyrokinetic code with free boundary conditions. Academic licence; Class C.

**Pyrokinetics** (LGPL, `pyro-kinetics/pyrokinetics`): Python library that standardises gyrokinetic analysis and converts input files between all major gyrokinetic codes — CGYRO, GS2, GENE, TGLF, GKW, STELLA, GX. The one-stop Python interface for the entire gyrokinetic ecosystem. Class B (LGPL outputs commercialisable).[^19][^20]

**ML surrogates for gyrokinetic transport:**

- **GyroSwin** (October 2025, NeurIPS 2025, `ml-jku/neural-gyrokinetics`): The first scalable 5D neural surrogate for nonlinear gyrokinetic plasma turbulence simulations. Extends a hierarchical Swin Transformer to five dimensions, trained on the full 5D distribution function. Demonstrated to outperform widely-used reduced numerics (TGLF) on heat flux prediction and to capture the turbulent energy cascade. License: MIT (confirmed on GitHub). This is the most significant 2025 ML development for L2 simulation.[^21][^22][^23][^14]
- **Neural Network / Gradient-Boosted Decision Tree surrogates for TGLF** (EFTC 2025): Comparison of ML surrogate approaches for turbulent transport modelling in tokamak plasma scenarios, comparing NN versus GBDT architectures for predicting TGLF transport coefficients. Both achieve < 5% error on validation set at 1,000–10,000x speedup.[^24][^25]
- **Stochastic Variational Gaussian Processes for transport surrogates** (AIP Physics of Plasmas, October 2025): Produces transport model surrogates applicable to medium-to-large tokamak devices with uncertainty estimates.[^26]

| Tool | License Class | Python API | GPU Support | Key Limitation |
|------|---------------|------------|-------------|----------------|
| GACODE (CGYRO/TGLF) | A (Apache 2.0) | Yes (gacode Python bindings) | Yes | Complex setup on new platforms |
| GENE | C (academic request) | Via Python wrappers | Yes (CUDA) | Cannot commercialise without MPG licence |
| GS2 | C (academic) | Partial | No | Slower than CGYRO for large simulations |
| Pyrokinetics | B (LGPL) | Yes (`pip install pyrokinetics`) | N/A | Translation layer only; needs underlying code |
| GyroSwin | A (MIT) | Yes (Python) | Yes | Training on limited dataset; not yet validated on reactor-class geometry |

***
### L3 — MHD/Equilibrium: Plasma Shape, Stability, and Disruptions
**JOREK** (nonlinear MHD, LGPL, `jorek.eu`): The leading open-source code for nonlinear resistive MHD simulations of tokamak X-point geometries. JOREK is used for disruption physics, ELM (Edge Localised Mode) dynamics, VDE (Vertical Displacement Events), kink modes, and free-boundary instabilities via JOREK-STARWALL coupling. A January 2025 Plasma Physics and Controlled Fusion paper describes "Self-consistent full MHD coupling of JOREK and STARWALL for advanced plasma free boundary simulation". JOREK supports GPU acceleration and is the code used in the ITER IMAS December 2025 release announcement for disruption simulation visualisation. Class B (LGPL; simulation outputs fully commercialisable).[^27][^28][^6][^29]

**FreeGS** (LGPL, `freegs-plasma/freegs`, `pip install freegs`): Python-native free-boundary Grad-Shafranov equilibrium solver. Currently at v0.6.1. FreeGS4E (`freegs4e/freegs4e`, LGPL-3.0) is an actively maintained fork providing time-evolution capability for dynamic equilibrium (last PyPI release April 2026). FGE (Fast Free-Boundary Grad-Shafranov Evolutive, arXiv December 2025) is an independent new solver that self-consistently couples the Grad-Shafranov equation with circuit equations for external conductors — more complete physics than FreeGS for advanced scenario design.[^30][^31][^32][^33][^34]

**BOUT++** (LGPL, `boutproject/BOUT-dev`): Framework for plasma fluid simulations in curvilinear geometry, primarily for boundary plasma (scrape-off layer, divertor) simulations. Jointly developed by University of York, LLNL, CCFE, DCU, DTU. Python interface via xBOUT (`pip install xbout`). Class B.[^35][^36]

**GVEC** (LGPL, April 2026, JOSS): New flexible 3D MHD equilibrium code for stellarator and tokamak configurations. Relevant as private fusion companies (Commonwealth Fusion, Renaissance Fusion) pursue both tokamak and stellarator designs.[^37]

**Disruption prediction (ML):** Plasma disruptions are the single highest-risk operational failure mode in tokamaks — uncontrolled termination of the plasma that can damage first-wall components. At reactor scale (ITER), the disruption rate must be < 1 in 200 pulses. The ML disruption prediction ecosystem is mature:[^38]

- Cross-machine transfer learning (2023 Nature Communications Physics): ML model trained on a smaller tokamak (AUG) successfully predicts disruptions on a larger one (JET), validated for cross-machine knowledge transfer[^39]
- DIII-D + JET cross-machine disruption prediction using deep CNN (2022/2025 paper confirms cross-machine applicability)[^40]
- E-CAAD model (IAEA FEC 2025): Demonstrates effective cross-machine disruption classification[^41]
- Open-source disruption data exchange standard (Fusion Engineering and Design, 2025): Proposes two open-source standards on GitHub for sharing disruption data for ML training across fusion machines. This is the OPTIMADE-equivalent for disruption data.[^42]

| Tool | License Class | Python API | GPU Support | Key Limitation |
|------|---------------|------------|-------------|----------------|
| JOREK | B (LGPL) | Partial (Python analysis tools) | Yes | Complex setup; Fortran core |
| FreeGS 0.6.1 | B (LGPL) | Yes (pure Python) | No | Static equilibrium only; FreeGS4E for dynamics |
| FreeGS4E | B (LGPL-3) | Yes (`pip install freegs4e`) | No | Fork maintenance; may diverge |
| BOUT++ | B (LGPL) | Yes (xBOUT) | Partial | Boundary physics only |
| GVEC | B (LGPL) | Yes (Python bindings) | No | New (2026); limited validation |

***
### L4 — Integrated/Core Transport: Full Plasma Scenario Modelling
The December 8, 2025 ITER announcement is the most important single event in the fusion simulation open-source ecosystem since the field began: **the complete IMAS (Integrated Modelling and Analysis Suite) was released as open source on GitHub at `github.com/iterorganization`**. This release includes:[^6][^43][^44]
- Infrastructure software for IMAS Data Dictionary (IDS) manipulation
- SOLPS-ITER (edge plasma: B2.5 + EIRENE) — previously restricted to ITER Members
- SOLPS-GUI (graphical interface for SOLPS-ITER)
- DINA Plasma Simulator (tokamak scenario modelling)
- Heating & Current Drive Workflow (HCD-WF)
- Additionally, METIS, CHEASE, GACODE, NICE released by their respective institutions in alignment with this effort[^6]

**IMAS-Python v2.0.0** (LGPL-3.0, `pip install imas`): Pure Python library for working with IDS data structures from the IMAS Data Dictionary. Released March 2025. This is the programmatic access layer for all IMAS data exchange — `imas.load_imas_entry()`, IDS read/write, netCDF file interface. The core Access Layer (`imas_core`) is not yet publicly available, limiting some functionality, but the netCDF interface enables data sharing. Class B (LGPL).[^7]

**OMFIT** (MIT, `omfit.io`): The integrated modelling and data analysis framework used at DIII-D, JET, and other tokamaks. OMFIT interfaces with IMAS via the OMAS Python library and organises modelling tasks into modules covering transport, equilibrium, neutral beam injection, ECH, and machine-specific data structures. MIT licensed — fully commercialisable. The `GYRO_GACODE` module in OMFIT directly interfaces with CGYRO for turbulent transport modelling. Python-native, `pip install omfit-core`.[^45][^46][^47]

**OMAS** (MIT, `gafusion/omas`, `pip install omas`): Ordered Multidimensional Array Structure — Python library for IMAS data exchange, providing a simplified interface between Python codes and IMAS IDS. Developed at General Atomics. MIT licensed. The primary programmatic bridge between OMFIT, experiment data, and IMAS-compliant simulation codes.[^5][^48]

**duqtools** (open source, arXiv January 2025): Python workflow tool for uncertainty quantification and large-scale validation of fusion modelling simulations. Demonstrated running 2,000 different IMAS-based plasma simulations for JINTRAC model validation. Directly relevant to Zer0pa's BoTorch-based active learning layer.[^49]

**MITIM** (MIT Integrated Modelling, MIT license, `pabloprf/MITIM-fusion`, `pip install MITIM-fusion`): Light-weight Python toolbox for plasma physics modelling tasks at CFS/MIT — optimisation, profile analysis, transport modelling integration. MIT licensed. Used by CFS for SPARC design.[^50][^51]

| Tool | License Class | Python API | GPU Support | Key Limitation |
|------|---------------|------------|-------------|----------------|
| IMAS full suite | B/A (LGPL/Apache, mixed) | Yes (IMAS-Python, LGPL) | Via codes | imas_core not yet public; some IDS paths require institutional access |
| OMFIT | A (MIT) | Yes (Python framework) | Via codes | Monolithic; steep learning curve |
| OMAS | A (MIT) | Yes (`pip install omas`) | N/A | Access layer, not simulation code |
| SOLPS-ITER | B (LGPL, newly released) | Via IMAS | Yes (partial) | Complex boundary conditions; significant user expertise required |
| MITIM | A (MIT) | Yes (`pip install`) | No | CFS-specific workflows; generalisation requires adaptation |
| duqtools | A (MIT/open) | Yes | N/A | Not a simulation code; orchestration only |

***
### L5 — Reactor Engineering: Neutronics, Breeding Blanket, Activation
**OpenMC + DAGMC** (MIT): Direct Accelerated Geometry Monte Carlo (DAGMC) enables OpenMC to operate on CAD-native geometry (STEP files), eliminating the need to convert complex reactor geometries to constructive solid geometry format. This is the standard approach for tritium breeding blanket (TBB) neutronics analysis. The complete chain is: CAD (FreeCAD or commercial) → DAGMC → OpenMC → activation analysis.[^9][^10]

**Paramak** (MIT, `fusion-energy/paramak`): Automated parametric 3D CAD model generation for fusion reactor components. Open-source, Python, generates geometry compatible with OpenMC/DAGMC. Enables rapid design-space exploration for blanket geometry without commercial CAD.[^52]

**R2S-ACT** (Rigorous 2-Step Activation): Standard methodology for fusion activation analysis — neutron transport (OpenMC) provides neutron flux maps; FISPACT-II or similar codes compute time-dependent activation inventories. FISPACT-II is available to researchers under UKAEA licence (Class C/E).

**Fusion neutron activation libraries:** TENDL (TALYS-based Evaluated Nuclear Data Library, EUROfusion/NEA): fusion-specific activation data, open access. Complementary to JEFF and ENDF for fusion-relevant reaction channels.

**ML for materials damage:** Physics-informed surrogate models for displacement damage (dpa) as a function of neutron spectrum and fluence are an active research area. No production-grade open-source tool found as of April 2026; this is an open build target.

***
### L6 — Orchestration: Workflow Management and Bayesian Optimisation
OMFIT serves as the primary orchestration layer for the fusion simulation ecosystem — it connects codes at L1–L5 through a unified Python framework with a tree-structured data model. The OMFIT + OMAS + IMAS architecture provides what AiiDA+Atomate2 provides for the materials science stack: provenance tracking, workflow management, and code-to-code data exchange.[^45][^46]

**Bayesian optimisation for plasma scenarios:** The October 2025 Nature Communications Physics paper demonstrates high-fidelity data-driven dynamics models for reinforcement learning-based tokamak control. RL-based plasma control is deployed experimentally at DIII-D (General Atomics) and TCV (EPFL). The DOE Fusion S&T Roadmap (October 2025) explicitly calls out AI as a key challenge area, including "Improving fusion system performance and design using AI".[^53][^54][^55]

**Physics-Informed Meta-instrument (PiMiX)** (January 2024): Multi-modal integrated diagnostic-to-control workflow using deep neural networks — connecting multi-instrument data fusion with multiphysics modelling for plasma control.[^56]

**IMAS-MCP** (April 2026, `iterorganization/imas-mcp`): The ITER Organization has released an IMAS Model Context Protocol (MCP) server providing 8 specialised tools for natural language queries over IMAS data paths, including semantic search over the IMAS Data Dictionary. This is the tool-calling interface that connects LLMs to the IMAS data infrastructure — directly relevant to Zer0pa's orchestration layer. Available at `github.com/iterorganization/imas-mcp`. MIT license.[^57]

***
## 1.4 Dataset and Database Catalogue
| Dataset | Description | Size | License | Access | ML-Ready |
|---------|-------------|------|---------|--------|----------|
| ITER IMAS Data Dictionary | Device-agnostic IDS schema for all plasma data | Schema only | LGPL (infrastructure) | GitHub: iterorganization | Via IMAS-Python |
| DIII-D Open Access Fusion Data Platform | Experimental plasma data from DIII-D tokamak (General Atomics) | Large (decades) | Open access | Via OMFIT/MDSplus | Partial; MDSplus format |
| JET Final Campaign (DTE3, 2023) | Final DT campaign data; UKAEA[^58][^59] | Multi-TB | UKAEA open access (negotiated) | Via UKAEA data portal | Requires preprocessing |
| ENDF/B-VIII.0 | US evaluated nuclear data library | ~4 GB | Public domain (NNDC) | HDF5 download | Yes (OpenMC) |
| JEFF-3.3 | European nuclear data library | ~2 GB | Public domain (NEA) | HDF5 download | Yes (OpenMC) |
| JDDB (J-TEXT Disruption Database) | Lightweight extensible disruption database[^60] | ~1,000 shots | Academic (negotiated) | IAEA INDICO 2025 | Partial |
| Open disruption exchange standard | Cross-machine disruption data in standardised format[^42] | Growing | Open (GitHub) | GitHub | Yes |
| KSTAR | Korean tokamak experimental data | Large | Restricted (NFRI) | Application-based | No |

**The DIII-D open access platform** (hosted by General Atomics): includes DIII-D and MAST experimental data with automated data analysis tools. The DOE Fusion S&T Roadmap confirms the open access platform as a strategic national infrastructure.[^54]

**JET data:** The final D-T campaign (DTE3, 2023) is documented in a 2025 Insights paper (UKAEA). Full raw data release timeline is linked to decommissioning programme; partial data available through publications and on-request to collaborators. The UKAEA decommissioning program makes JET a historical dataset.[^58][^59][^61]

***
## 1.5 ML Models Catalogue
| Model | Architecture | Task | License | Interface | Limitation |
|-------|-------------|------|---------|-----------|------------|
| GyroSwin | 5D Swin Transformer | Nonlinear gyrokinetic turbulence surrogate[^21][^23] | A (MIT) | PyTorch, HuggingFace | Validated on limited CGYRO training data; not yet reactor geometry |
| NN/GBDT for TGLF | Neural network / gradient boosting | Quasilinear transport surrogate[^24][^25] | Open (paper) | Python (paper code) | Quasilinear only; TGLF physics regime |
| SVGP transport surrogate | Stochastic Variational GP | Turbulent heat/particle transport[^26] | Open | Python | Uncertainty quantification focus; medium-device validated |
| Cross-machine disruption CNN | Deep CNN | Disruption prediction (JET/DIII-D)[^40] | Academic | Python | Cross-machine transfer accuracy degrades with geometry gap |
| E-CAAD disruption model | ML ensemble | Cross-machine disruption precursor detection[^41] | Academic | Python (IAEA submission) | Not publicly released |
| Runaway electron surrogate | Deep learning + physics constraints | Runaway electron avalanche growth rate[^62] | Academic (Cambridge) | Python | Niche application; reactor safety |
| PiMiX | Neural network, multi-modal | Integrated diagnostic-to-control[^56] | Academic | Python | Research prototype |

**Foundation models for fusion:** No published foundation model trained on the full IMAS IDS corpus exists as of April 2026. The IMAS-MCP server (April 2026, `iterorganization/imas-mcp`) provides the tool-calling interface that would enable a frontier LLM to query IMAS data. This is the correct architecture for the Zer0pa L6 orchestration layer: LLM + IMAS-MCP tool-calling, not a bespoke fine-tuned model.[^57]

***
## 1.6 Private Fusion Company Simulation Infrastructure
**Commonwealth Fusion Systems (CFS):** Has a public GitHub organisation (`cfs-energy`) and has published SPARC physics in the Journal of Plasma Physics (2020–2021, full series). CFS uses MITIM for integrated modelling and scenario optimisation. SPARC design uses GACODE/TGLF, MHD equilibrium codes, and engineering simulation. CFS's philosophy (publicly stated) is that SPARC combines "decades of knowledge of plasma physics from dozens of tokamaks around the world with cutting-edge simulation tools and data analysis".[^50][^51]

**Helion Energy:** Field-reversed configuration (FRC) concept. No public simulation code repository found. Uses proprietary plasma simulation codes for FRC compression dynamics — a fundamentally different equilibrium topology than tokamak, not well-served by JOREK or GACODE.

**TAE Technologies:** Also FRC-based. No public simulation tools found.

**Zap Energy:** Flow Z-pinch concept. No public simulation tools found.

**UK Atomic Energy Authority (UKAEA) — STEP Programme:** The Spherical Tokamak for Energy Production programme has an explicit digital twin strategy. The STEP digital strategy builds around "a digital twin of the whole plant" evolving from system architecting codes. STEP uses PROCESS (systems code), BLUEMIRA (Python, MIT-like, STEP open-source CAD/engineering tool), and ITER IMAS infrastructure.[^63][^64]

**IAEA 2025 World Fusion Outlook:** Confirmed that the fusion energy landscape "continues to develop at an extraordinary pace" with 40+ private companies active. The capitalization of fusion startups through April 2026 exceeds $5B collectively.[^65][^66]

***
## 1.7 Frontier Watch (2024–2026)
1. **IMAS Open Source (December 2025):** The ITER Organization released IMAS, SOLPS-ITER, DINA, and HCD-WF under open-source licenses. This single event opens the entire ITER integrated modelling infrastructure to private companies for the first time. Before December 2025, IMAS was restricted to ITER Member institutions. This is the fusion equivalent of AlphaFold2 going open-access.[^6]

2. **GyroSwin — 5D Gyrokinetic Neural Surrogate (NeurIPS 2025):** First scalable 5D neural surrogate for nonlinear gyrokinetics — reduces a simulation that takes weeks to minutes while matching physics on heat flux and energy cascade. MIT license, available on GitHub. This is the GyroSwin paper's primary claim to significance: it addresses the single biggest computational bottleneck in fusion plasma design.[^21][^23]

3. **JOREK-STARWALL Free-Boundary Coupling (2025):** Self-consistent full MHD coupling of plasma, vacuum, and conducting structures for advanced disruption simulation. Critical for ITER and private device disruption mitigation design.[^28]

4. **GENE Milestone — Experiment-Simulation Agreement (March 2025, Nature Communications):** Unprecedented quantitative agreement between GENE gyrokinetic simulations and experimental turbulence measurements, validating the gyrokinetic model for reactor predictions. This validates the ML surrogate training data quality.[^4]

5. **Open Disruption Data Standard (FED 2025):** Proposed open-source standard for sharing disruption machine protection data across tokamaks — the OPTIMADE moment for disruption databases.[^42]

6. **IMAS-MCP (April 2026):** ITER Organization releases an MCP server providing LLM tool-calling access to IMAS data. First LLM-native interface for the fusion simulation ecosystem.[^57]

***
## 1.8 Cross-Domain Intersectional Signals
**1. Gyrokinetic Turbulence as a 5D Stochastic PDE (connects to Zer0pa's computational physics + information theory):**

The gyrokinetic Vlasov equation \[ \frac{\partial f}{\partial t} + \dot{\mathbf{R}} \cdot \nabla f + \dot{v}_\parallel \frac{\partial f}{\partial v_\parallel} = C[f] + S \] is formally a 5-dimensional advection-diffusion equation with a nonlinear collision operator \(C[f]\) and source term. The mathematical methods developed for turbulence modelling in fluid dynamics — spectral decomposition, Fourier-space energy cascades, Kolmogorov scaling — map directly onto gyrokinetic turbulence, just in the 5D phase space rather than 3D physical space. The GyroSwin approach (5D Swin Transformer) is precisely applying the spatial-hierarchical vision transformer architecture — developed for 2D image turbulence in fluid dynamics — to 5D phase-space turbulence. The Zer0pa signal: gyrokinetic turbulence is an information flow problem in 5D phase space. The Liouville operator governing the distribution function evolution is a continuous-time information processing system; the entropy production rate under the collision operator is the formal information decay rate. The mutual information between phase-space regions (the correlation structure of the distribution function) determines the anomalous transport coefficients. Shannon information theory provides the natural language for characterising gyrokinetic transport efficiency.

**2. Grad-Shafranov Equilibrium as an Inverse Problem (connects to computational physics + imaging):**

The Grad-Shafranov equation \[ \Delta^* \psi = -\mu_0 R J_\phi = -\mu_0 R \left( p'(\psi) R + \frac{F F'(\psi)}{\mu_0 R} \right) \] is an elliptic PDE for the poloidal flux function \(\psi\). Plasma equilibrium reconstruction from magnetic diagnostics is formally a constrained inverse problem: given a set of magnetic flux loop and Rogowski coil measurements, infer the current density distribution that satisfies the Grad-Shafranov equation and is consistent with the measurements. This is mathematically equivalent to compressed sensing MRI reconstruction (given sparse \(k\)-space measurements, reconstruct the full image under smoothness constraints). Methods from medical imaging — iterative Tikhonov regularisation, TV-norm minimisation, Bayesian posterior sampling — are directly applicable. PiMiX (2024) applies neural network methods to this inverse problem; the CRATOS-GS code (2025) introduces AMR to the forward solver. Zer0pa's computational physics background provides the mathematical fluency for the inverse problem formulation.[^67][^56]

**3. Plasma Disruption as Topological Tipping Point (connects to cellular automata + complex systems):**

A tokamak disruption is a bifurcation in a high-dimensional dynamical system — the plasma configuration crosses a stability boundary and transitions irreversibly to a different state (the current quench/thermal quench sequence). This is formally a fold bifurcation or saddle-node bifurcation in the space of MHD equilibria. Early warning signals of disruption — slowing down of fluctuation decay rates near the bifurcation point (critical slowing down), growing variance in magnetic fluctuation signals — are the same topological signatures of tipping points studied in complex systems science, climate science, and ecology. Persistent homology (topological data analysis) of the magnetic fluctuation time series before a disruption should reveal growing topological features as the plasma approaches the stability boundary. No published application of TDA to disruption prediction was found as of April 2026 — this is an open research gap where Zer0pa's intersectional competency would be novel.

**4. Nuclear Cross-Section Uncertainty as Bayesian Channel Capacity:**

Nuclear cross-section covariance matrices (ENDF/B Bayesian evaluation, JEFF covariances) encode the uncertainty in measured reaction cross-sections as correlations between energy groups. The propagation of this uncertainty through reactor simulation (OpenMC with covariance sampling) is equivalent to a Bayesian inference problem: given a noisy measurement channel (the cross-section measurement apparatus), what is the posterior distribution over transport-relevant quantities (keff, neutron flux, activation inventory)? The Fisher information metric of the cross-section parameter space determines the efficiency of this propagation — highly relevant to FECSG-ML surrogate approaches. Information theory provides the bound: the channel capacity of the nuclear measurement apparatus (in bits per measurement) sets the minimum achievable uncertainty in reactor predictions. Zer0pa's information theory background maps directly onto nuclear data uncertainty quantification.[^13]

***
## 1.9 Commercial Value Map
| Market Segment | Capital Deployed | Key Buyers | Open-Source Gap | Zer0pa Entry Point |
|---------------|-----------------|------------|-----------------|---------------------|
| Private tokamak design | >$5B VC invested (40+ companies)[^65] | CFS, Helion, TAE, Zap, Renaissance, Proxima | Integrated workflow orchestration (OMFIT equivalent but cloud-native) | IMAS-MCP + OMFIT Python orchestration as managed service |
| ITER/EUROfusion | Multi-billion government | National labs, ITER IO | IMAS now open-sourced — need deployment and integration tooling | IMAS-Python + GyroSwin + JOREK ML pipeline as a managed compute service |
| Disruption mitigation | N/A (existential safety) | All tokamak operators | Cross-machine open data standard just proposed[^42] | Build the disruption data platform + transfer learning service |
| Neutronics/blanket design | $500M+ engineering | CFS (SPARC blanket), STEP (UKAEA), General Fusion | OpenMC + DAGMC is open; no managed cloud service exists | OpenMC-as-a-service with DAGMC geometry integration |
| ML surrogate training data | N/A | Entire field | GyroSwin open; no training data curation service | DIII-D/JET data + GACODE runner + GyroSwin fine-tuning service |

**Key insight:** The December 2025 IMAS open-source release is the enabler. Before December 2025, IMAS was restricted to ITER Member institutions, making it impossible for a South African startup to legally deploy IMAS-based workflows commercially. After December 2025, the entire ITER modelling infrastructure is accessible under LGPL licence. This is the market timing event that makes the Zer0pa fusion vertical viable.

***
## 1.10 Pipeline Assembly Recommendation
**Minimum viable fusion pipeline (all Class A or B):**

```
L1: OpenMC v0.15.2 (MIT) + ENDF/B-VIII.0 (public domain)
    ↓
L2: GACODE/CGYRO (Apache 2.0) + GyroSwin surrogate (MIT) for fast transport
    ↓  
L3: JOREK (LGPL) for disruption + FreeGS4E (LGPL) for equilibrium
    ↓
L4: OMFIT (MIT) + IMAS-Python v2.0 (LGPL) + OMAS (MIT)
    ↓
L5: OpenMC + DAGMC (MIT) + Paramak (MIT) for blanket geometry
    ↓
L6: OMFIT modules + IMAS-MCP (MIT) for LLM tool-calling + duqtools (MIT) for UQ
```

**Best-of-breed addition:** Replace CGYRO direct runs with GyroSwin for scenario exploration; fall back to CGYRO for final validation. This 1,000x speedup in L2 is the compute efficiency argument for the Zer0pa managed service.

**Open questions:**
1. The `imas_core` Access Layer is not yet publicly released — some IDS functionality is disabled. Monitor `github.com/iterorganization` for the full release. Until then, use the netCDF interface in IMAS-Python.
2. GENE (Class C) remains the highest-accuracy gyrokinetic code for some plasma regimes. For commercial deployments, either use GACODE/CGYRO (Apache 2.0) or negotiate an MPG licence.
3. No open database of ITER-geometry gyrokinetic simulation data exists for training GyroSwin on reactor-class scenarios — this is the primary data bottleneck for L2 ML surrogate quality.

***
# Part 2: South Africa and Emerging Market Energy Context
## 2.1 PGM-Green Hydrogen Strategic Landscape
South Africa controls approximately 80–87% of global platinum reserves and a substantial share of global iridium reserves — both critical for PEM electrolysis OER and HER catalysts. This is not a peripheral fact; it is the strategic anchor of the entire South African hydrogen economy.[^68][^69]

**Government strategy:** The South African Hydrogen Society Roadmap (HSRM, 2021, DSTI/DMRE) targets 500,000 tonnes per annum of green hydrogen production by 2030. The DMRE green hydrogen framework document ("Roadmap towards cleaner fossil fuels") is the operational policy instrument. A March 2025 EU announcement committed €4.7 billion under the Global Gateway Investment Package specifically for South Africa's green hydrogen and PGM value chain. The target production cost is $1.60/kg of green hydrogen by 2030 — among the lowest projected globally due to SA's renewable resources.[^70][^69]

**Private sector engagement:**
- **Anglo American Platinum (Amplats):** Actively backing the global green hydrogen advance, with investments through AP Ventures in LOHC technology and green hydrogen infrastructure. Has signed a commercial agreement with BMW South Africa and Sasol for hydrogen fuel cell vehicles. The South African Green Hydrogen Summit (SAGHS) is Anglo American Platinum's signature industry convening event. Amplats is the largest platinum producer globally and has a stated commercial interest in expanding PEM electrolyser demand to consume more platinum.[^71][^72]
- **Sibanye-Stillwater:** As of April 2026, actively collaborating on new applications for platinum and palladium beyond automotive. Sibanye operates in both SA and US (Montana) and has explicit PGM catalyst technology partnerships.[^73][^74]
- **Implats:** PGM mining focus; no specific in silico catalyst R&D programs found in public sources.

**Critical buyer question:** Both Amplats and Sibanye-Stillwater have stated commercial interests in accelerating PEM electrolyser adoption (which increases platinum demand). An in silico PEM catalyst screening service that identifies platinum-reduced or platinum-enhanced OER catalysts is directly aligned with their commercial interests. Amplats' AP Ventures fund invests in early-stage green hydrogen technology — a potential investor/buyer dual relationship for Zer0pa.

***
## 2.2 South Africa Solar + Storage Market
South Africa experienced the fastest growth rate of rooftop solar PV globally during 2022–2024, driven by Stage 6 loadshedding (up to 12 hours/day outages). The South Africa solar energy market is forecast to grow at 38% CAGR (2024–2029), adding USD 5.46 billion in market size. Installed rooftop PV capacity reached 8.75 GW by 2025.[^75][^76][^77]

The rooftop solar market is paired with battery storage — predominantly Li-ion, with Tesla Powerwall, Sungrow, and NEC as leading suppliers. The GreenCape 2025 Energy Services report confirms the embedded generation (EG) segment is dominated by rooftop PV with Li-ion battery pairing. Eskom's load reduction has eased since 2024 but structural grid unreliability sustains demand.[^78][^77]

**SA energy company investment in simulation/digital twins:** No public evidence found of Rubicon, SolarAfrica, Starsight, or Hohm Energy deploying computational simulation or digital twin capabilities for battery system design. The market is primarily installation/integration-focused, not R&D-focused. The simulation demand in this sub-sector is more likely to originate from battery manufacturers and system integrators than from SA energy services companies.

**UCT and CSIR roles in energy modelling:**
- **UCT Energy Systems Research Group (ESRG):** Active in net-zero pathway modelling for South Africa, with demand scenarios used in wind/solar benchmark assessments. Uses PyPSA-based sector-coupled modelling.[^79]
- **CSIR Energy Centre:** Conducts national energy system modelling, supports municipalities with science-based energy planning. Python-based energy modelling stack.[^80]
- **PyPSA-RSA:** Meridian Economics developed a PyPSA-RSA model (2024) as a South Africa-specific energy planning tool. Available for national scenario analysis.[^81]

**BRICS context:** South Africa's BRICS membership has not produced specific computational materials science or energy simulation technology cooperation frameworks with accessible funding for Zer0pa. The EU Global Gateway (€4.7bn, March 2025) is the more tangible funding mechanism — South African entities can access EU grant co-funding for green hydrogen projects that have EU export components.[^69]

**Zer0pa entry points in the South African market:**
1. **Amplats/Sibanye catalyst screening service:** In silico PEM OER/HER catalyst screening to identify platinum-optimised or platinum-alloyed catalyst compositions. Clear value alignment — accelerates PEM demand.
2. **Battery storage system simulation for C&I/residential:** Providing degradation modelling and optimisation for South African solar+storage deployments. Technical opportunity but market may not yet be price-sensitive to simulation-driven optimisation vs. off-the-shelf sizing.
3. **National energy planning:** Supporting CSIR/UCT ESRG PyPSA-Earth South Africa scenarios with materials discovery pipeline outputs (e.g., lower-cost storage materials that change LCOE assumptions).

***
# Part 3: Electrochemistry Reasoning LLM — Gap and Opportunity
## 3.1 Current State of Domain-Specific Battery/Electrochemistry LLMs
**BatteryBERT** (Apache 2.0, `ShuHuang/batterybert`, 2022, ACS JCIM): Six BERT variants (BatteryBERT, BatteryOnlyBERT, BatterySciBERT — cased and uncased) pre-trained on battery research paper corpus. Fine-tuned on battery paper classification and extractive QA for component identification (anode, cathode, electrolyte). Outperforms standard BERT on battery-specific NLP tasks. Available on HuggingFace. **This is an encoder-only model — it does not reason; it classifies and extracts.** It is the correct tool for Named Entity Recognition in battery text pipelines, not for scientific reasoning.[^82][^83]

**BatteryDataExtractor** (MIT, `CambridgeMolecularEngineering/BatteryDataExtractor`): Python toolkit embedding BatteryBERT for automated extraction of battery material properties from literature. Suitable for Phase 0 literature mining in the energy pipeline.[^84]

**OmniScience** (SES AI, March 2025, arXiv 2503.17604): A domain-specialised large **reasoning** model for science — not just battery BERT-class extraction. Built through three-stage training: (1) domain adaptive pretraining on scientific literature; (2) instruction tuning; (3) reasoning-based knowledge distillation. The battery agent component ranks electrolyte solvents/additives for electrolyte design. Benchmark performance: "competitive with state-of-the-art large reasoning models on the GPQA Diamond and domain-specific battery benchmarks." License status: unclear — SES AI is a commercial entity; the model may not be fully open-weight. **Class E until license is confirmed.**[^85][^86][^87]

**Frontier models on battery/electrochemistry benchmarks:** The February 2026 review "Advancing battery research through large language models" documents wide adoption of GPT-4-class models for battery applications. GPT-4.1 achieves F1 ≈ 0.91 for thermoelectric property extraction[^1420]; analogous performance is expected for battery properties. The GPQA Diamond benchmark includes chemistry questions; current rankings show frontier models achieving 60–80% on chemistry GPQA. No electrochemistry-specific benchmark equivalent to MatSciBench exists as of April 2026 — this is an open gap that Zer0pa could fill with a curated evaluation set.[^88][^89][^90]
## 3.2 Base Models for Scientific Reasoning Fine-Tuning
| Model | License | MATH-500 | GPQA-D | Scientific Reasoning | Notes |
|-------|---------|----------|--------|---------------------|-------|
| DeepSeek-R1-Distill-Llama-70B | A (MIT) | 94.5 | ~65% | Excellent | Best open-weight reasoning; based on Llama-3.3-70B[^91] |
| Qwen2.5-72B | A (Apache 2.0) | ~90% | ~60% | Very strong | Strong STEM base; Apache 2.0 |
| Llama-3.3-70B | Meta Llama Community License | ~88% | ~55% | Strong | Not fully open; community license has restrictions[^92] |
| DeepSeek-R1 (full) | A (MIT) | 97.3 | ~71% | Best available | 671B MoE; too large for single-node inference |
| Mistral-7B | A (Apache 2.0) | ~65% | ~40% | Moderate | Small size limits science reasoning; not recommended for 70B task |

**Recommendation for electrochemistry fine-tuning base:** DeepSeek-R1-Distill-Llama-70B (MIT) is the strongest open-weight reasoning model for a scientific domain fine-tuning project. Its MIT licence makes it fully commercialisable — critical for Zer0pa. Qwen2.5-72B (Apache 2.0) is the alternative with comparable performance and a more permissive licence from a legal simplicity perspective.
## 3.3 Fine-Tuning Infrastructure
| Framework | License | GPU Requirement | 70B LoRA Time | Key Feature |
|-----------|---------|-----------------|----------------|-------------|
| Unsloth | Apache 2.0 | Single A100 80GB (QLoRA) | ~4.2 hours[^93] | Fastest; memory-optimised |
| LLaMA-Factory | Apache 2.0 | Multi-GPU supported | ~6–8 hours A100 | Most flexible; many formats |
| Axolotl | Apache 2.0 | Single A100 80GB | ~4.2 hours[^93] | Well-documented; community |

For a 70GB domain corpus (PyBaMM docs, NREL reports, OC25 narratives, battery literature), LoRA fine-tuning of a 70B model requires approximately one A100 80GB node for 4–8 hours per fine-tuning run. QLoRA reduces memory to ~35GB allowing single-48GB GPU deployment. Total training cost estimate: $50–$200 per fine-tuning run on cloud A100 (~$2–4/hr).[^93][^94]

**Fine-tuning corpus availability:**
- PyBaMM documentation: open (BSD); suitable for physics-informed QA
- NREL battery reports: public domain US government; importable
- OC25 data narratives: currently not in instruction-following format — a 1–2 week engineering task
- RSC electrochemistry literature: proprietary; cannot be included without licence; use PubChem, ChEMBL, and preprint servers instead
- BatteryBERT training corpus (battery papers abstracts): available on HuggingFace

**Verdict:** Building a fine-tuned electrochemistry reasoning model is a genuine gap. OmniScience is the closest existing model but has unclear licensing. A Zer0pa ElectroChem-R1 (DeepSeek-R1-Distill-Llama-70B + LoRA fine-tuning on open battery science corpus) is achievable in 4–8 weeks of engineering effort at minimal compute cost (~$500 total GPU cost for initial training). The gap is the curated instruction-following dataset; this is the actual engineering challenge.

***
# Part 4: Electrochemical Device Data Standard
## 4.1 Battery Data Format (BDF) — The New Standard
**Battery Data Format (BDF)**, released December 22, 2025, LF Energy Battery Data Alliance:[^95][^96][^97]
- Open, community-driven standard (Linux Foundation Energy, similar to MIT in practice)
- Provides a unified, machine-readable HDF5-based schema with metadata aligned to the **BattINFO ontology**
- Enables datasets from experiments, simulations, and industrial projects to be shared across the battery ecosystem
- Released at `battery-data-alliance/battery-data-format` (GitHub)
- BattINFO alignment means it is FAIR-data compliant and semantic-web interoperable[^98]

This is the closest existing equivalent to OPTIMADE for battery cycling data. It is new (December 2025) and adoption is early, but it has Linux Foundation backing — the same governance model that produced LFDEM, OpenFOAM, and other durable open standards. **BDF is the data format to target for Zer0pa's device-layer data ingestion.**
## 4.2 Python Battery Data Libraries
| Library | License | Formats Supported | Python API | Key Feature |
|---------|---------|-------------------|------------|-------------|
| battdat (NREL, battery-data-toolkit) | A (BSD/MIT) | HDF5, Parquet + metadata | Yes (`pip install battery-data-toolkit`)[^99] | BattINFO-aligned; PyData ecosystem integration |
| BEEP (NREL) | CC-BY (code and data) | JSON, HDF5, Arbin | Yes (`pip install beep`)[^100][^101] | Early cycle life prediction; training data generation |
| navani | Open (MIT-adjacent) | BioLogic MPR, Arbin, Ivium, Lanhe, txt/xls[^102] | Yes (`pip install navani`) | Best multi-cycler parser; pandas output |
| galvani | B (GPL v3+) | BioLogic MPR, VMP3[^103] | Yes (`pip install galvani`)[^104] | Legacy BioLogic format specialist; GPL limits redistribution |

**Licensing note on galvani:** GPL v3+ means the galvani library cannot be embedded in a closed-source commercial product without open-sourcing the enclosing code. Use navani (MIT-adjacent) or battdat as the preferred ingestion layer in a commercial pipeline.
## 4.3 EIS Data Standards
Electrochemical Impedance Spectroscopy (EIS) data — complex impedance Z' and Z'' as a function of frequency — has no formal universal standard as of April 2026. The Zenodo 2025 EIS dataset (NMC811 21700 cells) demonstrates the emerging practice: CSV files per cell with JSON-LD metadata using CSVW, DCAT, and BattINFO terms. The metadata standard uses `metadata.jsonld` for semantic description of the impedance spectra, with BattINFO ontology terms for cell type, SoC, and measurement conditions. This JSON-LD approach is the current de facto best practice for EIS FAIR data — not a formal standard but the direction the community is moving.[^105]

**EIS ingestion in a pipeline:** Raw EIS data (Z', Z'', frequency) is typically stored as CSV or proprietary formats (Gamry DTA, BioLogic MPR). navani can parse BioLogic MPR files containing EIS data. battdat accepts EIS data via its `CycleSummary` data model. No dedicated open-source EIS equivalent impedance model library (Equivalent Circuit Model fitting) is available under Class A licence — impedance.py (`pip install impedance`, MIT) is the closest: a Python library for EIS impedance model fitting with equivalent circuit specification. Class A.[^106]
## 4.4 Battery Dataset Catalogue
| Dataset | License | Format | Size | Access | ML-Ready |
|---------|---------|--------|------|--------|----------|
| BDF (LF Energy) | Open (LFE) | HDF5 + BattINFO JSON-LD | Spec only (December 2025) | GitHub | N/A (schema) |
| CALCE (UMD) | Academic research | Arbin/custom CSV | ~1,000 cells | Direct download | Requires navani/battdat preprocessing |
| Oxford Battery Degradation | CC-BY-4.0 | MATLAB/CSV | 8 cells (high quality) | Zenodo | Partial |
| NASA Battery Dataset | Public domain | MATLAB | ~70 cells | NASA Technical Reports | Partial |
| Severson 2019 (Nature Energy) | Open (CC-BY) | CSV | 124 LFP cells | GitHub | Yes (canonical early prediction dataset) |
| EIS Dataset (Zenodo 2025) | CC-BY | CSV + JSON-LD (BattINFO) | 54 NMC811 cells[^105] | Zenodo | Yes (FAIR) |
| BEEP d3batt | CC-BY | JSON, HDF5 | ~185 cells | AWS S3 open | Yes (BEEP pipeline) |

---

## References

1. [[PDF] ITER Integrated Modelling Programme](https://www.iter.org/sites/default/files/media/2025-07/i-2_pinches.pdf) - Establishment of a programme on integrated modelling and control of fusion plasmas, including benchm...

2. [[PDF] SURROGATE MODEL FOR TURBULENT TRANSPORT USING ...](https://conferences.iaea.org/event/392/contributions/36356/attachments/20329/34386/Synopses_yongxiao_2025_final.pdf) - In this work, we develop a deep learning-based AI surrogate model to predict turbulent transport and...

3. [5D Surrogates for Gyrokinetic Plasma Turbulence Simulations - arXiv](https://arxiv.org/html/2510.07314v1) - Few works have attempted to train machine learning surrogates for nonlinear gyrokinetics. Narita et ...

4. [Milestone in predicting core plasma turbulence - PMC - NIH](https://pmc.ncbi.nlm.nih.gov/articles/PMC11910665/) - This work presents an unprecedented comparison of plasma turbulence between experiment and simulatio...

5. [A Data integration tool for the integrated modeling and analysis for ...](https://www.sciencedirect.com/science/article/abs/pii/S092037962300515X) - OMAS, a library designed to simplify the interface of Python codes with IMAS. ... ITER Integrated Mo...

6. [Release of IMAS infrastructure and physics models as open source](https://www.iter.org/node/20687/release-imas-infrastructure-and-physics-models-open-source) - The Integrated Modelling and Analysis Suite (IMAS) provides standard tools and applications to suppo...

7. [IMAS-Python 2.0.0 released - Ignition Computing](https://ignitioncomputing.com/news/2025/03/20/ITER-IMAS-Python-2.0-released) - IMAS-Python is a pure Python library for working with IDS data structures from the IMAS Data Diction...

8. [Demonstration of OpenMC as a framework for atomic transport and plasma
  interaction](http://arxiv.org/pdf/2411.12937.pdf) - Modern tooling is demanded for predicting the transport and reaction
characteristics of atoms and mo...

9. [Performance Portable Monte Carlo Particle Transport on Intel, NVIDIA,
  and AMD GPUs](http://arxiv.org/pdf/2403.12345v1.pdf) - ...of OpenMC at scale on the Frontier, Polaris, and
Aurora supercomputers, demonstrating that perfor...

10. [Validation of the OpenMC Code for Fusion Applications: The FNG-Streaming Benchmark Case](https://www.tandfonline.com/doi/full/10.1080/15361055.2024.2400762)

11. [Multigroup Cross Section Generation Part III: Libraries](https://docs.openmc.org/en/v0.12.2/examples/mgxs-part-iii.html) - The Library class is designed to automate the calculation of multi-group cross sections for use case...

12. [Evaluating machine learned nuclear data precision in full core ...](https://www.nature.com/articles/s41598-026-35227-9) - All calculations use the official OpenMC version 0.15.2 with ENDF/B-VII.1 incident-neutron HDF5 libr...

13. [FECSG-ML: Feature Engineering for Nuclear Reaction Cross ...](https://www.sciencedirect.com/science/article/abs/pii/S0969804324003737) - Neutron-induced nuclear reactions, particularly nuclear cross sections data, are essential for vario...

14. [[2502.07469] 5D Neural Surrogates for Nonlinear Gyrokinetic ... - arXiv](https://arxiv.org/abs/2502.07469) - We propose a method for training neural surrogates for 5D gyrokinetic simulations. Our method extend...

15. [CGYRO — GACODE 1.0 documentation](https://gafusion.github.io/doc/cgyro.html) - CGYRO is a global-spectral gyrokinetic code. Core developers Notable publications Table 3 List of CG...

16. [gafusion/gacode: GA Turbulence and Transport Codes - GitHub](https://github.com/gafusion/gacode/) - GACODE is free software released under the Apache 2.0 license. The developers of GACODE recommend th...

17. [GENE - Plasma-PEPSC](https://plasma-pepsc.eu/gene/) - GENE (Gyrokinetic Electromagnetic Numerical Experiment) is an open source plasma microturbulence cod...

18. [GENE | High-Performance Computing in Europe](https://hpc-portal.eu/codes-and-competences/codes/gene) - Licensing Info. Free Customised licence (request to MPG). 13/04/2025. Code. Code Category. Plasma ph...

19. [Pyrokinetics - A Python library to standardise gyrokinetic analysis](https://joss.theoj.org/papers/10.21105/joss.05866.pdf) - ...near limitless source of low-carbon energy and is often regarded as a solution for the world’s lo...

20. [GitHub - pyro-kinetics/pyrokinetics: Python library to run and analyse ...](https://github.com/pyro-kinetics/pyrokinetics) - This project aims to standardise gyrokinetic analysis. A general pyro object can be loaded either fr...

21. [5D Surrogates for Gyrokinetic Plasma Turbulence Simulations - arXiv](https://arxiv.org/abs/2510.07314) - We demonstrate that GyroSwin outperforms widely used reduced numerics on heat flux prediction, captu...

22. [5D Surrogates for Gyrokinetic Plasma Turbulence Simulations](https://openreview.net/forum?id=SkAY3KHKn2) - This paper presents GyroSwin, a deep learning surrogate model for 5D gyrokinetic plasma turbulence s...

23. [NeurIPS Poster GyroSwin: 5D Surrogates for Gyrokinetic Plasma ...](https://neurips.cc/virtual/2025/poster/117909) - We demonstrate that GyroSwin outperforms widely used reduced numerics on heat flux prediction, captu...

24. [[PDF] Neural Network and Decision Tree Surrogate Models for Turbulent ...](https://indico.global/event/13788/contributions/131718/attachments/62985/121550/Lanzarone_EFTC%202025.pdf) - Surrogate Models for Turbulent Transport in Tokamak Plasmas. M ... • Compare two ML algorithms: • Ne...

25. [Comparison of Neural Network and Gradient-Boosted Decision Tree ...](https://hal.science/hal-05280765v1) - Comparison of Neural Network and Gradient-Boosted Decision Tree Surrogates of Linear Gyrokinetic Sim...

26. [Transport model surrogates using stochastic variational Gaussian ...](https://pubs.aip.org/aip/pop/article/32/10/103906/3369192/Transport-model-surrogates-using-stochastic) - A surrogate model for turbulent transport models is proposed based on Gaussian process (GP) regressi...

27. [FREE-BOUNDARY SIMULATIONS OF MHD PLASMA ... - HAL](https://hal.science/tel-02012234/) - The numerical code JOREK-STARWALL is adapted and applied to the simulation of the so-called free-bou...

28. [JOREK non-linear MHD Code](https://www.jorek.eu) - Self-consistent full MHD coupling of JOREK and STARWALL for advanced plasma free boundary simulation...

29. [[PDF] The JOREK non-linear extended MHD code and applications to ...](https://mediatum.ub.tum.de/doc/1653698/document.pdf) - Comparisons have been made between JOREK and BOUT++ with the aim to validate the nonlinear MHD codes...

30. [freegs4e · PyPI](https://pypi.org/project/freegs4e/) - FreeGS4E is a package forked from FreeGS (v0.6.1), which has the capability to solve the static inve...

31. [freegs4e · PyPI](https://pypi.org/project/freegs4e/0.1.2/) - FreeGS4E: Free boundary Grad-Shafranov solver for time evolution ... FreeGS4E is licensed under the ...

32. [FGE: A Fast Free-Boundary Grad-Shafranov Evolutive Solver - arXiv](https://arxiv.org/abs/2512.06847) - It self-consistently solves the free-boundary Grad-Shafranov equation coupled with circuit equations...

33. [freegs-plasma/freegs: Free boundary Grad-Shafranov solver - GitHub](https://github.com/freegs-plasma/freegs) - This Python module calculates plasma equilibria for tokamak fusion experiments, by solving the Grad-...

34. [freegs.gradshafranov — FreeGS 0.1.dev1+g9fbec2056 documentation](https://freegs.readthedocs.io/en/latest/generated/freegs.gradshafranov.html) - FreeGS is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser ...

35. [README.md - boutproject/BOUT-dev - GitHub](https://github.com/boutproject/BOUT-dev/blob/next/README.md) - BOUT++ is a framework for writing fluid and plasma simulations in curvilinear geometry. It is intend...

36. [boutproject - GitHub](https://github.com/boutproject) - BOUT++: Plasma fluid finite-difference simulation code in curvilinear coordinate systems. C++ 229 10...

37. [[PDF] GVEC: A flexible 3D MHD equilibrium solver](https://joss.theoj.org/papers/10.21105/joss.09670.pdf) - The Galerkin Variational Equilibrium Code (GVEC) is a new code for finding 3D MHD equilibrium soluti...

38. [(PDF) Disruption prediction with artificial intelligence techniques in ...](https://www.academia.edu/123651376/Disruption_prediction_with_artificial_intelligence_techniques_in_tokamak_plasmas) - Accurate disruption prediction is critical for next-generation tokamaks like ITER, which targets les...

39. [Disruption prediction for future tokamaks using parameter-based ...](https://www.nature.com/articles/s42005-023-01296-9) - An adaptive disruption predictor was built based on the analysis of quite large databases of AUG and...

40. [[PDF] Disruption prediction at JET through deep convolutional neural ...](https://iris.unica.it/retrieve/58b34fef-7ff1-48aa-b413-bb89bfaac588/Aymerich_2022_Nucl._Fusion_62_066005.pdf) - The proposed algorithm has been assessed using data from DIII-D and JET showing promising cross-.

41. [[PDF] disruption prediction for future tokamak reactors from different ...](https://conferences.iaea.org/event/392/papers/36206/files/13939-FEC2025_proceeding_WeiZehng2.pdf) - The results demonstrate that the E-CAAD model trained on the existing machine can effectively distin...

42. [An open source fusion machine agnostic standard for the exchange ...](https://www.sciencedirect.com/science/article/pii/S0920379625001358) - We propose two open-source standards accessible on GitHub. These standards aim to facilitate the sha...

43. [ITER Organization - GitHub](https://github.com/iterorganization) - ITER is an international nuclear fusion research and engineering megaproject aimed at creating energ...

44. [ITER Organization on Instagram](https://www.instagram.com/reel/DSEuJ0xD9uR/) - ... likes, 11 comments - iter_organization on December 9, 2025: "The ... Analysis Suite (IMAS) under...

45. [What is OMFIT and how does it work](https://omfit.io/publications.html) - OMFIT interfaces with the ITER IMAS data infrastructure via the OMAS Python library. In OMFIT, model...

46. [OMFIT: A Community and Framework for Integrated Modeling and ...](https://ui.adsabs.harvard.edu/abs/2020APS..DPPN10001S/abstract) - OMFIT is a software framework developed for integrated modeling and data analysis, whose main applic...

47. [GYRO_GACODE - OMFIT](https://omfit.io/modules/mod_GYRO_GACODE.html) - GYRO/CGYRO are nonlinear tokamak microturbulence package designed to run on nearly all modern comput...

48. [gafusion/omas: Ordered Multidimensional Array Structure - GitHub](https://github.com/gafusion/omas) - OMAS is a Python library designed to simplify the interface of third-party codes with the ITER Integ...

49. [Duqtools: Dynamic uncertainty quantification for Tokamak reactor
  simulations modelling](https://arxiv.org/html/2409.13529v1) - ...operations of fusion reactors. Reduced models
and increasing computational power means that it is...

50. [SPARC: Proving commercial fusion energy is possible](https://cfs.energy/technology/sparc/) - SPARC's design combines decades of knowledge of plasma physics from dozens of tokamaks around the wo...

51. [MITIM (MIT Integrated Modeling) Suite for Fusion Applications · GitHub](https://github.com/pabloprf/MITIM-fusion) - The MITIM (MIT Integrated Modeling) is a versatile and user-friendly Python library designed for pla...

52. [The Paramak: automated parametric geometry construction for fusion reactor designs.](https://f1000research.com/articles/10-27/v1/pdf) - ...enables better decisions to be made during concept selection and the detailed design phase. The P...

53. [High-fidelity data-driven dynamics model for reinforcement learning ...](https://www.nature.com/articles/s42005-025-02302-y) - Reinforcement learning (RL)-based control in tokamaks offers improved flexibility for nuclear fusion...

54. [[PDF] Fusion Science & Technology Roadmap - Department of Energy](https://www.energy.gov/sites/default/files/2025-10/fusion-s&t-roadmap-101625.pdf) - led by General Atomics has developed an Open. Access Fusion Data Platform that hosts both DIII-D and...

55. [Decades of coding experience are powering the next era of fusion ...](https://www.pppl.gov/news/2026/decades-coding-experience-are-powering-next-era-fusion-energy) - Decades of coding experience are powering the next era of fusion energy · Challenge 1: Improving fus...

56. [Physics-informed Meta-instrument for eXperiments (PiMiX) with
  applications to fusion energy](https://arxiv.org/pdf/2401.08390.pdf) - ...-driven methods (DDMs), such as deep neural networks, offer a generic
approach to integrated data...

57. [iterorganization/imas-codex - GitHub](https://github.com/iterorganization/imas-mcp) - The IMAS Codex server provides 8 specialized tools for different types of queries: Search: Natural l...

58. [Impact of years of fusion experiments revealed by JET](https://www.ukaea.org/news/impact-of-years-of-fusion-experiments-revealed-by-jet/) - Our publications and access to our public data. Visit UKAEA. Learn about open events and educational...

59. [[PDF] Insights of the JET high fusion power scenario in the final DT ...](https://scientific-publications.ukaea.uk/wp-content/uploads/UKAEA-CCFE-PR25403.PDF) - The final D-T campaign at JET (DTE3) took place in 2023. Even though demonstration of high fusion po...

60. [Contribution List · Indico for IAEA Conferences](https://conferences.iaea.org/event/393/contributions/) - To address this need, we introduce JDDB (J-TEXT Disruption Database), a flexible and extensible most...

61. [JET Decommissioning and Repurposing | UKAEA Fusion Energy](https://www.ukaea.org/work/jet-decommissioning-and-repurposing/) - Our publications and access to our public data. Visit UKAEA. Learn about open events and educational...

62. [A physics-constrained deep learning surrogate model of the ...](https://www.cambridge.org/core/journals/journal-of-plasma-physics/article/physicsconstrained-deep-learning-surrogate-model-of-the-runaway-electron-avalanche-growth-rate/793C841942EE585A18893B7A6F4F2F20) - A surrogate model of the runaway electron avalanche growth rate in a magnetic fusion plasma is devel...

63. [Digital: accelerating the pathway](https://royalsocietypublishing.org/doi/10.1098/rsta.2023.0411) - The Spherical Tokamak for Energy Production (STEP) programme is an ambitious but challenging endeavo...

64. [Digital: accelerating the pathway](https://pmc.ncbi.nlm.nih.gov/articles/PMC11423680/) - ...definition. The digital strategy for STEP is built around a vision of a digital twin of the whole...

65. [Every fusion startup that has raised over $100M - TechCrunch](https://techcrunch.com/2026/04/10/every-fusion-startup-that-has-raised-over-100m/) - Like Helion, Zap Energy is based in Everett, Washington, and the company has raised $327 million, ac...

66. [[PDF] IAEA World Fusion Outlook 2025](https://www-pub.iaea.org/MTCD/publications/PDF/p15935-25-02871E_WFO25_web.pdf) - The fusion energy landscape continues to develop at an extraordinary pace. What was once confined to...

67. [CRATOS-GS: A free-boundary, hierarchical adaptive mesh ...](https://pubs.aip.org/aip/adv/article/15/9/095128/3364418/CRATOS-GS-A-free-boundary-hierarchical-adaptive) - We present CRATOS-GS, a free-boundary hierarchical adaptive mesh refinement (AMR) Grad–Shafranov sol...

68. [Platinum group metals, green hydrogen production and economic ...](https://afripoli.org/platinum-group-metals-green-hydrogen-production-and-economic-development-in-south-africa) - South Africa will reportedly need to spend more than US$ 250 billion over the next 30 years to “fund...

69. [South Africa | Green Hydrogen Organisation](http://gh2.org/countries/south-africa) - The South African government aims to deploy 10 GW of electrolysis capacity in the Northern Cape regi...

70. [[PDF] Emerging themes and priorities of green hydrogen research to ...](https://greenhydrogensummit.org.za/wp-content/uploads/2024/04/GIZ_Sanedi_H2-report.pdf) - Together with SANEDI, the DMRE has recently published the DMRE green hydrogen framework document tit...

71. [Anglo American Platinum providing further backing for green ...](https://www.miningweekly.com/article/anglo-american-platinum-providing-further-backing-for-green-hydrogens-global-advance-2025-02-25) - JSE-listed Anglo American Platinum and South Africa-linked AP Ventures are supporting the next vital...

72. [South African Green Hydrogen Summit (SAGHS)](https://southafrica.angloamerican.com/our-impact/events/saghs) - Anglo American Platinum has signed a ground-breaking agreement with BMW South Africa and Sasol to in...

73. [[PDF] Sibanye Stillwater Limited](https://reports.sibanyestillwater.com/2025/download/SSW-FORM20F25.pdf) - Securities registered or to be registered pursuant to Section 12(b) of the Act. Title of Each Class....

74. [Sibanye-Stillwater collaborates further to find new applications for ...](https://www.facebook.com/miningweekly/posts/sibanye-stillwater-collaborates-further-to-find-new-applications-for-platinum-me/1445276060951507/) - Plug Power Delivers First Electrolyzer for 100MW Green Hydrogen Project at Galp's Sines Refinery Oct...

75. [South Africa Solar Energy Market Analysis, Size, and Forecast 2025 ...](https://www.technavio.com/report/solar-energy-market-industry-in-south-africa-analysis) - The South Africa solar energy market size is forecast to increase by USD 5.46 billion, at a CAGR of ...

76. [South Africa Solar Energy Market Growth Report 2031](https://www.mordorintelligence.com/industry-reports/south-africa-solar-energy-market) - The South Africa Solar Energy Market size worth 9.76 gigawatt in 2026 is growing at a CAGR of 11.58%...

77. [[PDF] 2025 Energy Services | GreenCape](https://greencape.co.za/wp-content/uploads/2025/04/Energy-Services-2025.pdf) - The EG segment is dominated by the rooftop solar photovoltaic (PV) market, while the energy storage ...

78. [South Africa Energy Storage Market (2025-2031) - 6Wresearch](https://www.6wresearch.com/industry-report/south-africa-energy-storage-market) - The South Africa energy storage market is expected to witness significant growth in the coming years...

79. [[PDF] South Africa - Wind and solar benchmarks for a 1.5°C world](https://newclimate.org/sites/default/files/2024-09/windsolarbenchmarks_southafrica_0.pdf) - In particular, we highlight the results of modelling from the University of Cape Town, exploring net...

80. [Energy systems - CSIR](https://www.csir.co.za/what-we-do/natural-environment/energy/energy-systems) - CSIR researchers are urging other municipalities to adopt science-based energy planning and modellin...

81. [[PDF] PyPSA-RSA model quick start guide - Meridian Economics](https://meridianeconomics.co.za/wp-content/uploads/2024/05/PyPSA-Basics.pdf) - Includes a toolbox of modules for multi-horizon investment planning, unit commitment of conventional...

82. [BatteryBERT: A Pretrained Language Model for Battery Database Enhancement](https://pubs.acs.org/doi/10.1021/acs.jcim.2c00035) - ...The pretrained BatteryBERT models were then fine-tuned on downstream tasks, including battery pap...

83. [BatteryBERT: A Pre-trained Language Model for Battery ... - GitHub](https://github.com/ShuHuang/batterybert) - A pre-trained language model for battery database enhancement. Features: Installation: Run the follo...

84. [BatteryDataExtractor: battery-aware text-mining software embedded with BERT models](https://pubs.rsc.org/en/content/articlepdf/2022/sc/d2sc04322j) - ...therefore likely to improve their text-mining performance. To this end, we release a Python-based...

85. [OmniScience: A Domain-Specialized LLM for Scientific Reasoning and
  Discovery](https://arxiv.org/pdf/2503.17604.pdf) - Large Language Models (LLMs) have demonstrated remarkable potential in
advancing scientific...introd...

86. [A Domain-Specialized LLM for Scientific Reasoning and Discovery](https://arxiv.org/html/2503.17604v2) - In this work, we introduce OmniScience, a specialized large reasoning model for general science, dev...

87. [OmniScience: A Domain-Specialized LLM for Scientific Reasoning ...](https://arxiv.org/html/2503.17604v3) - We demonstrate the versatility of OmniScience by developing a battery agent that efficiently ranks m...

88. [Advancing battery research through large language models: A review](https://pmc.ncbi.nlm.nih.gov/articles/PMC12881755/) - Regarding the first strategy in the model layer, expert LLMs have demonstrated impressive capabiliti...

89. [GPQA Diamond - Epoch AI](https://epoch.ai/benchmarks/gpqa-diamond) - The GPQA (Graduate-Level Google-Proof Q&A) dataset is a collection of challenging multiple-choice qu...

90. [GPQA - Vals AI](https://www.vals.ai/benchmarks/gpqa) - GPQA. Academic. Updated: 4/16/2026. Graduate-level Google-Proof Q&A benchmark evaluating models on q...

91. [The Complete Guide to DeepSeek Models: V3, R1, V4 and Beyond](https://www.bentoml.com/blog/the-complete-guide-to-deepseek-models-from-v3-to-r1-and-beyond) - Understand the differences among DeepSeek-V3, R1, V3.1, V3.2, V4, and distilled models. Learn how to...

92. [deepseek-ai/DeepSeek-R1 - Hugging Face](https://huggingface.co/deepseek-ai/DeepSeek-R1) - DeepSeek-R1 achieves performance comparable to OpenAI-o1 across math, code, and reasoning tasks. To ...

93. [Axolotl vs Unsloth vs TorchTune: Best LLM Fine-Tuning Frameworks ...](https://www.spheron.network/blog/axolotl-vs-unsloth-vs-torchtune/) - A100 80GB VRAM. All frameworks work smoothly. Unsloth gives you 70B model fine-tuning in 4.2 hours w...

94. [Best GPU for Fine-Tuning 70B Models: H100 vs A100...](https://lyceum.technology/magazine/which-gpu-for-fine-tuning-70b-model/) - QLoRA (4-bit) reduces the weight footprint to ~35GB, allowing 70B fine-tuning on a single 80GB GPU o...

95. [A New Open Standard for Battery Data Interoperability - LF Energy](https://lfenergy.org/lf-energy-battery-data-alliance-announces-the-battery-data-format-bdf/) - LF Energy's Battery Data Alliance released the Battery Data Format (BDF), an open, community-driven ...

96. [LF Energy Battery Data Alliance Announces the Battery Data Format ...](https://batterydataalliance.energy/news/bdf-announcement) - BDF provides a unified, machine-readable format to make battery data shareable, reproducible, and mo...

97. [Battery Data Format (.bdf) - GitHub](https://github.com/battery-data-alliance/battery-data-format) - The Battery Data Format (BDF) provides a standard structure for data generated in battery labs, offe...

98. [LF Energy Releases Battery Data Format: An “Open Source ...](https://switchgear-magazine.com/tm-news/products/lf-energy-releases-battery-data-format-an-open-source-standard-for-bess-interoperability/) - The new format provides a unified, machine-readable structure with metadata aligned to the BattINFO ...

99. [battery-data-toolkit - PyPI](https://pypi.org/project/battery-data-toolkit/) - The library has three main purposes: Storing battery data in standardized formats. battdat stores da...

100. [[PDF] BEEP: A Python library for Battery Evaluation and Early Prediction](https://web.mit.edu/braatzgroup/Herring_SoftwareX_2020.pdf) - Published by Elsevier B.V. This is an open access article under the CC BY license ... Data formats a...

101. [ElsevierSoftwareX/SOFTX_2020_49: BEEP: A Python ... - GitHub](https://github.com/ElsevierSoftwareX/SOFTX_2020_49) - Beep is software designed to support Battery Estimation and Early Prediction of cycle life correspon...

102. [be-smith/navani - GitHub](https://github.com/be-smith/navani) - Navani is a Python module for processing and plotting electrochemical data from battery cyclers, com...

103. [galvani - PyPI](https://pypi.org/project/galvani/0.2.1/) - License: GNU General Public License v3 or later (GPLv3+) (GPLv3+); Author: Chris Kerr; Requires: Pyt...

104. [galvani - PyPI](https://pypi.org/project/galvani/) - Open and process battery charger log data files. Project description: galvani Read proprietary file ...

105. [EIS data of 54 21700 cells - Zenodo](https://zenodo.org/records/15422339) - This dataset contains electrochemical impedance spectroscopy (EIS) data collected from a batch of 21...

106. [Electrochemical Impedance Spectroscopy (EIS) Basics](https://pineresearch.com/support-article/eis-basics/) - Electrochemical impedance spectroscopy is a complicated electroanalytical chemistry technique. This ...

1420. [Automated Extraction of Material Properties using LLM-based AI ...](https://arxiv.org/html/2510.01235v1) - Benchmarking on a manually curated set of 50 papers shows that GPT-4.1 achieves the highest extracti...

