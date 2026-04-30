# 011 — CPU package install failures on Python 3.13 darwin (deferred to Runpod-Linux)

**Boundary:** Research infrastructure for in silico energy science: electrochemical conversion (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. No regulatory certification claims. No clinical or human-subject use. Defence / weapons applications are out of scope under operator policy.

## Context

Several Python packages used at L2 (MLIP), L6 (active-learning), and adjacent are present in PRD but DO NOT install cleanly on Python 3.13 darwin-arm:

| Package | Failure mode | Root cause |
|---|---|---|
| `mace-torch` | `ResolutionImpossible` for torch | `torch` has no Python 3.13 darwin-arm wheel as of 2026-04 |
| `fairchem-core` | inherits torch dep | same |
| `botorch` | inherits torch dep | same |
| `ax-platform` | sklearn build failure | sklearn build path also affected |
| `solcore` | `metadata-generation-failed` | upstream build system not 3.13-compatible |
| `aiida-core` (optional) | postgres / docker assumptions | not installable cleanly without Postgres on Mac |

## Resolution strategy

1. **Document the gap** — this file.
2. **Tag the missing extras** in `pyproject.toml` under `runpod-only`.
3. **Ship analytic / fixture fallbacks** for every layer where the missing tool would be the canonical CPU path:
   - L2 MACE → `MLIPManifestAdapter` (manifest-only). MACE inference replaces it on Linux.
   - L4 Solcore → `SolcorePvAdapter` analytic Shockley-Queisser fallback; tandem analytic in `l4_tandem_pv.py`.
   - L6 BoTorch → not yet wired; deferred. The L6 router operates today without active-learning; a future wave wires `scipy.optimize`-based GP surrogates as an interim.
4. **CI tolerates the gap** — the `.github/workflows/ci.yml` `Install advanced CPU deps (best-effort)` step uses `|| true`.
5. **Runpod-Linux migration auto-resolves** — when the pipeline runs on Linux (CI ubuntu-latest, Runpod), all four extras install. The `runpod-only` extra in pyproject is the install target there.

## Acceptance gate retained

The sovereign acceptance gate (12-of-12 falsification wave + electrochem e2e + fusion Phase-0 + reasoning bench refusal_recall=1.0) clears WITHOUT these packages. The gap reduces capability *quantity*, not *correctness*. Boundary discipline, license gating, plug-replaceability, and audit/KG remain green.

## Verifying the gap status

```bash
.venv/bin/python -c "
import importlib
for mod in ('mace', 'fairchem', 'torch', 'botorch', 'ax', 'solcore'):
    try:
        m = importlib.import_module(mod)
        print(f'{mod:<14}: OK ({getattr(m, \"__version__\", \"unknown\")})')
    except Exception as e:
        print(f'{mod:<14}: MISSING ({type(e).__name__})')
"
```

Run this on every dev machine. If a package newly works on darwin (e.g. torch ships a 3.13 wheel), file an issue tagged `runpod-only` to flip it off the deferred list.
