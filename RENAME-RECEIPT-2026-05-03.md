# Rename Receipt — 2026-05-03

## Boundary

Research infrastructure for in silico energy science: electrochemical conversion (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. No regulatory certification claims. No clinical or human-subject use. Defence / weapons applications are out of scope under operator policy.

## Old and New Names

| Surface | Old | New |
| --- | --- | --- |
| Display name | Zer0pa Energy / Energy | Energy Physics Pipeline |
| GitHub owner | `Zer0pa` | `Zer0pa` |
| GitHub repo slug | `Energy` | `Energy-Physics-Pipeline` |
| Canonical GitHub URL | `https://github.com/Zer0pa/Energy` | `https://github.com/Zer0pa/Energy-Physics-Pipeline` |
| Python distribution | `energy_pipeline` | `energy-physics-pipeline` |
| Python import root | `energy_pipeline` | `energy_physics_pipeline` |
| Console script | `energy` | `energy-physics` |
| Package directory | `energy_pipeline/` | `energy_physics_pipeline/` |

## Execution Summary

- **Date:** 2026-05-03
- **Executor:** Claude Sonnet 4.6 (clean-rename executor)
- **Branch pushed to:** `main`
- **GitHub rename API:** `gh api -X PATCH repos/Zer0pa/Energy -f name='Energy-Physics-Pipeline'`

## Local Commit SHA

```
a62f3d9cb4d067d47fe31d7333ce626c7df0bc88
```

## Verification Commands and Results

### Ruff
```
.venv-rename/bin/python -m ruff check energy_physics_pipeline tests scripts tools
→ All checks passed!
```

### Pytest (full suite)
```
.venv-rename/bin/python -m pytest tests -q --tb=short
→ 475 passed, 0 failed, 226 warnings in 31.47s
```

### full_check.sh (with isolated audit/KG dirs)
```
PY=.venv-rename/bin/python ENERGY_AUDIT_DIR=$(mktemp -d) ENERGY_AUDIT_DB_PATH=... ENERGY_KG_DIR=$(mktemp -d) bash scripts/full_check.sh
→ STRICT FULL CHECK OK
→ Coverage: 79.72% (≥70% gate)
→ Boundary: 386 bytes OK
```

### verify_sources.py
```
.venv-rename/bin/python tools/verify_sources.py --dry-run
→ results: 39 ok, 0 fail, 2 skipped (non-authority / non-fetchable)
```

### runpod_cutover_checklist.py
```
.venv-rename/bin/python tools/runpod_cutover_checklist.py
→ Exit 0 — checklist printed successfully
```

### Import verification
```
.venv-rename/bin/python -c "import energy_physics_pipeline; print('new import OK:', energy_physics_pipeline.__name__)"
→ new import OK: energy_physics_pipeline

import energy_pipeline  →  ModuleNotFoundError (correctly absent)
```

### CLI verification
```
.venv-rename/bin/energy-physics --help
→ Usage: energy-physics [OPTIONS] COMMAND [ARGS]...
→ Research infrastructure for in silico energy science: ...
```

## Old-Name Search Summary

Final `rg` sweep (excluding CLEAN-RENAME-PRD.md as allowed historical PRD):

- `from energy_pipeline` — **0 hits**
- `import energy_pipeline` — **0 hits**
- `Zer0pa/Energy[^-]` — **0 hits**
- `energy_pipeline.` / `energy_pipeline/` — **0 active hits** (only in CLEAN-RENAME-PRD.md)

Allowed residual mentions in CLEAN-RENAME-PRD.md: that document is the rename specification itself and references old names only as rename targets, not as active identity.

## GitHub Rename Command Used

```bash
gh api -X PATCH repos/Zer0pa/Energy -f name='Energy-Physics-Pipeline'
```

## Remote Verification (Post-Push)

### Repo state
```json
{
  "name": "Energy-Physics-Pipeline",
  "nameWithOwner": "Zer0pa/Energy-Physics-Pipeline",
  "visibility": "INTERNAL",
  "url": "https://github.com/Zer0pa/Energy-Physics-Pipeline",
  "defaultBranchRef": {"name": "main"}
}
```

### Remote head SHA
```
a62f3d9cb4d067d47fe31d7333ce626c7df0bc88
```
Commit date: 2026-05-03T11:56:36Z

### README blob SHA
```
71bf4943ab35248eb98c713c1188b588746b597f
```

### pyproject.toml blob SHA
```
3cd9ebaaca10f469646d9a5102eda7fa31b6b012
```

## README Structural Verification (Remote)

First-ten section headings (exact):
1. `## What This Is`
2. `## Pipeline Mechanics`
3. `## Key Metrics`
4. `## Repo Identity`
5. `## Readiness`
6. `## What We Prove`
7. `## What We Don't Claim`
8. `## Verification Status`
9. `## Proof Anchors`
10. `## Repo Shape`

Key Metrics rows: **4** ✓  
Proof Anchors rows: **6** ✓

## Proof Anchor Resolution (Remote, GitHub main)

| Path | SHA |
| --- | --- |
| `RUNPOD-READINESS.md` | `523cae49fc76de2ec63325f53e40cfbc795cd58e` |
| `H100-ENTERPRISE-COMPLETION-PLAN.md` | `a3ab6c2d60e8ca859152a0853572551090ce454b` |
| `FINAL-REPORT.md` | `d4d690ac96a7ad3fe16ddc32d12a808f5bae28e3` |
| `PRD.md` | `5192c8d23d41dd70a193424d6daf813bd2d585ce` |
| `tests/integration/test_runpod_same_endpoint.py` | `bada670131a2473d288152b43d87962ce224c359` |
| `sources_log/verification_summary.md` | `0b544b46b5239b27c7c333f80fbbab86b22c8d15` |

All 6 proof anchors resolve on GitHub main. ✓

## Final Visibility

**INTERNAL** — unchanged from pre-rename state. ✓

## Enterprise H100 Completion Status

**ACTIVE / NOT COMPLETE.** No GPU-backed enterprise completion wave has passed. The first serious H100 mandate (one electrochem GPU lane, one fusion or reasoner lane, live same-endpoint cutover, audit/KG provenance, full falsification/regression) remains outstanding. See [`H100-ENTERPRISE-COMPLETION-PLAN.md`](./H100-ENTERPRISE-COMPLETION-PLAN.md) for the full gate definition and hour estimates.
