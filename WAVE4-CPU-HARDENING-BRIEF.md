# Wave 4 CPU Hardening Brief Before Runpod

## Boundary

Research infrastructure for in silico energy science: electrochemical conversion (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. No regulatory certification claims. No clinical or human-subject use. Defence / weapons applications are out of scope under operator policy.

## Verdict

Do not start Runpod migration yet.

Wave 3 is a useful forward patch and should not be broadly reverted. It added real hardening around Runpod dispatch, production falsifiers, audit/KG enforcement, parser manifests, MCP dispatch, and boundary tests. The repo is still not ready for Runpod because the sovereign readiness gate is higher than an isolated green test run.

The next role should run a focused CPU augment wave. The objective is not to narrate readiness; it is to make readiness mechanically true under the actual overnight operating model: Opus Max lead, Sonnet-level subagents at minimum, parallel worktrees, no user engagement after startup, and a final falsification wave.

## Review Evidence

Review date: 2026-04-30, Sandton / Johannesburg time.

Canonical repo state reviewed:

- Branch: `main`
- Commit: `58ab030`
- Tag: `wave3-cpu-hardening`
- GitHub: `https://github.com/Zer0pa/Energy`

Local checks:

- `bash scripts/full_check.sh`: passes when run in isolation; reports total coverage 79.62 percent.
- `.venv/bin/python -m ruff check energy_pipeline tests`: passes.
- `.venv/bin/python -m ruff check energy_pipeline tests scripts`: fails on unused imports in `scripts/quick_demo.py`.
- `ENERGY_L4_BACKEND=runpod_rest` probe against `/v1/electrochem/l4/pybamm`: returns `200` with `execution_mode=gpu_rest_stub`, proving the normal route ignores the backend flag.
- `.venv/bin/python tools/verify_sources.py --dry-run`: 39 OK, 1 failed (`jorek`, SSL verification), 1 skipped non-authority (`gyroswin`).

Independent xhigh verifier consensus:

- Architecture / Runpod verifier: not ready; only ready for adapter-level mock Runpod dry-run.
- Falsification / reproducibility verifier: not ready; mandatory audit/KG and production falsifier coverage are still bypassable.
- Scientific / data / license verifier: not ready; boundary is stronger, but license/source/manifest/readiness claims still require another CPU wave.

## Decision

No broad revert. Do a Wave 4 augment.

Rationale: Wave 3 moved the codebase closer to the PRD and should be retained. The failures are integration and authority failures, not evidence that the Wave 3 direction is wrong. The next agent must tighten the central execution path, not throw away the work.

## Sovereign Readiness Definition

The repo is ready for Runpod only when all of the following are true from a fresh clone:

1. Changing `ENERGY_L?_BACKEND` is sufficient to switch the same public endpoint from CPU/stub to `runpod_rest`.
2. Clients do not need to call a different `/v1/runpod/...` route to exercise Runpod.
3. Accepted outputs always pass through `accept_envelope` / `accept_envelope_and_dro`.
4. Accepted outputs always emit audit and KG evidence unless explicitly marked as non-accepted dry-run output.
5. Production falsifiers, not inline test helpers, are the authority for the falsification wave.
6. License gates match the source findings and block promotion without real evidence.
7. Source manifests are either verified or demoted from authority.
8. Parallel overnight execution cannot corrupt or lock the shared audit/KG runtime.
9. Reports and handoffs do not claim Runpod readiness until the above is proven.

## Blocking Gaps And Required Fixes

### 1. Same-shape Runpod cutover is still missing

Current behavior:

- `/v1/electrochem/l4/pybamm` returns the stub envelope even when `ENERGY_L4_BACKEND=runpod_rest`.
- The real Runpod adapter is exposed only as `/v1/runpod/{layer}/{domain}/{op}`.
- The plug-replaceability tests check dispatch internals and config visibility, not a same-endpoint production route swap.

Required implementation:

- Add a backend resolver used by normal REST endpoints.
- For each public layer endpoint, route through the resolver according to the relevant `ENERGY_L?_BACKEND`.
- Keep `/v1/runpod/...` as an internal/debug dispatch surface if useful, but it must not be the client-facing cutover mechanism.
- When `ENERGY_L?_BACKEND=runpod_rest` and no `ENERGY_RUNPOD_BASE_URL` is configured, the normal endpoint must return a structured 503/failure envelope, not silently fall back to `gpu_rest_stub`.

Acceptance tests:

- With `ENERGY_L4_BACKEND=runpod_rest` and a fake Runpod upstream, `POST /v1/electrochem/l4/pybamm` calls the fake upstream and returns `execution_mode=runpod_rest`.
- With the same flag and no base URL, the same endpoint returns structured 503 with `runpod_not_configured`.
- Golden fixture output projection is invariant across `local_cpu`, `gpu_rest_stub`, and `runpod_rest`; only allowed provenance/runtime fields differ.
- Add equivalent focused tests for at least one fusion endpoint, preferably `/v1/fusion/l4/scenario`.

### 2. Audit/KG is not mandatory on every accepted output

Current behavior:

- Many REST endpoints create an envelope and return `env.model_dump()` directly.
- Some parser/manifest adapters call `accept_envelope(..., write_audit=False, write_kg=False)` while still returning accepted-looking outputs.
- MCP helpers maintain their own audit/KG singletons rather than using the central enforcement path.

Required implementation:

- Route every accepted REST response through `accept_envelope`.
- Route every accepted adapter response through `accept_envelope` or `accept_envelope_and_dro`.
- Remove accepted-output paths that set `write_audit=False` / `write_kg=False`. If a path is intentionally dry-run/no-write, label it as such and prevent `scientific_valid=True`.
- Make MCP audit/KG emission use the same central enforcement semantics.

Acceptance tests:

- Under `ENERGY_AUDIT_REQUIRED=true`, accepted REST calls increase audit and KG counts.
- Parser outputs with `scientific_valid=True` emit audit/KG.
- A deliberately missing audit/KG path fails in strict mode.
- `energy_pipeline/rest/app.py`, parser adapters, real L4/L5 adapters, and MCP wrappers have direct tests proving central acceptance.

### 3. Audit/KG runtime is not parallel-safe enough for overnight work

Current behavior:

- `AuditWriter()` defaults to `audit_log/audit.duckdb`.
- Parallel verifier processes can hold competing DuckDB write locks.
- `scripts/full_check.sh` passes when isolated, but the intended execution model uses multiple subagents and worktrees.

Required implementation:

- Add env-configurable runtime paths, at minimum `ENERGY_AUDIT_DIR`, `ENERGY_AUDIT_DB_PATH`, and equivalent KG path controls.
- Ensure test runs use a temporary audit/KG root, not the repo's tracked `audit_log` / `kg_store`.
- Ensure process-global audit/KG singletons can be closed/reset between tests.
- Either serialize shared writes intentionally or isolate each subagent/worktree by runtime path. Isolation is preferred.

Acceptance tests:

- A multiprocessing test runs two or more concurrent accepted outputs without DuckDB lock failure.
- `scripts/full_check.sh` creates an isolated temporary runtime by default.
- No test writes persistent state to the repo root except intentional `.keep` files.
- `git status --short` is clean after the strict gate.

### 4. Production falsifier coverage is incomplete

Current behavior:

- `DEFAULT_FALSIFIER_SET` exists, but at least PV fill factor is not enforced at the envelope default-falsifier level.
- Several named falsification-wave gates still rely on inline helpers in tests or model validators rather than production central gates.

Required implementation:

- Add/verify production gates for:
  - PV fill factor outside `[0, 1]`
  - COCOS / coordinate convention mismatch
  - negative plasma temperature
  - negative plasma density
  - thermoelectric efficiency above Carnot
  - battery SoC outside `[0, 1]`
  - missing IMAS / IDS version
  - cross-model disagreement thresholds
  - recursive unit enforcement for physical numeric leaves
- Apply the default production gate set to all accepted envelopes.

Acceptance tests:

- Each bad case is created as a realistic envelope or DRO and rejected by production acceptance.
- Inline test helpers may build fixtures, but no inline helper may be the authority for a gate.
- Falsification wave reports production gate IDs, not helper-only IDs.

### 5. License gates and source findings are misaligned

Current behavior:

- GPL / conditional Class B isolation evidence accepts any `https://` URL in places where a license-grant/isolation record is required.
- Registry/manifest classes conflict with `sources_log/license_findings.jsonl` for some tools, including fairchem/eSEN, PEMD, and PiNet2.
- Reports overstate clean source/license status.

Required implementation:

- Tighten GPL/conditional isolation evidence to `kg://license-grant/...` or a vetted local evidence record with explicit grant/isolation semantics.
- Do not accept a public project URL as isolation evidence.
- Align registry entries, parser manifest defaults, tests, and source findings.
- If evidence is unresolved, mark the tool blocked, conditional, or manifest-only; do not promote to Class A by convenience.

Acceptance tests:

- `https://github.com/.../LICENSE` does not satisfy isolation/grant evidence for GPL/conditional tools.
- `kg://license-grant/<tool>` does satisfy promotion when the evidence record exists.
- eSEN/fairchem, PEMD, PiNet2, PF-PINO, GENE, AQCat25, AlphaPEM, LBPM, SCAPS-1D/Solcore all have explicit tests matching source findings.

### 6. Source verification is not clean

Current behavior:

- Live dry-run gives 39 verified, 1 failed (`jorek` SSL), 1 skipped non-authority (`gyroswin`).
- The checked-in summary can be read as cleaner than the current live verification permits.

Required implementation:

- Fix or replace the JOREK source URI with a verifiable primary source.
- Keep GyroSwin non-authority unless a primary source is found.
- Make `verification_summary.md` distinguish verified, failed, skipped non-authority, and non-fetchable entries.

Acceptance tests:

- `tools/verify_sources.py --dry-run` returns zero authority failures, or failed entries are explicitly demoted from authority and excluded from readiness claims.
- Summary wording does not state "0 failed" while any entry renders as `FAIL`.

### 7. CPU manifest coverage still does not match PRD wording

Current behavior:

- CIF, xyz, SMILES, and several tool manifests exist.
- OPTIMADE / Materials Project / NOMAD pointer implementations appear absent or only docstring-level.

Required implementation:

- Add manifest-only pointer adapters for OPTIMADE, Materials Project, and NOMAD that store no bulk data.
- Include fields for query string, source URI, checksum/provenance, license/rights notes, and intended downstream layer.
- Keep these as metadata/pointer artifacts unless a small fixture is explicitly needed.

Acceptance tests:

- Contract tests validate all three pointer types.
- No bulk datasets are committed.

### 8. Reports and handoffs overclaim readiness

Current behavior:

- `FINAL-REPORT.md` and `HANDOFF-FROM-OVERNIGHT-EXECUTOR.md` claim ready for Runpod.
- This brief supersedes those claims.

Required implementation:

- Keep this brief as the readiness authority until Wave 4 gates pass.
- After Wave 4 passes, update final/handoff docs with the actual new commit, exact commands, and falsification evidence.
- Do not claim Runpod readiness until same-shape config cutover and mandatory audit/KG are mechanically proven.

Acceptance tests:

- A new verifier reading only top-level docs cannot conclude "ready for Runpod" before Wave 4 gates pass.

### 9. Script quality and strict gate polish

Required implementation:

- Include `scripts` in Ruff or explicitly justify exclusions.
- Fix `scripts/quick_demo.py` unused imports.
- Consider raising the soft coverage gate once stability is restored; do not use coverage as a substitute for scientific authority.

Acceptance tests:

- `.venv/bin/python -m ruff check energy_pipeline tests scripts` passes.
- `bash scripts/full_check.sh` passes and leaves `git status --short` clean.

## Required Agent Topology

The next execution lead is Opus Max or equivalent, acting as chief engineer. It must use subagents to preserve lead context for scientific and architectural thinking.

Minimum subagents:

1. Runpod same-shape cutover architect / implementer.
2. Audit/KG concurrency and central enforcement implementer.
3. Production falsifier implementer.
4. License/source alignment verifier.
5. CPU manifest/pointer adapter implementer.
6. Final falsification verifier.

Use Sonnet-level agents at minimum. Use Opus-level agents where architecture, licensing, or scientific falsification is ambiguous. The lead has authority to make engineering decisions that improve performance, datafulness, and scientific power without asking the user, provided the hard boundary is preserved.

## Required Final Gate

The Wave 4 agent may report "ready for Runpod" only after all commands pass from a clean clone or clean worktree:

```bash
python3.12 -m venv .venv || python3.13 -m venv .venv
.venv/bin/pip install -e '.[test,tda,mcp]'
.venv/bin/pip install pybamm pybop pypsa pvlib cantera pyscf netCDF4 freegs omas pyrokinetics qiskit mcp ripser persim
.venv/bin/python -m ruff check energy_pipeline tests scripts
.venv/bin/python -m pytest tests -q --tb=short
bash scripts/full_check.sh
.venv/bin/python tools/verify_sources.py --dry-run
.venv/bin/python tools/runpod_cutover_checklist.py
git status --short
```

Additional required probes:

- Same-endpoint `ENERGY_L4_BACKEND=runpod_rest` fake-upstream test.
- Same-endpoint fusion fake-upstream test.
- Parallel audit/KG collision test.
- Mandatory audit/KG count test for REST, parser, adapter, and MCP paths.
- Production falsifier wave with no inline authority helpers.

## Expected Output From Next Agent

If Wave 4 succeeds:

- Commit and push implementation to `main`.
- Update `FINAL-REPORT.md`, `HANDOFF-FROM-OVERNIGHT-EXECUTOR.md`, `RUNBOOK.md`, and `NEXT-WAVE-PLAN.md`.
- Add a one-page Runpod readiness brief covering architecture, datasets, process/sequence, differentiators by layer, and parked GPU-only work.
- Provide the exact GitHub commit and the strict gate transcript summary.

If Wave 4 does not succeed:

- Commit and push a new hardening brief with precise failing gates.
- Do not claim readiness.
- Do not begin Runpod migration.
