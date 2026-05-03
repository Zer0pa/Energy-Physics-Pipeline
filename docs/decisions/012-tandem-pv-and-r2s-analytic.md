# 012 — Tandem PV + R2S analytic upgrades

**Boundary:** Research infrastructure for in silico energy science: electrochemical conversion (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. No regulatory certification claims. No clinical or human-subject use. Defence / weapons applications are out of scope under operator policy.

## Decision

Two analytic upgrades to deepen the electrochem L4 and fusion L5 paths without GPU dependence:

### Tandem PV (`energy_physics_pipeline/adapters/electrochem/l4_tandem_pv.py`)

Replaces the single-junction Shockley-Queisser fallback (used when Solcore failed to install on Python 3.13 darwin) with a **2-terminal current-matched perovskite/Si tandem** analytic. Outputs:

- Per-junction radiative-limit Voc (perovskite top, silicon bottom).
- Photocurrent budget per junction from AM1.5G integrated photon flux.
- Current-matching constraint (tandem is limited by the lesser-photocurrent junction).
- Tandem fill factor via Green-1981 empirical formula.
- Final PCE clamped to 40% (state-of-art certified tandem PCE ~33% in 2024-2025).
- Full J(V) curve in the DRO under `curve_type=J_vs_V`.

This is **`scientific_valid=False`** — the analytic uses a flat Voc - 0.25 V floor and ignores spectral mismatch, thermal recombination, and series resistance. But it gives operators a defensible Voc/PCE band for the perovskite/Si tandem story before Solcore (or a Linux Runpod) takes over.

### R2S analytic activation (`energy_physics_pipeline/adapters/fusion/l5_r2s.py`)

Replaces the all-stub `OpenmcR2sAdapter` with a single-isotope point-kinetics activation calculator covering:

- **Co-60** chain (from Co-59 impurity in structural steel; T_1/2 = 5.27 yr; long-term contact-dose driver).
- **Mn-56** chain (from Mn-55 impurity; T_1/2 = 2.58 hr; short-term decay-heat driver).
- **He-6** chain (from Be-9 multiplier; T_1/2 = 0.81 s; immediate beta- contributor).

Outputs: decay heat (W) and contact dose (μSv/h at 1 m) at t = 0, 1 h, 1 day, 1 week post-shutdown. Inputs: fusion power (MW), blanket volume (m³), Li-6 enrichment, structural-steel impurity ppm, irradiation duration (yr).

This is **`scientific_valid=False`**; the gate_status is `warn` with a `r2s.analytic_only` failure record, exactly because the calculation lacks spectrum-folded cross-sections, ALARA-class detail, and a real transport step. But it lets the L5 pipeline emit a contract-shaped envelope on real CPU and gives operators a sane order-of-magnitude check against published Eurofer-97 + FLiBe blanket designs (decay heat ~1-10 kW per MW fusion power at shutdown — our analytic lands in this range under default inputs).

## Why ship them now (vs deferring to Runpod)

The Runpod migration is meant to be a **config-flag swap**. If the only fallback at L4 PV / L5 R2S is "all-zero stub", then the pre-Runpod pipeline cannot even smoke-test the L4→DRO→L5 contract end-to-end. These analytic adapters give the pre-Runpod pipeline a *defensible-shape*, *contract-correct* envelope to flow through the audit + KG. The Runpod side replaces the analytic with the real Solcore / OpenMC-R2S; the contract holds.

## Tests

- `tests/integration/test_tandem_pv.py` — 7 tests; physical-bounds checks + DRO contract.
- `tests/integration/test_r2s_analytic.py` — 5 tests; decay decreases over time, dose scales with fusion power, scientific_valid=False, forbidden-intent gate.

Both green; both run in <15 s combined.
