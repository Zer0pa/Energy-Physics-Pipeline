# Converged Electrochemical Energy Conversion — Materials-to-Systems (M2S) Simulation Pipeline

**Zer0pa / Frontier AI Orchestration Lab — April 2026**
*Companion to: In Silico Drug Process Development (2026) and In Silico Materials Science (2026)*

***

## Executive Map — Top Tools Per Pipeline Layer

| Layer | Scientific Function | Top Tool 1 | Top Tool 2 | Top Tool 3 |
|-------|---------------------|-----------|-----------|-----------|
| **L1: Electronic Structure** | Quantum charge-transfer physics | GPAW 24.x (B) | PySCF 2.8 (A) | CP2K 2025.1 (B) |
| **L2: Atomistic / MLIP** | Ion transport, interface dynamics | MACE-OMol25 (A) | eSEN-M fairchem (A†) | LAMMPS (B) |
| **L3: Mesoscale** | Pore-scale transport, microstructure evolution | PF-PINO 2026 (E) | MOOSE + RACCOON (B) | OpenLB 3.1 (B) |
| **L4: Device Scale** | Cell electrochemistry, optoelectronics | PyBaMM v25 (A) | AlphaPEM (A) | Solcore 6 (A) |
| **L5: Stack / System** | Power dispatch, LCOE | PyPSA 0.31 (A) | pvlib-python 0.15 (A) | NREL SAM (A) |
| **L6: Orchestration** | Active learning, multi-layer coupling | AiiDA 2.8 (A) | Atomate2 0.5 (A) | BoTorch + Ax (A) |

***

## Section 1: The Unified Physical Substrate

### 1.1 Confirming — and Refining — the Hypothesis

The working hypothesis is **confirmed and sharpened**. Solar photovoltaics, green hydrogen electrolysis and fuel cells, electrochemical storage, and thermoelectrics are not merely analogous systems — they are governed by the same master physics operating under different boundary conditions. The unifying physical framework is:

> **Charge transfer at a material interface driven by an electrochemical potential gradient, constrained by the second law of thermodynamics.**

Every conversion device in this brief is a realisation of this single mechanism:
- In a solar cell, photon absorption creates an electrochemical potential gradient across a p-n junction, driving electron-hole pair separation and collection.
- In an electrolyser, an applied electrochemical potential gradient drives water oxidation and reduction at electrode surfaces.
- In a fuel cell, spontaneous electrochemical reactions release electrons through an external circuit.
- In a battery, intercalation/de-intercalation of ions under electrochemical driving forces stores and releases charge.
- In a thermoelectric, a temperature gradient drives charge carrier diffusion (Seebeck effect), coupling heat and charge transport via Onsager reciprocal relations.

The deepest unifying equation is the **Butler-Volmer equation** — derived from Marcus theory and the Boltzmann distribution — which governs the current-overpotential relationship at every electrode interface in the pipeline:[^1][^2]

\[ j = j_0 \left[ \exp\!\left(\frac{\alpha F \eta}{RT}\right) - \exp\!\left(-\frac{(1-\alpha) F \eta}{RT}\right) \right] \]

where \( j_0 \) is the exchange current density (set by the electronic structure of the electrode surface), \( \eta \) is the overpotential (the departure from the Nernst equilibrium potential), \( \alpha \) is the charge transfer coefficient (related to the Marcus reorganisation energy \( \lambda \)), \( F \) is the Faraday constant, \( R \) is the gas constant, and \( T \) is temperature. When \( |\eta| \gg RT/F \), this reduces to the Tafel equation; when \( |\eta| \to 0 \), it linearises to ohmic behaviour. Every efficiency limit in electrochemistry — the Nernst potential for fuel cells, the thermodynamic efficiency of electrolysis, the Tafel slope for catalysis — is derived from this equation and the second law[^3].

For photovoltaics, the analogous equation is the **diode equation** \( j = j_{sc} - j_0 \exp(eV/kT) \) which is the Butler-Volmer equation applied to a semiconductor junction under illumination. The Shockley-Queisser limit is the thermodynamic efficiency ceiling derived by applying detailed balance (microscopic reversibility) to this equation.[^3][^4]

### 1.2 Where the Hypothesis Requires Refinement

**Wind energy is structurally distinct.** The conversion physics is fluid mechanical — turbine aerodynamics and structural mechanics — not electrochemical. The shared layer is only the materials layer (blade composites, generator materials) and the system layer (energy dispatch). For this pipeline, wind energy enters as an **input boundary condition** (wind resource data) at Layer 5, not as a simulation domain in its own right. The relevant simulation tool, OpenFAST (NREL, Apache 2.0), operates at the fluid-structural level and produces power-duration curves that feed directly into PyPSA system dispatch.[^5][^6][^7][^8][^9]

**The common substrate does not eliminate domain-specific simulation requirements.** A solar cell requires optical simulation (photon absorption) that has no direct analogue in electrochemistry. Solid oxide devices operate at 600–900°C with mixed ionic-electronic conduction mechanisms absent from room-temperature electrochemistry. Thermoelectrics require phonon transport simulation alongside charge transport. The convergence is at the level of governing equations and information tokens, not tool interchangeability.

***

## Section 2: The Natural Scale Hierarchy — Pipeline Layers

The following layers emerge from the physics. They are not prescribed; they are the natural scale boundaries where the governing equations change character and a new information token must be passed to the next layer.

### Layer 1: Quantum / Electronic Structure (Å–nm scale, femtoseconds)
**What happens**: The electronic structure of electrode materials, photovoltaic absorbers, catalytic surfaces, and electrolyte molecules is computed from first principles. This layer determines: (a) the band gap and optical absorption spectrum of PV materials, (b) the adsorption free energies of intermediates on electrocatalyst surfaces, (c) the Marcus reorganisation energy and electronic coupling for charge transfer rates, (d) ionic migration barriers in solid electrolytes, and (e) topological properties of band structures.[^2][^10]

**Scale-bridging challenge (L1→L2)**: The output of L1 — energies, forces, and reaction free energies at specific configurations — must be assembled into a training dataset for an MLIP or used directly as parameters for L2 kinetic models. This requires active learning loops (DFT → MLIP training → MD → uncertainty → new DFT calculations).

**Primary input token**: CIF file (crystal structure) or SMILES/xyz (molecular structure) + electrochemical potential bias (the applied voltage, expressed as a shift in the Fermi level).

**Primary output token**: Band structure + DOS (electronic density of states), adsorption free energy profiles \( \Delta G_{ads}(\phi) \) as a function of electrode potential, Marcus reorganisation energy \( \lambda \), and optical dielectric function \( \varepsilon(\omega) \).

### Layer 2: Atomistic / MLIP Simulation (nm–μm, picoseconds–microseconds)
**What happens**: Using MLIP potentials trained on L1 data, atomic-scale dynamics are simulated at finite temperature. This layer accesses ion transport coefficients in liquid and solid electrolytes, solvation shell structure around lithium ions, interface formation kinetics (SEI, double layer), and mechanical properties of electrode active materials.[^11][^12]

**Primary input token**: MLIP weights + initial configuration (extxyz) + temperature/pressure/electrochemical potential boundary conditions.

**Primary output token**: Transport coefficients (Li⁺ diffusion coefficient D, ionic conductivity σ, transference number t₊), radial distribution functions, and structural trajectory files (HDF5/LAMMPS dump format).

### Layer 3: Mesoscale — Pore-Scale Transport and Microstructure (μm–mm, microseconds–seconds)
**What happens**: The porous microstructure of electrodes, membranes, and gas diffusion layers is simulated at the scale of individual pores and grain boundaries. Lattice Boltzmann methods solve ion transport in porous electrode architectures; phase field methods simulate dendrite growth, electrode particle fracture, and catalyst coarsening. Kinetic Monte Carlo models surface poisoning and catalyst degradation.[^13][^14][^15]

**Primary input token**: Effective transport coefficients from L2 + pore-scale geometry (from X-ray CT or procedurally generated) + Butler-Volmer kinetic parameters.

**Primary output token**: Effective medium transport parameters (tortuosity factor τ, effective diffusivity D_eff, effective conductivity σ_eff), microstructure evolution trajectories in VTK format, and degradation morphology maps.

### Layer 4: Device Scale — Electrochemical Cell Simulation (mm–cm, steady-state and transient)
**What happens**: The full multi-physics behaviour of an electrochemical device — coupled ion transport, electron transport, reaction kinetics, heat generation, and fluid dynamics — is simulated in the geometry of the actual cell. For batteries, this is the Doyle-Fuller-Newman (DFN/P2D) model; for fuel cells, a coupled CFD-electrochemistry model; for solar cells, coupled optical absorption and semiconductor transport.[^16][^17][^18]

**Primary input token**: Effective transport parameters from L3 + Butler-Volmer kinetic parameters + cell geometry + operating conditions (current, temperature, pressure, illumination spectrum).

**Primary output token**: **Polarization curve** (cell voltage vs. current density, V-j) for electrochemical devices; **J-V curve** for photovoltaics. These are the universal device characterisation tokens. Electrochemical Impedance Spectra (EIS) provide frequency-domain characterisation.

**The polarization curve as the universal information token**: The V-j curve is the electrochemical analogue of SMILES in the pharma pipeline — the compact representation that encodes all of a device's performance information and flows upward through the scale hierarchy. It is parameterised by: open-circuit voltage (OCV = Nernst potential minus losses), exchange current density (from L1 DFT), transport resistances (from L2–L3), and activation overpotentials. This parameterisation is the critical data handoff from L4 to L5.

### Layer 5: Stack, Module, and System Scale (cm–km, hours–years)
**What happens**: Individual cells are assembled into stacks, then into systems with balance-of-plant components (thermal management, power electronics, compressors, inverters). Performance modelling accounts for cell-to-stack scaling, degradation trajectories over thousands of cycles, and techno-economic analysis under real-world weather and grid conditions.[^19][^20][^21]

**Primary input token**: V-j curve + degradation rate parameters + balance-of-plant specifications + resource data (solar irradiance, wind speed, grid price timeseries).

**Primary output token**: **Levelised Cost of Energy (LCOE)** in $/kWh for electricity, or **Levelised Cost of Hydrogen (LCOH)** in $/kg — the final delivered value metrics. Also: capacity factor, reliability distribution, degradation trajectory to end-of-life.

### Layer 6: Orchestration and Active Learning (Meta-layer, all scales)
**What happens**: Bayesian optimisation algorithms or reinforcement learning agents propose material modifications or process parameter changes, dispatch simulations across L1–L5, and update surrogate models to converge on optimal materials/device/system designs. This is Zer0pa's natural operating domain.[^22][^19]

***

## Section 3: Resource Map by Layer

### 3.1 Layer 1: Quantum / Electronic Structure Tools

#### GPAW 24.x (Technical University of Denmark / Psi-k)
**What it does**: Python-native DFT code supporting real-space grids, plane waves, and numerical atomic orbitals (NAO). Unique dual capability: ground-state DFT (electrode surface adsorption energies) AND many-body methods — GW band structures for accurate photovoltaic band gaps, Bethe-Salpeter Equation (BSE) for optical spectra, and real-time TDDFT for photocurrent simulation. The most complete open-source code for the photovoltaics simulation workflow.[^10][^23]
**Maintained**: Active — 2024 major paper published in JCP.[^23]
**License**: GPL v3 — **Class B**. Outputs (band structures, optical spectra, adsorption free energies) fully commercialisable.
**Python API**: Full — GPAW is a Python package with ASE integration; `from gpaw import GPAW`.
**GPU support**: Limited; primarily CPU + MPI.
**Performance**: State-of-art for optical spectra from BSE; competitive for surface adsorption calculations.
**Key application**: PV band gap prediction (GW), optical absorption for solar cell efficiency limits (BSE), real-time carrier dynamics (rt-TDDFT).[^24][^25]
**Integration**: ASE calculator interface; AiiDA-GPAW plugin.

#### PySCF 2.8
**What it does**: Apache-licensed quantum chemistry Python package supporting DFT, CDFT (Constrained DFT), TDDFT, GW, and periodic solid-state calculations. The **constrained DFT (CDFT) module** is the primary open-source tool for computing Marcus theory parameters (reorganisation energy λ, electronic coupling V_DA) for charge transfer reactions in batteries and electrocatalysis.[^1]
**License**: Apache 2.0 — **Class A**.
**Python API**: Native Python library — `from pyscf import gto, dft`.
**Key application**: Marcus theory parameter computation for electrocatalyst kinetics, charge transfer rates in organic photovoltaics.[^26][^1]
**CDFT for Marcus theory**: The combination CDFT + AIMD for computing Marcus parameters — "we use the Marcus theory to predict electron transfer rates and the combined CDFT-AIMD approach to compute the parameters" — is a published production workflow for electrochemical devices.[^1]

#### CP2K 2025.1
**What it does**: Hybrid QM/MM and mixed Gaussian/plane-wave DFT. Best-in-class for DFT-MD at solid-liquid interfaces — the exact simulation type needed for electrolyte decomposition, SEI formation, and catalyst surface dynamics under electrochemical conditions[^1186].[^11]
**License**: GPL v2 — **Class B**.
**Python API**: AiiDA-CP2K plugin; cp2k-input-tools.
**Key application**: AIMD of liquid electrolytes at electrode surfaces to generate MLIP training data.

#### Wannier90 + Z2Pack (Band topology for energy applications)
**What it does**: Wannier90 computes maximally localised Wannier functions from DFT output — the required preprocessing step for computing Berry phase, Chern numbers, and topological invariants. Z2Pack then uses these to classify materials as topological insulators, Weyl semimetals, or trivial. For energy applications, this identifies materials with topologically protected surface states that could enhance charge transport.[^27][^28][^29]
**License**: GPL — **Class B**.
**Key application**: Screening PV and thermoelectric materials for topological features that protect charge carrier transport; identifying non-trivial thermoelectric band topology.

#### VASP 6.6.0 — Note on commercial role
VASP remains the fastest code for hybrid functional and GW calculations and was used to generate the majority of Materials Project, AFLOW, and NOMAD training data. However, it is **Class D** (commercial license required). For Zer0pa's pipeline, VASP is the tool to use for one-time, high-accuracy reference calculations; the results flow into MLIP training datasets that are then open. The commercial license cost (~EUR 5,000/year academic) is warranted for benchmark reference data generation but not for production screening.[^30]

***

### 3.2 Layer 2: Atomistic / MLIP for Electrochemical Systems

#### MACE-OMol25 (Cambridge + Meta FAIR, 2025)
**What it does**: MACE architecture fine-tuned on the OMol25 dataset (100M+ DFT calculations at ωB97M-V/def2-TZVPD level — the most accurate DFT functional used for a dataset at this scale). Covers molecules in condensed phase, aqueous electrolytes, ionic liquids, and organic solvents — the complete chemical space of battery and fuel cell electrolytes. Transition state search benchmark: 96.6% success rate on organic chemistry.[^31][^32][^33][^34]
**License**: MIT — **Class A**. Fully commercialisable.
**Python API**: `pip install mace-torch`; fairchem integration.
**Key application**: Liquid electrolyte dynamics simulation (ionic conductivity, solvation structure, SEI formation kinetics); transition state searches for electrocatalytic reaction networks.
**Performance**: Outperforms UMA-Small and AIMNet2 on OMol25 benchmarks for molecular chemistry.[^32]

#### eSEN-M (Meta FAIR, fairchem library, September 2025)
**What it does**: The best-performing model on the OC25 dataset (solid-liquid catalysis interfaces). Energy MAE of 0.060 eV, force MAE of 0.009 eV/Å, solvation energy MAE of 0.04 eV — state of art for heterogeneous catalysis with explicit solvent.[^35][^36][^37]
**License**: Apache 2.0 via fairchem — **Class A†** (same geographic restrictions as UMA; verify before deployment from South Africa).
**Python API**: `pip install fairchem-core`.
**Key application**: Screening of electrocatalyst surfaces for OER/HER/CO₂RR activity; reaction energy profiles at solid-liquid interfaces relevant to PEM electrolysers and fuel cells.
**Datasets**: Trained on OC25 (7.8M DFT calculations, solid-liquid interfaces, CC-BY-4.0).[^35]

#### BAMBOO (ByteDance AI Molecular Simulation, 2024)
**What it does**: Physics-inspired graph equivariant transformer architecture specifically designed for liquid electrolyte simulation — demonstrated for Li-ion battery electrolytes. Includes ensemble knowledge distillation for reducing prediction uncertainty in condensed-phase environments.[^12]
**License**: Not publicly released as open-source (ByteDance proprietary) — **Class E**. The methodology is published; independent reimplementation is feasible using MACE-OMol25 as the base architecture.
**Strategic note**: Use MACE-OMol25 (MIT) rather than BAMBOO for commercial deployment; equivalent capability through fine-tuning on OMol25 electrolyte subsets.

#### PEMD (City University of Hong Kong + collaborators, Digital Discovery 2026)
**What it does**: Open-source Python framework that unifies polymer construction, OPLS-AA force field parameterisation, multiscale simulation, and property analysis specifically for polymer electrolytes. Designed for high-throughput screening of solid polymer electrolytes for next-generation batteries.[^38][^39][^40][^41]
**License**: The paper is published in RSC Digital Discovery; GitHub code license requires verification — **Class E (pending)**.
**Key application**: Solid-state battery polymer electrolyte discovery; bridges L1 DFT to L4 device performance for solid-state batteries.
**Strategic note**: Verify license on GitHub before production use. If MIT/Apache, this is the most capable open tool for polymer electrolyte simulation.

#### PiNN / PiNet2 (Uppsala University, January 2025)
**What it does**: Equivariant neural network suite specifically designed for electrochemical systems — models potential energy surfaces, dipole moments, and charge response kernels for electrochemical interfaces. PiNet2-dipole predicts polarisation-dependent properties; PiNet2-χ generates atom-condensed charge response kernels for modelling electrode-electrolyte interactions.[^42]
**License**: Published in JCTC; GitHub code license requires verification.
**Key application**: Electrochemical interface modelling where charge distribution under applied potential is explicitly required.

#### LAMMPS (Sandia National Laboratories)
**What it does**: Large-scale parallel MD engine. The integration platform for all MLIPs (MACE, CHGNet, SevenNet all support LAMMPS via KOKKOS/ML-PACE interfaces). GPU-accelerated. Essential for production MD at electrode/electrolyte interfaces.
**License**: GPL v2 — **Class B**.
**Python API**: lammps Python module (in-process calling); AiiDA-LAMMPS plugin.

***

### 3.3 Layer 3: Mesoscale — Pore-Scale Transport and Microstructure

#### PF-PINO (Physics-Informed Neural Operator for Phase Field, March 2026)
**What it does**: Neural operator framework that learns parametric phase-field PDEs — Allen-Cahn, Cahn-Hilliard, and coupled systems — by embedding physical residuals into the loss function. Validated on **electrochemical corrosion, dendritic crystal solidification, and spinodal decomposition** — the three most important mesoscale degradation mechanisms in batteries and fuel cells. "PF-PINO significantly outperforms conventional FNO in accuracy, generalisation capability, and long-term stability".[^14][^15]
**License**: March 2026 preprint; GitHub code license **Class E (pending)**. Verify before production use.
**Python API**: PyTorch-based neural operator; GPU-accelerated.
**Key application**: Mesh-free, differentiable battery dendrite simulation; electrode cracking prediction; SEI microstructure evolution. Orders of magnitude faster than PRISMS-PF for parametric sweeps.
**Intersectional significance**: PF-PINO is simultaneously: a physics simulator (solves Allen-Cahn), a differentiable ML model (end-to-end trainable), and a continuous cellular automaton (Allen-Cahn ≡ reaction-diffusion ≡ Turing morphogenesis). For Zer0pa, this is the exact cellular automata ↔ phase field ↔ neural operator convergence.

#### MOOSE Framework + RACCOON (Idaho National Laboratory)
**What it does**: MOOSE is the general-purpose multi-physics FEM framework; RACCOON is its electrochemistry module for battery degradation simulation. Implements phase field fracture mechanics, electrochemical transport, and mechanical-electrochemical coupling — the full physics of electrode particle cracking during cycling.[^43]
**License**: LGPL — **Class B**.
**Python API**: Python scripting for parameter studies.
**Key application**: Coupled electrochemical-mechanical degradation of battery electrodes; SEI layer growth simulation.

#### OpenLB 3.1 (Lattice Boltzmann Method)
**What it does**: Open-source Lattice Boltzmann framework with specific modules for electrochemical applications — including Poisson-Nernst-Planck equations for ion transport in porous electrodes, multi-component flow for gas evolution in electrolysers, and thermal LB for heat management in fuel cells.[^44][^13]
**License**: GPL v2 — **Class B**.
**Python API**: C++ core with Python post-processing; no native Python API.
**Key application**: Pore-scale ion transport in porous battery electrodes; bubble transport in alkaline electrolysers; gas diffusion layer simulation in fuel cells.
**Significance**: Lattice Boltzmann is the mesoscale bridge between L2 molecular transport and L4 device-scale effective-medium models. Ion transport measured in LB simulations provides the effective diffusivity input for L4 battery models.

#### LBPM (Digital Rocks Portal, UT Austin)
**What it does**: Lattice Boltzmann Porous Media simulator — designed for multi-phase flow through arbitrary porous geometries. Can import X-ray CT reconstructions of electrode microstructures directly.
**License**: Apache 2.0 — **Class A**.
**Python API**: Limited; primarily C++ with HDF5 output.

***

### 3.4 Layer 4: Device-Scale Simulation

#### PyBaMM v25 (Python Battery Mathematical Modelling, Faraday Institution)
**What it does**: The most complete open-source battery modelling framework. Implements the full Doyle-Fuller-Newman (DFN/P2D) model, Single Particle Model (SPM), thermal models, and coupled degradation mechanisms — SEI growth, lithium plating, active material loss, mechanical stress. Current version v25.10.x.[^17][^45][^46][^47][^48][^49]
**Maintained**: Actively maintained; monthly releases; homepage confirms April 2026 active status.[^17]
**License**: BSD-3-Clause — **Class A**. Fully commercialisable.
**Python API**: Full — `pip install pybamm`; Jupyter-native.
**GPU support**: No (CPU-based; but fast for 1D models).
**Performance**: Benchmark: PyBaMM P2D model validated against COMSOL in multiple studies; "PyBaMM enables efficient simulations of battery performance and aging". Three open-source porous electrode theory codes benchmarked: dualfoil, MPET, and LIONSIMBA, with PyBaMM emerging as the maintained standard.[^50][^17]
**Integration**: PyBOP for parameter optimisation; CASADI for JIT compilation; can call LAMMPS/MD transport inputs.
**Commercialisability**: Full.

#### PyBOP — Battery Optimisation and Parameterisation
**What it does**: Bayesian and frequentist parameter estimation for PyBaMM models from experimental data. Uses PyBaMM as the forward model; supports MCMC, optimisation, and uncertainty quantification.[^51][^52][^53][^54]
**License**: BSD — **Class A**.
**Python API**: Full — `pip install pybop`.
**Application**: Fitting P2D model parameters from experimental EIS and cycling data; closing the L4 ↔ experimental validation loop.

#### AlphaPEM (1D Dynamic PEM Fuel Cell Model, arXiv July 2024)
**What it does**: Open-source Python 1D physics-based PEM fuel cell simulator. Experimentally validated; models hydrogen feed, proton transport, oxygen reduction, water management, and thermal dynamics. Designed for both research and embedded applications.[^16]
**License**: MIT — **Class A** (from arXiv submission context; verify on GitHub).
**Python API**: Full Python; graphical interface also available.
**Application**: PEM fuel cell system simulation; dynamic response under variable hydrogen supply (relevant to green hydrogen dispatch models).

#### openFuelCell2 (CFD-based, OpenFOAM)
**What it does**: 3D CFD toolbox built on OpenFOAM for simulating PEM fuel cells and electrolysers. Models multi-phase transport, electrochemical reactions, and membrane physics. Peer-reviewed in OpenFOAM Journal 2023.[^55][^56][^57]
**License**: GPL (OpenFOAM-based) — **Class B**.
**Python API**: Via PyFOAM; primarily CLI.
**Application**: 3D optimisation of fuel cell/electrolyser geometry; gas diffusion layer design; membrane electrode assembly thickness effects.

#### Cantera 3.2
**What it does**: Open-source suite for chemical kinetics, thermodynamics, and transport. Has specific SOFC module implementing elementary kinetics for solid oxide fuel cells — "unlike most SOFC models, this model does not use semi-empirical Butler-Volmer kinetics". Used in solid oxide co-electrolysis system modelling.[^58][^59][^60]
**License**: BSD — **Class A**. Fully commercialisable.
**Python API**: Full — `import cantera as ct`.
**Key application**: SOFC/SOEC with elementary kinetics; hydrogen production from high-temperature electrolysis; thermodynamic cycle analysis.[^60][^58]

#### Solcore 6 (Imperial College London)
**What it does**: Multi-scale Python library for modelling solar cells — from quantum confinement in nanostructures to full solar array performance. Unique among open-source tools in spanning: quantum well physics (Schrödinger-Poisson), optical simulation (transfer matrix + rigorous coupled wave analysis), electronic transport (drift-diffusion), and system performance under real-world spectra.[^18][^61][^62][^63]
**Maintained**: Active on PyPI (July 2025 update); homepage active.[^61][^62]
**License**: BSD — **Class A**. Fully commercialisable.
**Python API**: Full — `pip install solcore`.
**Application**: Multi-junction PV cell design (GaInP/InGaAs/Ge); perovskite tandem simulation; Shockley-Queisser efficiency limit analysis.[^64]

#### OghmaNano (formerly GPVDM)
**What it does**: General-purpose solar cell device simulator for thin-film devices — organic solar cells, OLEDs, OFETs, perovskite solar cells. Implements optical + electrical + thermal coupled simulation.[^65]
**License**: GPL — **Class B**.
**Python API**: Limited; primarily GUI-based.
**Application**: Organic and perovskite solar cell optimisation; defect physics analysis.

#### SCAPS-1D (University of Ghent)
**What it does**: Solar Cell Capacitance Simulator — the most widely used solar cell simulation tool globally for thin-film devices. Used to validate perovskite, CIGS, CdTe, and Sb₂(S,Se)₃ cell designs.[^66][^67][^68][^69]
**License**: Free download for academic use — **Class C**. Commercial use requires license negotiation. The SCAPS authors explicitly state it is for "non-commercial, academic research" use only.
**Python API**: No Python API; GUI-based with batch script mode.
**Open alternative**: OghmaNano (GPL) for production pipeline; Solcore (BSD) for scripted use cases.
**License Risk Flag**: SCAPS-1D is Class C — not usable in a commercial pipeline without explicit license. Use Solcore (BSD) or OghmaNano (GPL) as production alternatives.

***

### 3.5 Layer 5: Stack, Module, and System Scale

#### PyPSA 0.31 (Python for Power System Analysis)
**What it does**: The dominant open-source energy system optimisation platform. Handles multi-period linear and non-linear optimisation of power systems with renewable generation, storage, sector coupling (hydrogen, heat, transport), and grid transmission. PyPSA-Earth sector-coupled (Applied Energy 2025) extends to global energy system modelling with explicit hydrogen production pathways.[^70][^20][^71][^72][^19]
**Maintained**: Actively maintained; April 2026 confirmed active on GitHub.[^72]
**License**: MIT — **Class A**. Fully commercialisable.
**Python API**: Full — `pip install pypsa`.
**Application**: LCOE optimisation for hybrid solar-hydrogen systems; grid integration of variable PV/wind; optimal sizing of electrolyser-storage systems.[^71][^19]
**Integration**: Accepts polarisation curves and degradation rates from L4; interfaces with NREL SAM for resource data; outputs LCOH and LCOE distributions.

#### pvlib-python 0.15 (NREL / Sandia / Community)
**What it does**: Community-developed, NREL-maintained PV system performance simulation library. Implements all standard PV performance models (single-diode, PVWatts, Sandia Performance Model), irradiance transposition, temperature modelling, and spectral correction for real-world conditions.[^73][^74][^75][^76]
**License**: BSD-3-Clause — **Class A**. Fully commercialisable.
**Python API**: Full — `pip install pvlib`.
**Application**: Annual energy yield prediction; spectral mismatch correction for perovskite/tandem cells; integration with L4 Solcore for full materials-to-system chain.

#### NREL SAM (System Advisor Model) with pySAM
**What it does**: NREL's comprehensive techno-economic simulator for grid-connected renewable energy systems — solar PV, CSP, wind, geothermal, battery storage, and hydrogen. The pySAM Python API enables programmatic access to all SAM models.[^77][^78][^79][^80][^81]
**License**: BSD (open-source on GitHub, NREL/SAM) — **Class A**.[^80]
**Python API**: pySAM — `pip install nrel-pysam`.
**Application**: Full project financial modelling from material performance to LCOE/LCOH; hydrogen production economics for CSP-SOEC coupled systems.[^82][^83]

#### OpenFAST (NREL, Wind Turbine)
**What it does**: Open-source aero-hydro-servo-elastic wind turbine simulation tool. Models full turbine structural dynamics, aerodynamics, hydrodynamics (offshore), and control systems. Validated against commercial tools (BLADED, Flex5) within 3–15%.[^6][^7][^8][^9][^5]
**License**: Apache 2.0 — **Class A**.
**Python API**: OpenFAST Python bindings; also accessible via AeroElasticSE wrapper.
**Role in M2S pipeline**: Wind resource → OpenFAST power curve → PyPSA dispatch input. The wind materials component (blade composites, superconducting generators) feeds into the materials pipeline; the system output feeds into PyPSA.

***

### 3.6 Layer 6: Orchestration and Active Learning

See the companion Materials Science report (April 2026) for full coverage of AiiDA 2.8, Atomate2 0.5, pyiron, and BoTorch + Ax. The energy-specific orchestration additions are:

**PyBaMM + PyBOP active learning loop**: PyBaMM forward model + PyBOP Bayesian inference + experimental cycling data → optimal cell parameters → modified electrode design. This closes the battery design loop entirely within open-source Python.[^54][^51]

**fairchem (Meta FAIR, Apache 2.0)**: The unified Python API for accessing OC20, OC22, OC25 datasets and all associated models (eSEN, UMA, MACE-OMol25). The production tool for agentic electrocatalyst screening[^1002].

**Chemical foundation model-guided electrolyte discovery (Nat NPJ 2025)**: Demonstrates the commercial-grade active learning workflow — fine-tuned foundation model + generative screening → 7 novel high ionic conductivity electrolyte formulations discovered from 58 initial data points. This is the blueprint for the L6 orchestration layer for battery electrolytes.[^84]

***

## Section 4: Dataset and Database Catalogue

| Dataset | Domain | Size | License | ML-Ready | Access | Notes |
|---------|--------|------|---------|----------|--------|-------|
| **OC25** | Electrocatalysis (solid-liquid) | 7.8M DFT calculations | CC-BY-4.0 | Yes — fairchem loaders | fairchem GitHub[^35][^36] | Best dataset for solid-liquid interface catalysis |
| **OMol25** | Molecular chemistry, electrolytes | 100M+ DFT at ωB97M-V | CC-BY-4.0 | Yes — fairchem | fairchem GitHub[^32][^33] | Includes electrolyte solvents, ionic liquids |
| **AQCat25** | Heterogeneous catalysis (spin-aware) | 13.5M DFT | **Non-commercial (Class C)** | Yes — Hugging Face[^85] | Contact SandboxAQ for commercial | Full periodic table, spin polarisation |
| **OC20 / OC22** | Heterogeneous catalysis | 1.3M / 8.7M | CC-BY-4.0 | Yes — fairchem | fairchem[^86] | Foundation training data for catalysis models |
| **OCx24** | Experimental catalysis | 572 experimental samples | CC-BY-4.0 | Partial | Open Catalyst GitHub[^87] | Bridges simulation-to-experiment gap |
| **Materials Project Battery Explorer** | Battery materials | 500+ battery compounds | CC-BY-4.0 | Yes — pymatgen | next-gen.materialsproject.org/api | Intercalation voltages, capacities, stability |
| **JARVIS-DFT** | All functional materials | 80,000+ structures | NIST Public Domain | Yes | JARVIS API + OPTIMADE[^88][^89] | Includes thermoelectric, topological tasks |
| **CALCE Battery Dataset** | Battery degradation | >100 degradation trajectories | Academic free | Partial | calce.umd.edu | The standard battery ageing benchmark |
| **Oxford Battery Degradation** | Battery degradation | 48 LFP cells, 1,000+ cycles | CC-BY-4.0 | Yes | Zenodo[^90] | Used in NREL PINN training |
| **NREL NSRDB** | Solar irradiance (US/global) | 2km resolution, hourly | Public domain | Yes — pvlib API | developer.nrel.gov | National Solar Radiation Database |
| **ERA5 Reanalysis** | Wind + solar resource | Global, hourly, 31km | Copernicus CDS | Yes — xarray | copernicus.eu | Used in PyPSA-Earth for global energy models |
| **NASA POWER** | Global solar + meteorological | 0.5° resolution, daily | Public domain | Yes | power.larc.nasa.gov/api/ | Simple REST API, direct pvlib integration |
| **AFLOW Battery** | Battery cathode structures | 10,000+ structures | Custom free | Partial | AFLOW API | Li-ion, Na-ion, Mg-ion cathode materials |
| **OMat24** | Inorganic materials (electrode) | 110M+ DFT | CC-BY-4.0 | Yes — fairchem | fairchem[^91] | Training data for universal MLIPs for electrode materials |
| **Electrochemical CO₂ corpus** | Electrocatalysis literature | 6,086 NER annotations | Open | Yes | Published dataset[^92] | Text mining for catalyst property extraction |
| **Matbench-PV** | Photovoltaic materials | Subset of MatBench | MIT | Yes | matbench Python package | Band gap prediction tasks |

***

## Section 5: Machine Learning Models for Electrochemical Energy

### Foundation Models for Electrochemistry

#### eSEN-M (Meta FAIR, OC25, fairchem)
The current state-of-art model for solid-liquid interface electrocatalysis. On OC25 test set: energy MAE 0.060 eV, force MAE 0.009 eV/Å, solvation energy MAE 0.04 eV — best-in-class on all three metrics. Apache 2.0, Python API via fairchem.[^37][^35]

#### AQCat25-EV2 (SandboxAQ, October 2025)
The first heterogeneous catalyst model with full periodic table coverage including spin polarisation effects. Trained on 13.5M DFT calculations with spin-polarised reference data. "Predicts energetics with accuracy approaching quantum-mechanical methods at speeds up to 20,000x faster". Architecture: equivariant GNN v2 with spin-aware features. **License: Non-commercial (Class C)** — contact SandboxAQ for commercial licensing. The most capable model for industrial catalysis screening but requires commercial negotiation.[^93][^85][^94]

#### MACE-OMol25 (MIT, Cambridge/Meta)
MACE fine-tuned on OMol25 molecular dataset. 96.6% transition state search success rate on organic chemistry. Best open-source choice for electrolyte molecular dynamics and reaction pathway screening in electrochemical systems. MIT license = Class A, fully commercialisable.[^31]

#### PiNN/PiNet2 (Uppsala, JCTC January 2025)
Equivariant NN suite specifically designed for electrochemical systems — models potential energy surfaces AND charge response under applied electrochemical potential. The first open-source MLIP that explicitly treats electrochemical bias as an input variable rather than requiring separate DFT runs at each potential.[^42]

#### NREL PINN Battery Surrogate (NREL, June 2025)
Physics-informed neural network that replaces the P2D battery model — "predicts battery health nearly 1,000 times faster than traditional models". Trained on PyBaMM P2D simulations; validated against laboratory cycling data. The PINN separates physical degradation mechanisms from voltage output. **Open-source** — released by NREL. This is the production-grade surrogate for L4→L5 battery degradation modelling.[^90]

#### PINN-RUL for PEM Fuel Cells (Applied Energy, February 2025)
Physics-informed neural network for prognosticating remaining useful life (RUL) of PEM fuel cells — "9.2% improvement over SOTA, 26% input data requirement". Directly applicable to fuel cell fleet management and techno-economic modelling.[^95][^96]

***

## Section 6: Frontier Watch (2024–2026)

*Sorted by strategic impact on the M2S pipeline.*

### 6.1 PF-PINO: Physics-Informed Neural Operator for Phase Field (March 2026)
**What broke**: Phase field simulation of battery dendrite growth and electrochemical corrosion required expensive mesh-based FEM solvers. PF-PINO demonstrates that physics-informed neural operators solve Allen-Cahn and Cahn-Hilliard equations without mesh discretisation, validated on **electrochemical corrosion, dendrite solidification, and spinodal decomposition** simultaneously. "Significantly outperforms standard FNO in accuracy, generalisation capability, and long-term stability".[^15][^14]

**Why it matters for M2S**: Battery dendrite prediction has been a simulation bottleneck at Layer 3. PF-PINO is GPU-accelerated, differentiable, and mesh-free — it can be called from a Python orchestration layer like any other ML model. The differentiability enables gradient-based optimisation of electrolyte composition to minimise dendrite formation rate.

**Cross-domain signal**: PF-PINO is the exact cellular automata ↔ phase field ↔ neural operator convergence Zer0pa predicted. The Allen-Cahn equation is a continuous Turing morphogenesis system; PF-PINN is a neural network solving it; the result is a differentiable simulator for cellular-automaton-like electrochemical degradation dynamics.

### 6.2 OC25 + eSEN-M: Electrocatalysis Enters the Explicit Solvent Era (September 2025)
**What broke**: All prior open catalyst benchmarks (OC20, OC22) used implicit solvation models or vacuum calculations. OC25 introduces 7.8 million DFT calculations at **explicit solid-liquid interfaces** — catalyst surfaces surrounded by real water molecules and dissolved ions. eSEN-M achieves energy MAE 0.060 eV on this benchmark.[^36][^97][^35]

**Why it matters**: Electrochemical reactions happen at solid-liquid interfaces. Models trained on vacuum surface calculations systematically underpredict overpotentials and misorder catalyst activity. OC25 closes this gap, enabling quantitatively reliable prediction of HER, OER, CO₂RR, and N₂RR catalysis at real operating conditions.[^35]

**Implication for M2S pipeline**: The L1→L2→L3 chain for electrocatalysis is now: DFT adsorption energies on explicit solvated surfaces (OC25 data) → eSEN-M MLIP screening → macro-kinetic reaction network (Cantera) → L4 device overpotential. This chain is entirely open-source and approaches experimental accuracy.

### 6.3 AQCat25-EV2: Full Periodic Table Heterogeneous Catalysis (October 2025)
**What broke**: Prior universal MLIPs for catalysis underperformed on 3d/4d/5d transition metals due to missing spin polarisation training data. AQCat25-EV2, trained on 13.5M spin-aware DFT calculations, is "the first heterogeneous catalyst model which can be consistently and robustly applied across the entire periodic table".[^94][^93]

**The 20,000x acceleration**: For transition metal catalyst screening — IrO₂ OER catalysts, MoS₂ HER catalysts, single-atom catalysts for CO₂RR — AQCat25-EV2 runs at 20,000x the speed of DFT with near-DFT accuracy.[^93]

**Commercial access note**: Dataset on Hugging Face with non-commercial licence. Commercial licence negotiation with SandboxAQ required. Consider using eSEN-M (Apache 2.0, OC25 training data) as the open alternative with comparable performance at solid-liquid interfaces.[^85]

### 6.4 Chemical Foundation Model for Electrolyte Discovery (Nat. Comput. Mat., August 2025)
**What broke**: Electrolyte formulation has historically been empirical — thousands of experimental trials. A chemical foundation model, fine-tuned for ionic conductivity prediction and paired with generative screening, **identified 7 novel high-conductivity electrolytes from only 58 initial data points**. The approach uses transfer learning from a large-scale molecular foundation model, fine-tuned on sparse electrolyte data.[^84]

**Why it matters**: This is the active learning loop operating at maximum sample efficiency — a direct demonstration of the Zer0pa commercialisation model. The output is novel electrolyte formulations; the input is a foundation model + 58 experiments. The computational pipeline is open; the discovered formulations are yours.

### 6.5 OMol25: The Foundation Dataset for Molecular Electrochemistry (May 2025)
**What broke**: No large-scale molecular dataset existed at hybrid DFT accuracy (ωB97M-V/def2-TZVPD). OMol25 provides 100M+ calculations at this level — "representing billions of CPU core-hours". Covers 83 elements, Li/Na/Mg electrolyte solvents, ionic liquids, polymers, and biological molecules.[^98][^33][^32]

**Why it matters**: Every MLIP trained on OMol25 inherits state-of-art quantum chemical accuracy for electrolyte chemistry. MACE-OMol25 is the direct product. For battery liquid electrolytes, solid polymer electrolytes, and fuel cell ionomer modelling, OMol25 is the training foundation.

### 6.6 NREL PINN Battery Surrogate (June 2025)
**What broke**: Real-time battery state-of-health diagnostics required running the full P2D model — impractical for embedded systems. NREL's PINN surrogate separates physical degradation mechanisms from voltage output at ~1,000x speedup.[^90]

**Why it matters**: This is the L4 → production deployment bridge. The NREL PINN is open-source and can be integrated into a PyBaMM/PyBOP active learning loop — where the PINN provides rapid state-of-health estimates and PyBOP Bayesian inference updates model parameters from field data. This is the battery digital twin architecture.

### 6.7 PyPSA-Earth Sector-Coupled (Applied Energy, February 2025)
**What broke**: Energy system models were either national (limited geographic scope) or lacked sector coupling (hydrogen, heat, transport). PyPSA-Earth sector-coupled provides global coverage with explicit hydrogen production pathways, electrolysis modelling, and renewable dispatch co-optimisation.[^19][^71]

**Why it matters**: The L5 → L6 interface is now a global, sector-coupled optimisation problem with MIT-licensed open-source tools. A materials discovery result at L1 (new electrocatalyst) can be propagated all the way to LCOH at L5 in a single orchestrated pipeline.

***

## Section 7: Cross-Domain Connections

### 7.1 Marcus Theory ↔ Shannon Information Theory — The Unexploited Unification

Marcus theory describes the electron transfer rate as:[^99][^26][^1]
\[ k_{et} = \frac{2\pi}{\hbar} |V_{DA}|^2 \frac{1}{\sqrt{4\pi\lambda k_BT}} \exp\!\left(-\frac{(\Delta G^0 + \lambda)^2}{4\lambda k_BT}\right) \]

where \( V_{DA} \) is the electronic coupling, \( \lambda \) is the reorganisation energy, and \( \Delta G^0 \) is the reaction free energy. This is formally equivalent to a channel capacity problem: the Gaussian factor is the probability of successful charge transfer over a noisy thermal barrier; \( \lambda \) is the effective "noise variance" of the thermal bath; \( \Delta G^0 \) is the "signal amplitude"; and \( k_{et} \) is the information-theoretic channel rate.

**The practical implication**: Optimising an electrocatalyst for maximum current density at minimum overpotential is equivalent to maximising the channel capacity of a noisy communication channel — choosing \( \Delta G^0 \) and \( \lambda \) to maximise \( k_{et} \) subject to thermodynamic constraints. Information-theoretic optimisation methods (capacity-achieving codes, rate-distortion theory) have direct mathematical analogues in Marcus theory electrocatalyst design. This connection is recognised in the literature but not computationally exploited. **For Zer0pa**: this is a direct import of information theory tooling into electrocatalyst design.[^99]

### 7.2 Topological Band Theory ↔ Fibre Bundle Theory — Applied to Energy Materials

The Brillouin zone of a crystal is a 3-torus (a topological manifold). The electron wavefunction phases define a vector bundle over this torus — a fibre bundle where the fibre at each k-point is the space of occupied Bloch states. The Chern number of this bundle is an integer topological invariant that counts the number of protected surface state branches. In topological insulators, these protected surface states carry charge without bulk scattering — ideal for photovoltaic carrier collection and thermoelectric transport.[^100][^101][^27]

**Tools**: GPAW (DFT) → Wannier90 (Wannierisation) → Z2Pack (Chern number / Z₂ invariant) → WannierTools (surface state simulation).[^27]

**Current state**: The JARVIS-DFT topological dataset contains thousands of computed topological materials; the Z2Pack + WannierTools toolchain is open-source (GPL) and Python-accessible. This is a mature enough computational capability to deploy in the M2S pipeline as a topology-screening layer at L1.

**For Zer0pa**: The fibre bundle computation is geometric unity applied to solid-state physics. The Berry curvature \( \Omega_n(\mathbf{k}) = -2 \text{Im} \langle \partial_{k_x} u_n | \partial_{k_y} u_n \rangle \) is the curvature 2-form of the Berry connection — a gauge field on the Brillouin zone bundle. Computing topological invariants for PV and thermoelectric materials is a direct application of the lab's geometric unity framework.

### 7.3 Cellular Automata / Reaction-Diffusion ↔ Electrochemical Degradation — PF-PINO as the Bridge

Dendrite growth in batteries, corrosion of fuel cell membranes, and catalyst coarsening are all reaction-diffusion processes — governed by the same mathematical framework as Turing morphogenesis. PF-PINO (March 2026) makes this computation practically accessible: it trains a neural operator to solve Allen-Cahn/Cahn-Hilliard equations that are continuous generalisations of cellular automata.[^14][^15]

**The specific cross-domain connection**: SPPARKS (Sandia, GPL) implements kMC on lattices that are literal discrete cellular automata — local transition rules producing emergent microstructure. SPPARKS + PF-PINO together span the discrete (kMC) and continuous (phase field PDE) limits of the same mathematical object. Training PF-PINO on SPPARKS-generated data would produce a continuous, differentiable cellular automaton model for electrochemical microstructure evolution.

### 7.4 Onsager Reciprocal Relations ↔ Coupled Transport in Thermoelectrics and Fuel Cells

Onsager's reciprocal relations state that the matrix of phenomenological coefficients coupling thermodynamic fluxes to forces is symmetric: \( L_{ij} = L_{ji} \). For thermoelectric materials, this relates the Seebeck and Peltier effects; for fuel cells, it couples heat and mass transport; for batteries, it couples ionic and electronic fluxes. A 2025 Nature study confirmed Onsager reciprocity in biological subcellular systems — validating its universality even far from equilibrium.[^102]

**Computational tools**: Computing Onsager transport coefficients from first principles requires AIMD (CP2K) or MLIP-MD (MACE-OMol25) trajectories analysed with Green-Kubo formulas. The Python package MDYNE implements Green-Kubo transport coefficient calculation from MD trajectories (MIT license). This is the L2 → L4 handoff for thermoelectric device simulation.

**For Zer0pa**: The Onsager matrix is a tensor representation of coupled transport — formally analogous to the coupling matrices in cognitive theory (Hebbian weight matrices, connectivity tensors in neural field theory). The same tensor analysis tools apply.

### 7.5 Non-Equilibrium Thermodynamics ↔ Stochastic Thermodynamics for Electrochemical Kinetics

The Jarzynski equality and Crooks fluctuation theorem from stochastic thermodynamics provide **exact** relations between non-equilibrium work and equilibrium free energy differences: \( \langle e^{-W/k_BT} \rangle = e^{-\Delta F/k_BT} \). These enable computing free energy differences (electrochemical reaction free energies) from non-equilibrium MD trajectories without the slow convergence of equilibrium methods. This is directly applicable to computing Butler-Volmer kinetic parameters from MLIP-MD without running thermodynamic integration.[^103][^104]

**Tools**: pymbar (MIT) implements the multi-state Bennett acceptance ratio (MBAR) and Jarzynski estimators; OpenMM 8 (MIT) has native free energy calculation support with MLIP backends.[^105]

### 7.6 Biological Degradation Dynamics ↔ Electrochemical Ageing — PINN Transfer Learning

Biological tissue degradation models (bone remodelling, arterial wall fatigue, cellular senescence) share mathematical structure with electrochemical device ageing. Both are: (1) multi-mechanism processes with competing degradation pathways, (2) stochastic in nature (local defect nucleation), (3) coupled to mechanical stress fields, and (4) accelerated by environmental extremes (temperature, pH, cycling rate). The PINN degradation models developed in biomechanics (growth-remodelling PINNs) are directly transferable to battery electrode cracking and fuel cell catalyst coarsening — same PDEs, different material parameters.

**No existing tool exploits this transfer**. The most direct path is: use PyBaMM degradation models (SEI growth, lithium plating, LAM) as the physics prior; train a PINN surrogate in the style of NREL's battery PINN; validate against CALCE or Oxford battery degradation datasets. The PINN architecture is identical to biological growth models — only the physics equations differ.[^90]

***

## Section 8: Commercial Value Map

### 8.1 Battery Simulation
**Market size**: Battery simulation software valued at USD 2.22 billion in 2025, projected to reach USD 4.19 billion by 2030 (13.6% CAGR). US sub-market at USD 0.42 billion in 2025, growing to USD 1.37 billion by 2035.[^106][^107][^108]

**Primary buyers**: Automotive OEMs (BMW, Tesla, GM), battery manufacturers (CATL, Samsung SDI, Panasonic), national energy laboratories (NREL, Argonne), battery startups (Northvolt, QuantumScape, SES AI).

**Incumbents and moats**: COMSOL Multiphysics (proprietary, ~USD 10,000/node/year) dominates device-scale battery modelling; Battery Design Studio (Thermo-Fisher, Class D); MATLAB-based P2D implementations are common but closed. The incumbent moat is validated parameter libraries — not simulation capability.

**Open-source gap**: PyBaMM (BSD) and PyBOP (BSD) are production-ready and match COMSOL for 1D models; the gap is 3D coupled electrochemical-thermal simulations (where COMSOL + BDS excel). For an orchestration-first pipeline, the 1D PyBaMM chain is sufficient for materials screening; 3D validation can be outsourced.

**Commercialisation path for Zer0pa**: Materials-to-cell-performance predictions — given a new cathode material (structure from MatterGen/DiffCSP), predict cycle life, rate capability, and thermal runaway temperature using the PyBaMM pipeline. Buyers are battery manufacturers who want rapid in silico pre-screening before physical cell testing. **Shortest path to revenue** of any sub-domain.

### 8.2 Green Hydrogen / Electrolysis Simulation
**Market size**: Green hydrogen market valued at USD 2.79 billion in 2025, projected to reach USD 247 billion by 2035 (56.7% CAGR). Hydrogen electrolyser simulation tools entering critical growth phase. The gap between where green hydrogen needs to be (USD 2/kg) and where it is (USD 4–6/kg) makes computational optimisation commercially urgent.[^109][^110][^111]

**Primary buyers**: Electrolyser manufacturers (Nel, ITM Power, Plug Power, Thyssenkrupp), green hydrogen project developers, catalyst developers (Johnson Matthey, Umicore), governments with hydrogen strategies.

**Incumbents**: COMSOL Electrochemistry Module (Class D); Aspen Plus with electrolyser modules; gProms (Class D). No open-source tool matches their integrated process design capability.

**Open-source stack assessment**: The open stack (openFuelCell2 + Cantera + AlphaPEM + fairchem eSEN-M + PyPSA) covers DFT → device → system. The gap is stack-to-system scaling and balance-of-plant integration, which requires process engineering tools (DWSIM, open-source, Class B) not covered in this brief.

**Commercialisation path**: Catalyst screening service — given a target (IrO₂ replacement for PEM OER), use eSEN-M + OC25 data to screen earth-abundant alternatives, rank by computed overpotential, validate top candidates with PyBaMM-style device model. Buyers are electrolyser manufacturers and catalyst companies. The USD 2/kg hydrogen cost target creates a specific, quantifiable commercial need.

### 8.3 Solar Photovoltaics Simulation
**Market size**: Solar PV design software market at USD 1.88 billion in 2025, growing at 6.1% CAGR to USD 2.81 billion by 2034. The larger opportunity is materials R&D acceleration for perovskite tandems.[^112]

**Primary buyers**: PV manufacturers (First Solar, LONGi, JinkoSolar), perovskite developers (Oxford PV, Saule Technologies), national labs (NREL, Fraunhofer ISE), utility developers.

**Incumbents**: Sentaurus TCAD (Synopsys, Class D — ~USD 50,000/year); PC1D; SCAPS-1D (academic free, Class C). PVsyst, HelioScope, Aurora Solar for system design. No open alternative matches Sentaurus for device physics; Solcore (BSD) is the closest open tool.

**Open-source gap**: 2D/3D device simulation (Sentaurus) has no open-source equivalent of comparable performance. The gap for Zer0pa is between materials (Solcore optical + Shockley-Queisser limit) and device validation (requires TCAD or experiment). For perovskite tandems, Solcore + GPAW TDDFT covers the critical design questions.

**Commercialisation path**: Perovskite absorber layer design — given a target (1.7eV bandgap, <1% non-radiative recombination), screen halide perovskite compositions using GPAW GW band gap + DFT defect level calculations + Solcore device simulation. Output is a ranked list of synthesisable compositions with predicted efficiency. Primary buyers are perovskite PV startups and national labs.

### 8.4 Multi-Physics Surrogate AI — The Horizontal Market
**Market size**: Multi-physics simulation surrogate AI market at USD 1.42 billion in 2024, projected to grow to USD 10.45 billion by 2033 (24.8% CAGR).[^113]

**The horizontal opportunity**: Rather than building domain-specific simulation tools, Zer0pa's orchestration-first model positions it to build surrogate AI services that run on top of the open-source stack. A surrogate model trained on PyBaMM P2D simulations can predict battery performance 1,000x faster than the full model; a surrogate trained on openFuelCell2 CFD can replace 3D CFD with neural operators at similar speedup.[^90]

**Buyer profile**: Any OEM or developer running iterative design loops who cannot afford COMSOL simulation costs at scale. A Zer0pa pipeline that accepts a cell geometry + material parameters and returns a polarisation curve + degradation trajectory in under 1 second — versus hours for commercial tools — is directly monetisable as a service.

***

## Section 9: Pipeline Assembly Recommendation

### 9.1 The M2S Minimum Viable Pipeline

The following is the minimum viable Materials-to-Systems pipeline, fully open-source, commercially deployable, covering all major electrochemical sub-domains:

```
INPUT: [Atomic structure: CIF/xyz/SMILES] + [Device specification]
              ↓ LAYER 1 — Electronic Structure
    [GPAW (GPL) for optical + topological properties]
    [PySCF (Apache) for Marcus/CDFT charge transfer parameters]
    [Wannier90 + Z2Pack (GPL) for topological screening]
              ↓ Output token: ΔG_ads, λ, ε(ω), band gap, topological invariant
              ↓ LAYER 2 — Atomistic / MLIP
    [MACE-OMol25 (MIT) for molecular/electrolyte systems]
    [MACE-MPA-0 (MIT) for electrode materials]
    [LAMMPS (GPL) as MD engine]
              ↓ Output token: D_ion, σ_ionic, transport coefficients → HDF5
              ↓ LAYER 3 — Mesoscale
    [PF-PINO (2026) for dendrite / degradation / corrosion phase field]
    [OpenLB (GPL) for porous electrode ion transport]
    [MOOSE/RACCOON (LGPL) for coupled electrochemical-mechanical]
              ↓ Output token: τ (tortuosity), D_eff, microstructure maps → VTK
              ↓ LAYER 4 — Device Scale
    [PyBaMM v25 (BSD) — batteries (P2D, SPM, thermal, degradation)]
    [AlphaPEM (MIT) — PEM fuel cells and electrolysers]
    [Cantera 3.2 (BSD) — SOFC/SOEC elementary kinetics]
    [Solcore (BSD) — photovoltaic multi-junction cells]
              ↓ Output token: Polarisation curve V(j) + EIS + J-V curve
              ↓ LAYER 5 — Stack / System
    [NREL PINN surrogate (NREL open) — ~1000x faster degradation prediction]
    [pvlib-python (BSD) — PV system yield]
    [PyPSA (MIT) — energy system dispatch + LCOE/LCOH]
    [SAM pySAM (BSD) — techno-economic]
              ↓ Output token: LCOE ($/kWh), LCOH ($/kg), reliability distribution
              ↓ LAYER 6 — Orchestration
    [AiiDA 2.8 (MIT) + Atomate2 (Apache) — provenance + workflow]
    [BoTorch + Ax (MIT) — Bayesian optimisation]
    [fairchem (Apache) — electrocatalyst screening API]
    [PyBOP (BSD) — battery parameter estimation]
    ↑______________ Active Learning Loop ______________________________|
```

### 9.2 Layer Interface Specifications

| Handoff | From → To | Data Token | Format | Tool |
|---------|----------|-----------|--------|------|
| L1 → L2 | DFT adsorption energies → MLIP training | extxyz (energy/forces/stresses) | extxyz | GPAW → MACE training |
| L1 → L4 | Marcus parameters → Butler-Volmer | Exchange current j₀, transfer coeff α | JSON/Python dict | PySCF CDFT → PyBaMM |
| L2 → L3 | Transport coefficients → LB input | D_ion, σ_ionic, τ_structural | JSON/HDF5 | LAMMPS → OpenLB |
| L2 → L4 | Transport properties → P2D inputs | Diffusivity, conductivity tensors | JSON | MACE-MD → PyBaMM params |
| L3 → L4 | Effective medium params → cell model | τ, D_eff, ε_electrode | JSON | OpenLB → PyBaMM geometry |
| L4 → L5 | Device performance → system model | V-j curve, degradation rate | CSV/JSON | PyBaMM → PyPSA |
| L5 → L6 | LCOE/LCOH distribution → BoTorch | Scalar objective + uncertainty | Torch tensor | PyPSA → BoTorch acquisition |
| L6 → L1 | Next candidate structure | CIF + composition constraints | CIF | BoTorch → MatterGen → GPAW |

### 9.3 Open vs. Commercial Gaps

**Device scale (Layer 4 for PV)**: No open tool matches Sentaurus TCAD (Synopsys, Class D) for 2D/3D solar cell device physics. Solcore (BSD) covers the design-relevant calculations (J-V curves, quantum efficiency); full 2D device simulation requires commercial TCAD or FEniCSx with custom electrochemistry modules (feasible but requires development investment).

**Catalyst kinetics databases (Layer 1→3)**: AQCat25 (Class C) is the most complete catalyst dataset but non-commercial. Use OC25 (CC-BY-4.0) + eSEN-M for commercial electrocatalysis screening; sacrifice spin-polarisation accuracy for magnetic transition metals.

**Polymer electrolyte MLIP**: BAMBOO (ByteDance, Class E) is the best demonstrated liquid electrolyte MLIP but is not open. MACE-OMol25 (MIT) trained on OMol25 electrolyte subsets is the open alternative; PEMD (2026, license pending) provides the highest-level workflow wrapper.

**Stack/module scale for fuel cells**: No open equivalent of AspenPlus or gPROMS for integrated process design of electrolysis plants. Cantera + PyPSA covers thermochemistry and system dispatch; the gap is detailed piping/heat integration design (balance of plant).

***

## Section 10: Open Questions

**1. Direct scale coupling is still largely manual**: Despite the tool stack described above, no open framework automatically passes transport coefficients from LAMMPS trajectories to PyBaMM input parameters, or passes pore-scale LB results to 1D PyBaMM cell geometries. Each layer transition requires domain expertise to set up correctly. This is the most critical engineering gap to close.

**2. Degradation simulation remains semi-empirical at scale**: PyBaMM implements SEI growth, lithium plating, and active material loss models, but the kinetic rate parameters for these models are typically fitted to experimental data, not computed from L1 DFT. The path from first-principles degradation mechanisms (computed in CP2K or GPAW) to PyBaMM degradation parameters is not yet automated.

**3. No open electrochemical device data standard**: OPTIMADE provides a universal API for crystal structure databases; no equivalent standard exists for electrochemical device performance data (EIS spectra, cycling curves, degradation trajectories). The closest analogues are CALCE and Oxford Battery datasets (academic, non-standardised formats). An OPTIMADE-equivalent for electrochemical data would transform the ML training data landscape.

**4. Quantum computing for molecular simulation — not yet accessible**: Near-term quantum devices (IBM, IonQ, Google) have demonstrated VQE algorithms for small molecules but cannot simulate systems relevant to electrode materials at practical accuracy. The fault-tolerant threshold for useful quantum chemistry calculations (10 million+ physical qubits) is still 10–15 years away. Include as a monitoring target, not a pipeline component.

**5. The LLM reasoning gap for electrochemistry**: No open model approaches GPT-4-class reasoning on electrochemistry questions (equivalent to MatSciBench gap). A fine-tuned open-weight LLM on OC20/OC25 data, PyBaMM documentation, NREL reports, and electrochemistry literature would have significant value as the reasoning layer of the orchestration pipeline.

---

## References

1. [Understanding Electron Transfer Reactions Using Constrained ...](https://pubs.acs.org/doi/10.1021/acs.jpcc.2c06537) - We use the Marcus theory to predict electron transfer rates and the combined CDFT-AIMD approach to c...

2. [Methodological Frameworks for Computational Electrocatalysis - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12972284/) - To capture the influence of solvation and the electrochemical environment, DFT can be combined with ...

3. [Shockley–Queisser limit - Wikipedia](https://en.wikipedia.org/wiki/Shockley%E2%80%93Queisser_limit) - The Shockley–Queisser limit only applies to conventional solar cells with a single p-n junction; sol...

4. [[PDF] Implementing the Shockley-Queisser efficiency limit in SCAPS](https://scaps.elis.ugent.be/SCAPS%20Application%20Note%20Shockley-Queisser%20limit.pdf) - Here, the culprit clearly is the low recombination: for the red curves in 1, there is as good as no ...

5. [Frequency-Domain Analysis of an FEM-Based Rotor–Nacelle Model for Wind Turbines: Results Comparison with OpenFAST](https://www.mdpi.com/1996-1073/19/1/169) - This study presents a frequency-domain analysis of a finite-element (FEM)-based rotor–nacelle model ...

6. [Full-System Linearization for Floating Offshore Wind Turbines in OpenFAST: Preprint](http://www.osti.gov/servlets/purl/1489323/) - The wind engineering community relies on multiphysics engineering software to run nonlinear time-dom...

7. [OpenFAST | Wind Research | NLR](https://www.nlr.gov/wind/nwtc/openfast) - OpenFAST. OpenFAST is an open-source wind turbine simulation tool that was established with the FAST...

8. [What is OpenFAST? Competitors, Complementary Techs & Usage](https://sumble.com/tech/openfast) - OpenFAST is a free, open-source wind turbine simulation tool developed by the National Renewable Ene...

9. [Main repository for the NREL-supported OpenFAST whole ... - GitHub](https://github.com/OpenFAST/openfast) - OpenFAST is a wind turbine simulation tool which builds on FAST v8. FAST.Farm extends the capability...

10. [GPAW: An open Python package for electronic-structure calculations](https://arxiv.org/pdf/2310.14776.pdf) - ...This multi-basis feature renders GPAW highly versatile and unique among
similar codes. By virtue ...

11. [Multiscale simulation for electrolyte design: From microstructure ...](https://www.sciencedirect.com/science/article/abs/pii/S2405829726000607) - Multiscale simulation bridges electrolyte microstructure to macroscopic performance. · Combined DFT ...

12. [A predictive machine learning force field framework for liquid
  electrolyte development](https://arxiv.org/html/2404.07181) - ...applying MLFF to
simulate liquid electrolyte, a critical component of the current commercial
lith...

13. [Lattice Boltzmann simulation of ion transport during the charging ...](https://www.sciencedirect.com/science/article/abs/pii/S0735193324007048) - In this paper, the microscopic ion transport mechanism in NiHCF electrodes of desalination batteries...

14. [Physics-informed neural operator for predictive parametric phase ...](https://arxiv.org/html/2603.09693v1) - While neural operators such as the Fourier neural operator (FNO) show promise in accelerating the so...

15. [Physics-informed neural operator for predictive parametric phase ...](https://arxiv.org/abs/2603.09693) - Our results demonstrate that PF-PINO significantly outperforms conventional FNO in accuracy, general...

16. [AlphaPEM: an open-source dynamic 1D physics-based PEM fuel cell model
  for embedded applications](http://arxiv.org/pdf/2407.12373.pdf) - The urgency of the energy transition requires improving the performance and
longevity of hydrogen te...

17. [PyBaMM - Homepage](https://pybamm.org) - PyBaMM enables efficient simulations of battery performance and aging, accelerating battery design a...

18. [Solcore: A multi-scale, python-based library for modelling solar cells
  and semiconductor materials](https://arxiv.org/pdf/1709.06741.pdf) - ...cells. Calculations can be performed on ideal,
thermodynamic limiting behaviour, through to fitti...

19. [PyPSA-Earth sector-coupled: A global open-source multi-energy ...](https://ideas.repec.org/a/eee/appene/v383y2025ics0306261925000467.html) - This study presents sector-coupled PyPSA-Earth: a novel global open-source energy system optimizatio...

20. [PyPSA - Python for Power System Analysis](https://pypsa.org) - PyPSA is an open-source Python framework for optimizing modern power systems with renewable energy, ...

21. [Welcome - System Advisor Model - SAM](https://sam.nlr.gov) - The System Advisor Model (SAM) is a performance and financial model designed to estimate the cost of...

22. [AI agents for solid electrolytes: opportunities, challenges, and future ...](https://www.oaepublish.com/articles/aiagent.2025.10) - Artificial intelligence (AI) and autonomous agents are transforming the discovery and optimization o...

23. [GPAW: An open Python package for electronic structure calculations](https://pubs.aip.org/aip/jcp/article/160/9/092503/3269902/GPAW-An-open-Python-package-for-electronic) - We review the GPAW open-source Python package for electronic structure calculations. GPAW is based o...

24. [Calculation of optical spectra with TDDFT - GPAW](https://gpaw.readthedocs.io/tutorialsexercises/opticalresponse/lrtddft/lrtddft.html) - In this exercise we calculate optical spectrum of Na2 molecule using linear response time-dependent ...

25. [New real-time TDDFT implementation — GPAW - Read the Docs](https://gpaw.readthedocs.io/tutorialsexercises/opticalresponse/tddft/rttddft.html) - New real-time TDDFT implementation . There is an ongoing effort in refactoring the real-time TDDFT c...

26. [Computing Solvation Shell Dynamics and Energetics in Electron ...](https://arxiv.org/html/2510.22435v1) - Marcus theory is fundamental to describing electron transfer reactions and quantifying their rates, ...

27. [An open-source software package for novel topological materials](https://www.sciencedirect.com/science/article/abs/pii/S0010465517303442) - We present an open-source software package WannierTools, a tool for investigation of novel topologic...

28. [Overview — Z2Pack 2.2.1 documentation](https://z2pack.greschd.ch) - A tool for calculating topological invariants. The method is based on tracking the evolution of hybr...

29. [Z2PackDev/Z2Pack: A tool for calculating topological invariants.](https://github.com/Z2PackDev/Z2Pack) - Z2Pack automates the calculation of topological numbers of band-structures. It works with first-prin...

30. [VASP - Vienna Ab initio Simulation Package](https://www.vasp.at) - 6.6.0 ... A new version of VASP is available now! Have a look at the list of new features and improv...

31. [Reliable and Efficient Automated Transition-State Searches with Machine-Learned Interatomic Potentials](https://www.semanticscholar.org/paper/b7ba814d9702eff10f1a7be86208c40d063a09c7) - Transition-state searches are central to understanding reaction mechanisms, but the high computation...

32. [Exploring Meta's Open Molecules 2025 (OMol25) & Universal ...](https://www.rowansci.com/blog/exploring-open-molecules-2025) - Meta's Fundamental AI Research (FAIR) team released Open Molecules 2025 (OMol25), a massive dataset ...

33. [The Open Molecules 2025 (OMol25) Dataset, Evaluations, and Models](https://arxiv.org/abs/2505.08762) - Meta FAIR introduces Open Molecules 2025 (OMol25), a large-scale dataset composed of more than 100 m...

34. [[PDF] The Open Molecules 2025 (OMol25) Dataset, Evaluations, and Models](https://www.rivista.ai/wp-content/uploads/2025/06/2505.08762v1.pdf) - OMol25 uniquely blends elemental, chemical, and structural diversity including: 83 elements, a wide-...

35. [Open Catalyst 2025 (OC25) Dataset - Emergent Mind](https://www.emergentmind.com/topics/open-catalyst-2025-oc25-dataset) - The Open Catalyst 2025 (OC25) dataset is a large-scale, open-access resource designed to accelerate ...

36. [[PDF] The Open Catalyst 2025 (OC25) Dataset and Models for Solid ...](https://arxiv.org/pdf/2509.17862.pdf) - State-of-the-art models trained on the OC25 dataset exhibit energy, force, and solvation energy erro...

37. [The Open Catalyst 2025 (OC25) Dataset and Models for Solid ...](https://huggingface.co/papers/2509.17862) - State-of-the-art models trained on the OC25 dataset exhibit energy, force, and solvation energy erro...

38. [PEMD: a high-throughput simulation and analysis framework for ...](https://pubs.rsc.org/en/content/articlehtml/2026/dd/d5dd00454c) - We developed PEMD, an open-source Python framework that unifies polymer construction, OPLS-AA force ...

39. [PEMD: a high-throughput simulation and analysis framework for ...](https://scholars.cityu.edu.hk/en/publications/pemd-a-high-throughput-simulation-and-analysis-framework-for-soli/) - We introduce polymer electrolyte modeling and discovery (PEMD), an open-source Python framework that...

40. [PEMD: a high-throughput simulation and analysis framework for ...](https://pubs.rsc.org/en/content/articlelanding/2026/dd/d5dd00454c) - We introduce polymer electrolyte modeling and discovery (PEMD), an open-source Python framework that...

41. [Ion Transport in Polymer Electrolytes: Building New Bridges ...](https://pubs.acs.org/doi/abs/10.1021/acs.accounts.3c00791) - PEMD: a high-throughput simulation and analysis framework for solid polymer electrolytes. Digital Di...

42. [PiNN: Equivariant Neural Network Suite for Modeling Electrochemical Systems](https://pmc.ncbi.nlm.nih.gov/articles/PMC11823406/) - ...Electrochemical energy storage and conversion play increasingly important roles in electrificatio...

43. [Problem Set-Up — Phase Field Method Recommended Practices](https://pages.nist.gov/pf-recommended-practices/bp-guide-gh/ch5-problem-setup.html) - The purpose of this page is to give guidance on some of the important considerations when setting up...

44. [Lattice boltzmann simulation for electrolyte transport in porous ...](https://snu.elsevierpure.com/en/publications/lattice-boltzmann-simulation-for-electrolyte-transport-in-porous-) - The LB model successfully simulates the complicated microscopic behavior of a liquid electrolyte in ...

45. [Battery Models — PyBaMM v25.8.0 Manual](https://docs.pybamm.org/en/v25.8.0/source/user_guide/fundamentals/battery_models.html) - Battery Models# ... However, a few papers are provided in this section for anyone interested in read...

46. [Modelling coupled degradation mechanisms in PyBaMM](https://docs.pybamm.org/en/v25.8.0/source/examples/notebooks/models/coupled-degradation.html) - This notebook shows how to set up a PyBaMM model in which many degradation mechanisms run at the sam...

47. [Thermal models — PyBaMM v25.10.2 Manual](https://docs.pybamm.org/en/v25.10.2/source/examples/notebooks/models/thermal-models.html) - Thermal models#. There are a number of thermal submodels available in PyBaMM. In this notebook we gi...

48. [Parameters Sets — PyBaMM v25.4.0 Manual](https://docs.pybamm.org/en/v25.4.0/source/api/parameters/parameter_sets.html) - Lithium-ion battery degradation: how to model it. Phys. Chem. Chem ... A simplified electrochemical ...

49. [Base Battery Model — PyBaMM v25.8.0 Manual](https://docs.pybamm.org/en/v25.8.0/source/api/models/base_models/base_battery_model.html) - Whether to calculate the heat source terms during isothermal operation. Can be “true” or “false”. If...

50. [Performance benchmarks for open source porous electrode theory ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC11004710/) - Three open source PET models: dualfoil, MPET, and LIONSIMBA were compared to simulate the discharge ...

51. [pybop · PyPI](https://pypi.org/project/pybop/) - PyBOP provides tools for the parameterisation and optimisation of battery models, using both Bayesia...

52. [PyBOP: Optimise and Parameterise Battery Models — PyBOP ...](https://pybop-docs.readthedocs.io) - A Python package dedicated to the optimisation and parameterisation of battery models. PyBOP is desi...

53. [pybop-team/PyBOP: A parameterisation and optimisation ... - GitHub](https://github.com/pybop-team/PyBOP) - PyBOP provides tools for the parameterisation and optimisation of battery models, using both Bayesia...

54. [A Python package for battery model optimisation and parameterisation](https://ui.adsabs.harvard.edu/abs/2025JOSS...10.7874P/abstract) - The Python Battery Optimisation and Parameterisation (PyBOP) package provides methods for estimating...

55. [openFuelCell2 is a computational fluid dynamics (CFD ... - GitHub](https://github.com/openFuelCell2/openFuelCell2) - openFuelCell2 is a computational fluid dynamics (CFD) toolbox for simulating electrochemical devices...

56. [Open-source Computational Model for Polymer Electrolyte Fuel Cells](https://journal.openfoam.com/index.php/ofj/article/view/50) - We present a three-dimensional, steady-state, non-isothermal proton exchange membrane fuel cell mode...

57. [openFuelCell2 · A computational fluid dynamics (CFD) solver for ...](https://openfuelcell2.github.io) - openFuelCell2 is a computational fluid dynamics (CFD) toolbox for simulating electrochemical devices...

58. [Solid oxide fuel cell using elementary kinetics - Cantera](https://cantera.org/3.2/examples/python/kinetics/sofc.html) - A simple model of a solid oxide fuel cell. Unlike most SOFC models, this model does not use semi-emp...

59. [Open-source chemical kinetics, thermodynamics, and transport ...](https://cantera.org) - Cantera is an open-source suite of tools for problems involving chemical kinetics, thermodynamics, a...

60. [Technical evaluation and life-cycle assessment of solid oxide co ...](https://www.sciencedirect.com/science/article/pii/S135943112402550X) - Python coupled with Cantera is used for the thermodynamic equilibrium calculations. The algorithms u...

61. [solcore - PyPI](https://pypi.org/project/solcore/) - A complete semiconductor solver able of modelling the optical and electrical properties of a wide ra...

62. [www.solcore.solar](https://www.solcore.solar) - A multi-scale, Python-based library for modelling solar cells and semiconductor materials ... : It i...

63. [Solcore: a multi-scale, Python-based library for modelling solar cells ...](https://www.semanticscholar.org/paper/Solcore:-a-multi-scale,-Python-based-library-for-Alonso%E2%80%90%C3%81lvarez-Wilson/7427cf2c1d7c0409174b8e5ec6aac3eda72b44ce) - The model is a multi-scale simulation accounting for nanoscale phenomena such as the quantum confine...

64. [Solcore simulation of a GaInP/InGaAs/Ge solar cell](https://www.spiedigitallibrary.org/conference-proceedings-of-spie/13187/3021753/Solcore-simulation-of-a-GaInPInGaAsGe-solar-cell/10.1117/12.3021753.full) - Recently, multi-junction (MJ) solar cells have been researched extensively, due to their potential o...

65. [Gpvdm - A general-purpose solar cell simulation tool](https://www.gpvdm.com) - Use the power of device simulation to understand your experimental data from thin film devices such ...

66. [SCAPS-1D simulation of lead-free perovskite solar cells](https://pubs.rsc.org/en/content/articlelanding/2026/ra/d5ra08437g) - This work presents a theoretical evaluation of an n-i-p configured solar cell (FTO/SnO2/Cs2PtI6/Spir...

67. [scaps](https://scaps.elis.ugent.be) - SCAPS (a Solar Cell Capacitance Simulator) is a one dimensional solar cell simulation programme deve...

68. [Applications of machine learning in surfaces and interfaces](https://pubs.aip.org/aip/cpr/article/6/1/011309/3339760/Applications-of-machine-learning-in-surfaces-and) - also used solar cell capacitance simulator-one-dimensional (SCAPS-1D) software to generate a dataset...

69. [Synthetic dataset to study the performance of perovskite solar cell ...](https://f1000research.com/articles/14-961) - This paper presents a synthetic dataset to study the performance of perovskite solar cells (PSC) sim...

70. [PyPSA: Python for Power System Analysis](https://arxiv.org/pdf/1707.09913.pdf) - ...of PyPSA is described,
including the formulation of the full power flow equations and the multi-p...

71. [PyPSA-Earth sector-coupled: A global open-source multi-energy ...](https://www.sciencedirect.com/science/article/pii/S0306261925000467) - PyPSA-Earth sector-coupled: A global open-source multi-energy system model showcased for hydrogen ap...

72. [PyPSA: Python for Power System Analysis - GitHub](https://github.com/pypsa/pypsa) - PyPSA is an open-source Python framework for optimising and simulating modern power and energy syste...

73. [pvlib python: a python package for modeling solar energy systems](https://www.osti.gov/biblio/1993714) - pvlib python is a community-supported open source tool that provides a set of functions and classes ...

74. [pvlib python — pvlib python 0.15.1 documentation](https://pvlib-python.readthedocs.io) - pvlib python is a community developed toolbox that provides a set of functions and classes for simul...

75. [GitHub - pvlib/pvlib-python: A set of documented functions for ...](https://github.com/pvlib/pvlib-python) - pvlib python is a community developed toolbox that provides a set of functions and classes for simul...

76. [SOLAR ENERGY SIMULATION WITH PVLIB-PYTHON - Zenodo](https://zenodo.org/records/19586042) - This project uses PV Lib-Python, a sophisticated open-source framework for modeling and analyzing so...

77. [Microgrid Architecture for AI Computing Facilities](https://ieeexplore.ieee.org/document/11405439/) - Hybrid microgrid architectures integrating solar photovoltaic (PV), wind turbines, and battery energ...

78. [Demonstrating SolarPILOT’s Python API Through Heliostat Optimal Aimpoint Strategy Use Case](https://asmedigitalcollection.asme.org/ES/proceedings/ES2021/84881/V001T02A001/1114865) - SolarPILOT is a software package that generates solar field layouts and characterizes the optical pe...

79. [System Advisor Model (SAM) | Open Energy Information](https://openei.org/wiki/System_Advisor_Model_(SAM)) - The System Advisor Model (SAM) is a performance and financial model designed to facilitate decision ...

80. [NatLabRockies/SAM: System Advisor Model (SAM) - GitHub](https://github.com/NREL/SAM) - SAM is a simulation program for electricity generation projects. It has models for different kinds o...

81. [SAM Downloads - System Advisor Model](https://sam.nlr.gov/download.html) - The System Advisor Model (SAM) is a performance and financial model designed to estimate the cost of...

82. [Integration of Concentrating Solar Power With High Temperature Electrolysis for Hydrogen Production](https://www.tib-op.org/ojs/index.php/solarpaces/article/view/973) - Hydrogen has been identified as a leading sustainable contender to replace fossil fuels for transpor...

83. [Techno-Economic Analysis for Co-located Solar and Hydrogen Plants](https://ieeexplore.ieee.org/document/10161786/) - Power-to-X technologies with flexible electricity consumption has the potential improve the utilizat...

84. [Chemical foundation model-guided design of high ionic conductivity ...](https://www.nature.com/articles/s41524-025-01774-4) - The fine-tuned model is used to discover 7 novel high conductivity electrolyte formulations through ...

85. [SandboxAQ/aqcat25-dataset - Hugging Face](https://huggingface.co/datasets/SandboxAQ/aqcat25-dataset) - The AQCat25 dataset provides a large and diverse collection of 13.5 million DFT calculation trajecto...

86. [The Open Catalyst 2022 (OC22) Dataset and Challenges for Oxide
  Electrocatalysts](http://arxiv.org/pdf/2206.08917.pdf) - ...point calculations) across a range of oxide materials,
coverages, and adsorbates. We define gener...

87. [Open Catalyst Experiments 2024 (OCx24): Bridging Experiments and
  Computational Models](https://arxiv.org/html/2411.11783v1) - ...candidate for HER without having any experimental measurements on
Pt or Pt-alloy samples. We anti...

88. [The JARVIS Infrastructure is All You Need for Materials Design - arXiv](https://arxiv.org/html/2503.04133v2) - JARVIS is a unified platform for multiscale, multimodal, forward, and inverse materials design. It i...

89. [[PDF] The JARVIS Infrastructure is All You Need for Materials Design](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=959617) - This schematic highlights key elements of JARVIS, including databases for structural, electronic, me...

90. [Physics-informed neural network significantly boosts battery ...](https://techxplore.com/news/2025-06-physics-neural-network-significantly-boosts.html) - NREL's PINN replaces the traditional, resource-intensive battery physics model with a powerful artif...

91. [Open Materials 2024 (OMat24) Inorganic Materials Dataset and Models](https://arxiv.org/html/2410.12771) - ...space
compared to other computational methods or by trial-and-error. While
substantial progress h...

92. [A corpus of CO2 electrocatalytic reduction process extracted from the scientific literature](https://pmc.ncbi.nlm.nih.gov/articles/PMC10060421/) - ...and chemicals production. Thereinto, the design of new electrocatalysts with high activity and se...

93. [SandboxAQ Launches Quantitative AI Model to Accelerate Catalysis ...](https://www.prnewswire.com/news-releases/sandboxaq-launches-quantitative-ai-model-to-accelerate-catalysis-breakthroughs-302595943.html) - Trained on the AQCat25 dataset with 13.5 million high-fidelity quantum chemistry calculations across...

94. [AQCat25: Unlocking spin-aware, high-fidelity machine learning ...](https://arxiv.org/abs/2510.22938) - To extend these capabilities, we introduce AQCat25, a complementary dataset of 13.5 million density ...

95. [Physics-informed neural network for long-term prognostics of proton ...](https://ideas.repec.org/a/eee/appene/v382y2025ics0306261925000480.html) - This study formulated a physics-informed neural network (PINN) to prognosticate the remaining useful...

96. [Physics-Informed Neural Networks for Real-Time Gas Crossover ...](https://arxiv.org/html/2511.05879v2) - Energy AI 2025. RUL Prediction, PEM Fuel Cell, Membrane/catalyst degradation physics, 9.2% improveme...

97. [The Open Catalyst 2025 (OC25) Dataset and Models for Solid-Liquid...](https://openreview.net/forum?id=4DRmiJJk9w) - TL;DR: In this work, we introduce the Open Catalyst 2025 (OC25) dataset and models for solid-liquid ...

98. [Computational Chemistry Unlocked: A Record-Breaking Dataset to ...](https://newscenter.lbl.gov/2025/05/14/computational-chemistry-unlocked-a-record-breaking-dataset-to-train-ai-models-has-launched/) - Open Molecules 2025, or OMol25, is a collection of more than 100 million 3D molecular snapshots whos...

99. [New computational insights using Marcus theory to unlock the ... - ICIQ](https://iciq.org/new/new-computational-insights-using-marcus-theory-to-unlock-the-potential-of-photocatalysis/) - The Marcus theory was originally developed to provide a fundamental understanding of single-electron...

100. [[PDF] Z-ACA allotrope: a topological carbon material with obstructed ...](https://public-pages-files-2025.frontiersin.org/journals/physics/articles/10.3389/fphy.2024.1437146/pdf) - Later, the Wannier function [55–58] was used to calculate the band structure of the nanotube. The ba...

101. [[PDF] Orbital Topology of Chiral Crystals for Orbitronics](https://web.phys.ntu.edu.tw/nanomagnetism/eng/pdf/135-Advanced%20Materials%2037-2418040-2025-Orbital%20Topology%20of%20Chiral%20Crystals%20for%20Orbitronics.pdf) - In this work, we have shown the crucial role of the OAM as the key link intertwining crystal chirali...

102. [Subcellular systems follow Onsager reciprocity - Nature](https://www.nature.com/articles/s44385-025-00015-z) - The objective of this study is to test if Onsager reciprocity, a coupling between thermodynamic flow...

103. [Nonequilibrium Thermodynamics of Precision through a Quantum ...](https://link.aps.org/doi/10.1103/nrzn-h5ph) - Thermodynamic uncertainty relations (TURs) are a set of inequalities expressing a fundamental trade-...

104. [Consistency of Equilibrium and Nonequilibrium Molecular Dynamics ...](https://pubs.acs.org/doi/10.1021/acs.jced.5c00628) - Accurate evaluation of thermal conductivity using molecular simulation can be challenging depending ...

105. [OpenMM 8: Molecular Dynamics Simulation with Machine Learning ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC10846090/) - The newest version of the OpenMM molecular dynamics toolkit introduces new features to support the u...

106. [Battery Simulation Software Market Size, Share & Growth Report 2035](https://www.snsinsider.com/reports/battery-simulation-software-market-8450) - The Battery Simulation Software Market Size was valued at USD 1.60 billion in 2025 and is expected t...

107. [Battery Simulation Software Market Projected to Grow at a CAGR of ...](https://finance.yahoo.com/news/battery-simulation-software-market-projected-103000644.html) - The U.S. Battery Simulation Software Market size was USD 0.37 billion in 2024 and is expected to rea...

108. [Battery Simulation Software Market Report 2025-2030, By ...](https://www.marketsandmarkets.com/Market-Reports/battery-simulation-software-market-94545804.html) - The global battery simulation software market size is projected to grow from USD 2.22 billion in 202...

109. [Advanced alkaline electrolyzer design for cost reduction](https://wjarr.com/node/11096) - The recent worldwide move towards decarbonization and integration of renewable energy has heightened...

110. [Green Hydrogen Market Size and Growth Analysis 2026 to 2035](https://www.insightaceanalytic.com/report/green-hydrogen-market/1541) - Green Hydrogen Market Size is valued at USD 2.79 Billion in 2025 and is predicted to reach USD 247.2...

111. [Hydrogen Electrolyzer Simulation Tools Market To 2035 - IndexBox](https://www.indexbox.io/blog/hydrogen-electrolyzer-simulation-tools-market-to-2035-driven-by-lender-requirements-for-validated-project-bankability/) - The global market for Hydrogen Electrolyzer Simulation Tools is entering a critical growth phase, fo...

112. [Solar Photovoltaic Design Software Market Outlook 2026-2034](https://www.intelmarketresearch.com/solar-photovoltaic-design-software-market-27712) - Global Solar Photovoltaic Design Software market valued at USD 1877M in 2025, projected to reach USD...

113. [Multi-Physics Simulation Surrogate AI Market Research Report 2033](https://growthmarketreports.com/report/multi-physics-simulation-surrogate-ai-market) - According to our latest research, the global Multi-Physics Simulation Surrogate AI market size in 20...

1002. [facebookresearch/fairchem: FAIR Chemistry's library of ... - GitHub](https://github.com/facebookresearch/fairchem) - UMA models and legacy inorganic bulk models trained using OMat24 are trained with DFT and DFT+U tota...

1186. [Principles of Inorganic Materials Design](https://cashmere.io/v/VlWyz3) - by John N. Lalena, David A. Cleary, Olivier B.M. Hardouin Duparc  a few hundreds of atoms during hun...

