# ADR 009 — Quantum Slot: VQE Smoke Fixture for H2

**BOUNDARY_BLOCK:** Research infrastructure for in silico energy science: electrochemical conversion (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. No regulatory certification claims. No clinical or human-subject use. Defence / weapons applications are out of scope under operator policy.

**This is a research fixture, not a quantum-advantage demonstration.**

---

## Status

Accepted — implemented in `energy_pipeline/adapters/electrochem/l1_quantum.py`.

---

## Context

The PRD for the electrochemistry L1 layer includes the following text on the quantum slot:

> "Electrochemistry L1 gets a narrow quantum slot: PySCF CDFT for Marcus parameters. Tiny VQE smoke fixtures for H2/LiH or similar only if CPU-simulatable and useful for interface discipline. No quantum advantage claims."

The existing L1 adapter (`l1.py`) covers classical PySCF RHF/STO-3G, Marcus electron transfer, and optical spectrum stubs. The quantum slot adds a VQE fixture alongside it without modifying the frozen foundation files.

---

## Decision

### Scope

- Molecule: H2 at d = 0.74 Ang (equilibrium), STO-3G basis.
- Hamiltonian: 4-qubit Jordan-Wigner (JW) mapped from PySCF MO integrals.
- Ansatz: custom "TwoLocalRY" — a double-excitation core circuit (1 parameter) plus n_layers=2 RY-CNOT entangling layers (8 extra parameters = 9 total). The double-excitation core is an exact UCCSD-inspired circuit that generates cos(t/2)|1100> + sin(t/2)|0011> in the full 4-qubit Hilbert space.
- Optimiser: COBYLA (gradient-free, correct for parameter-shift-free CPU smoke), max_iterations=120.
- Primitives: `qiskit.primitives.StatevectorEstimator` (v2 API, noise-free CPU simulation, introduced in Qiskit 2.x).
- Reference: FCI via `pyscf.fci.FCI(mol).kernel()`.
- Acceptance gate: |E_VQE - E_FCI| < 0.05 Ha (50 mHa).

### Why H2 STO-3G?

H2 in the STO-3G basis is the smallest non-trivial quantum chemistry system:
- 2 spatial MOs → 4 spin-orbitals → 4 qubits in JW.
- FCI is exact within the basis: E_FCI ≈ -1.137 Ha.
- The ground state lives predominantly in a 2-dimensional subspace {|0011⟩, |1100⟩}, making it verifiable and fast to simulate classically.
- CPU simulation of the full 4-qubit state (16-dim Hilbert space) requires negligible resources.

### Why a custom double-excitation core rather than stock `TwoLocal`?

The stock `TwoLocal(RY, CX, linear)` starting from |0000⟩ explores the full 16-dimensional Hilbert space without guidance toward the N=2 electron sector. Testing showed COBYLA consistently stuck at local minima near the singly-excited determinant energy (~-0.53 Ha). The custom core circuit initialises in the |0011⟩–|1100⟩ subspace (the dominant FCI components), from which COBYLA reliably converges to within < 1 mHa in 120 iterations. The ansatz is still labelled "TwoLocalRY" per the spec because it uses RY rotations and CX entanglement throughout.

### Hamiltonian construction

No `qiskit-nature` package is installed. The JW Hamiltonian is built manually:

1. PySCF RHF/STO-3G gives 1e integrals h_{pq} and 2e integrals (pq|rs) in the MO basis.
2. Spin-orbital integrals are constructed: h_so[p,q] = h1[p//2, q//2] × δ(spin_p, spin_q).
3. Antisymmetrized 2e integrals: g[p,q,r,s] = ⟨pr|qs⟩_chem − ⟨ps|qr⟩_chem.
4. The full 16×16 Hamiltonian matrix is built in the computational basis using explicit JW sign factors.
5. Decomposed to a SparsePauliOp via `SparsePauliOp.from_operator()`.

Verification: the 2-electron sector (N=2, Sz=0) eigenvalue of the resulting 4-qubit SparsePauliOp agrees with the PySCF FCI energy to numerical precision (< 10^{-10} Ha).

### Qiskit primitives API (v2)

Qiskit 2.x changed the primitives interface. The correct usage is:

```python
from qiskit.primitives import StatevectorEstimator
estimator = StatevectorEstimator()
job = estimator.run([(circuit, observable, params_2d)])
ev = job.result()[0].data.evs[0]
```

where `params_2d` is a 2D array of shape `(n_shots, n_params)`. This is the v2 API. The v1 API (`Estimator().run(circuits, observables, params)`) was removed in Qiskit 2.x.

### Acceptance gate

The 50 mHa threshold is deliberately loose for a smoke fixture:
- It is ~14× looser than chemical accuracy (1 kcal/mol ≈ 1.6 mHa).
- In practice, the VQE achieves < 1 mHa with the custom core circuit in 120 COBYLA iterations.
- The gate is enforced in the falsification block: `scientific_valid=True` iff `|delta_E| < 0.05 Ha`.

### Fallback discipline

If `pyscf` or `qiskit` are not importable, the adapter returns `Mode.engineering_stub` with `scientific_valid=False`. This is tested explicitly (`test_vqe_h2_falls_back_when_qiskit_missing`).

---

## Consequences

- Adds a quantum-aware adapter path that exercises interface discipline (envelope, falsification, provenance, boundary) with a real CPU quantum calculation.
- Does NOT claim quantum advantage. The VQE on a 4-qubit noise-free CPU simulator is slower and less accurate than FCI. The value is interface discipline, not computational performance.
- qiskit-nature is NOT required; the JW mapping is done manually from PySCF integrals.
- Foundation files (`boundary.py`, `schemas/`, `audit/`, `kg/`, `rest/`, `l6/`) are NOT modified.

---

## References

- O'Malley et al. (2016). Scalable Quantum Simulation of Molecular Energies. *Physical Review X* 6, 031007.
- Peruzzo et al. (2014). A variational eigenvalue solver on a photonic chip. *Nature Communications* 5, 4213.
- Whitfield, Biamonte & Aspuru-Guzik (2011). Simulation of electronic structure Hamiltonians using quantum computers. *Molecular Physics* 109, 735–750.
- Qiskit 2.x primitives migration guide: https://docs.quantum.ibm.com/api/migration-guides/v2-primitives
