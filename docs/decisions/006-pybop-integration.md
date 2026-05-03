# 006 — PyBOP Parameter Inference Integration

> **BOUNDARY_BLOCK:**
> "Research infrastructure for in silico energy science: electrochemical conversion
> (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics,
> thermoelectrics) and fusion / plasma physics. Outputs are research artifacts.
> No regulatory certification claims. No clinical or human-subject use.
> Defence / weapons applications are out of scope under operator policy."

## Status

Accepted — implemented in `energy_physics_pipeline/adapters/electrochem/l4_pybop.py`.

## Context

The PRD priority order places the Battery Digital Twin squarely in Months 1–4:

> "Battery Digital Twin (Months 1–4): PyBaMM + PyBOP + NREL PINN. Shortest path to revenue."

The existing L4 adapter (`l4.py`) runs a PyBaMM DFN Chen2020 forward simulation.  The
missing piece for the digital twin is the *inverse problem*: given noisy voltage measurements,
recover the underlying cell parameters so that the twin can track degradation and personalise
predictions.  PyBOP (Bayesian Optimisation for battery Problems) v26.3 provides exactly this
capability as a CPU-only Python library with an Apache-2.0 license (class A).

## Decision

Integrate PyBOP as a new L4 adapter `PyBOPParameterInferenceAdapter` that:

1. Wraps the PyBaMM **SPM** (single-particle model), not DFN, for the inference loop.
   The PRD permits SPM for the inverse problem; DFN is reserved for high-fidelity forward
   simulation.  SPM is 5–10× faster than DFN on CPU, keeping the 60-second test budget
   feasible.

2. Infers the **negative electrode solid-phase diffusivity** (`Negative particle diffusivity
   [m2.s-1]`) as the initial parameter subset.  This parameter controls lithium transport
   inside the anode particles and is a primary degradation marker in the SPM literature.
   It was chosen because:
   - It is scalar (one unknown → simplest possible inference problem).
   - It appears directly in both SPM and DFN, enabling future cross-model comparisons.
   - It is accessible as a `pybamm.InputParameter` without model restructuring.

3. Uses `pybop.GaussianLogLikelihoodKnownSigma` + `pybop.SciPyMinimize` as the MAP estimator.
   This is the lightest-weight inference path in PyBOP that avoids the overhead of full MCMC
   while still producing a proper log-likelihood value for the envelope.

4. Falls back to a deterministic fixture (`mode=engineering_stub`, `scientific_valid=False`)
   if PyBOP or PyBaMM cannot be imported, preserving test stability in restricted environments.

## Identifiability note

At 1C discharge over 600 s, the voltage sensitivity to a 20% change in `Negative particle
diffusivity` is approximately 0.45 mV, which is at the noise floor (noise_std_V = 5 mV,
SNR < 0.1).  The adapter correctly propagates this to a `warn` gate status (relative_error > 50%)
rather than silently reporting a falsely precise result.  Higher C-rates or longer experiments
would improve identifiability; the spec parameters are intentionally conservative.

## Consequences

- `energy_physics_pipeline/adapters/electrochem/l4_pybop.py` — new file (owned by this decision).
- `tests/integration/test_pybop_inference.py` — new file (owned by this decision).
- No modifications to frozen foundation files (`l4.py`, `l5.py`, `boundary.py`, schemas, audit, kg).
- The `write_l4_artifacts` helper from `l4.py` is reused for KG and audit writes.
- License class A (Apache-2.0) — no license gate promotion needed.
