# CPU Hardening Brief Before Runpod

## Boundary

Research infrastructure for in silico energy science: electrochemical conversion (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. No regulatory certification claims. No clinical or human-subject use. Defence / weapons applications are out of scope under operator policy.

## Verdict

Not ready for Runpod migration yet.

The latest implementation is substantial and the full test suite can pass in a fully provisioned CPU environment, but the repo still overclaims the sovereign Runpod-readiness gate. Another CPU hardening wave is required before GPU work starts.

## Verification Evidence

Local review on 2026-04-30 after syncing `origin/main` at `13a99d5` / tag `wave2-cpu-complete`:

- `ruff check energy_pipeline tests`: passed.
- `pytest tests -q --tb=short`: 333 passed after installing optional CPU dependencies (`pybamm`, `pybop`, `pypsa`, `pvlib`, `cantera`, `pyscf`, `netCDF4`, `freegs`, `omas`, `pyrokinetics`, `qiskit`, `mcp`, `ripser`, `persim`).
- Coverage run: 333 passed, 77.1 percent total coverage.
- Falsification wave: passes in tests.
- Source manifest verification from this machine: 34/41 verified; 7 unresolved because of HTTP 404 or SSL verification failure.

Independent xhigh falsification agents found that a minimally provisioned environment fails scientific/integration tests because optional CPU dependencies are not installed. That is partly an environment/setup issue, but it also exposes a real reproducibility problem: the repo must provide one strict CPU install/check path that cannot silently skip or tolerate scientific gates.

## Blocking Gaps

### 1. Runpod cutover is not yet a config-flag swap

`energy_pipeline/rest/app.py` still has `/v1/runpod/{layer}/{domain}` returning 503. Normal layer routes do not dispatch by `ENERGY_L?_BACKEND`, and tests explicitly state `runpod_rest` is not live-tested. The next wave must implement a backend resolver and a mockable Runpod REST adapter so the same request can flow through `local_cpu`, `gpu_rest_stub`, and `runpod_rest` without changing endpoint shape.

Acceptance:

- `ENERGY_L?_BACKEND=runpod_rest` routes through the same typed adapter interface.
- If no Runpod URL is configured, the error is structured and audited.
- A fake Runpod handler in tests proves schema parity and golden fixture invariance.
- Plug-replaceability tests preserve golden fixture behavior except runtime/provenance fields.

### 2. Audit/KG is not sovereign

Several adapters accept `audit_writer=None` and `kg_store=None`, and REST stubs do not write audit/KG. The PRD requires audit/KG writes before outputs are accepted.

Acceptance:

- If `ENERGY_AUDIT_REQUIRED=true`, accepted outputs require an audit writer and KG store or use a configured default.
- REST stubs write audit and KG entries.
- Tests fail when an accepted adapter emits an envelope without audit/KG evidence.

### 3. Falsification wave is partly test-local

Several falsifiers are defined inline in `tests/falsification/test_falsification_wave.py` instead of production `energy_pipeline/l6/router.py` or a production falsifier module. The tests prove helper logic, not that live adapters and REST outputs are centrally blocked.

Acceptance:

- Move COCOS/unit, negative temperature/density, above-Carnot, SoC range, PV fill-factor, IMAS DD-version, and cross-model disagreement threshold gates into production falsifier code.
- Apply the default falsifier set to all REST and adapter outputs before acceptance.
- Keep test-local helpers only for fixtures, not authority logic.

### 4. Unit enforcement is too narrow

`units_required_falsifier` only inspects `outputs.payload.quantities`. Many adapters emit direct numeric fields outside that convention. The next wave must either normalize payloads into `quantities` or recursively enforce units for physical numeric leaves.

Acceptance:

- Numeric physical leaves without units fail or are explicitly whitelisted as dimensionless.
- Dimensionless fields use unit `"1"` or `"dimensionless"`.
- Fusion and electrochemistry outputs pass through the same unit checker.

### 5. License policy is inconsistent

ADR 001 says GPL Class B requires isolation/grant evidence, while schema tests allow Class B scientific promotion without evidence. Some weak-copyleft tools are also classified inconsistently.

Acceptance:

- Align license classes across ADR, `LicenseClass`, registry entries, tests, and source findings.
- GPL/AGPL Class B requires isolation evidence before scientific/product promotion.
- LGPL/FAIR/Llama-like conditional licenses use a distinct conditional class with evidence requirements.
- Tests cover Class B, C, D, and E promotion behavior.

### 6. Fusion forbidden-use blocker is narrower than policy

`boundary.py` uses exact substring terms. It blocks many obvious forbidden strings, but policy-equivalent variants around military use, diversion, extraction, purification, stockpiling, yield, and weapons optimization need broader matching.

Acceptance:

- Add normalized phrase and regex/stem matching for policy-equivalent forbidden intents.
- Add negative tests for paraphrases, not just exact terms.
- Ensure blocked requests emit no technical optimization output.

### 7. Source manifests are not fully content-addressed

`sources_log/verification_summary.md` is not fully clean. Some URLs are stale, moved, or inaccessible.

Acceptance:

- Replace stale source URLs where primary sources have moved.
- If a source cannot be verified, demote it to unresolved and ensure it is not used as authority.
- Update reports so they do not claim every manifest has a real digest unless all 41 do.

### 8. MCP surface is partly smoke-level

`pybamm_mcp.py` calls `PyBaMMBatteryAdapter.run` with unsupported keyword arguments and falls back instead of proving the real adapter path. Other MCP wrappers need the same adapter-call audit.

Acceptance:

- MCP wrappers call adapters using their real typed/spec APIs.
- Tests assert whether the returned MCP result came from `local_cpu` or `engineering_stub`.
- If optional deps are installed, real-path MCP tests must exercise real adapters.

### 9. CPU-feasible parser/manifests remain incomplete

Several PRD CPU-side items are present as docs/registry intent rather than runnable parser/manifest adapters: CIF/xyz/extxyz/SMILES/OPTIMADE/Materials Project/NOMAD, GPAW/CP2K/Wannier90/Z2Pack, fairchem/eSEN/LAMMPS/PEMD/PiNN, OpenLB/LBPM, and OpenModelica/FMI.

Acceptance:

- Build minimal parser/manifest adapters and tests for these CPU-feasible items, or explicitly demote them from the CPU-complete claim with a reason.
- Do not park parser/manifest work behind Runpod unless GPU is genuinely required.

### 10. Strict check path must be honest

`scripts/full_check.sh` currently tolerates scientific test failure with `|| true`. That converts a scientific gate into a warning.

Acceptance:

- Remove `|| true` from scientific tests.
- Provide one reproducible strict command that installs required CPU deps and runs lint, contract, falsification, scientific, integration, CLI, source verification, and coverage.
- Final report must cite that strict command, not a permissive one.

## Next-Agent Mandate

Do not start Runpod work. Run a CPU hardening wave first.

Work order:

1. Make strict install/check reproducible.
2. Fix Runpod backend resolver and mock Runpod parity test.
3. Make audit/KG required for accepted outputs.
4. Move test-local falsifiers into production and apply centrally.
5. Fix unit enforcement.
6. Align license policy and tests.
7. Harden fusion forbidden-use matching.
8. Clean or demote source manifests.
9. Fix MCP wrappers to call real adapter APIs.
10. Complete or explicitly demote remaining CPU parser/manifest adapters.
11. Update `FINAL-REPORT.md`, `HANDOFF-FROM-OVERNIGHT-EXECUTOR.md`, `RUNBOOK.md`, and `NEXT-WAVE-PLAN.md` so they no longer overclaim Runpod readiness until the new gates pass.

## Promotion Gate

Only advise "ready for Runpod" when all are true from a fresh clone:

- Strict CPU check passes without tolerated scientific failures.
- Full tests pass with optional CPU dependencies installed.
- Falsification wave exercises production falsifiers, not only test helpers.
- Audit/KG writes are mandatory for accepted outputs.
- `runpod_rest` dispatch is live-testable through a fake Runpod backend.
- Source manifests are verified or unresolved sources are demoted from authority.
- Reports accurately describe scientific-valid, engineering-stub, and parked work.
