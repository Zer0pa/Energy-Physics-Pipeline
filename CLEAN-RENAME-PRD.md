# Clean Pre-Public Rename PRD

## Boundary

Research infrastructure for in silico energy science: electrochemical conversion (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. No regulatory certification claims. No clinical or human-subject use. Defence / weapons applications are out of scope under operator policy.

## Mission

Rename this repository and codebase from the generic Energy identity to **Energy Physics Pipeline** before public-facing consumption expands.

This is not a cosmetic README edit. It is a clean pre-public rename across:

- GitHub repository name and URL;
- README front door;
- all active agent docs, prompts, handoffs, runbooks, reports, receipts, and planning docs;
- `pyproject.toml`;
- Python distribution name;
- Python package/module import root;
- CLI command and entry point;
- REST/CLI/module import strings;
- MCP registry module paths;
- tests;
- scripts and tools;
- verification commands and receipts.

The executing agent must run end-to-end until the repo is renamed, imports are renamed, tests pass, GitHub main is updated, remote receipts are recorded, and stale identity strings are either removed or explicitly quarantined as historical rename evidence.

No partial completion is acceptable.

## Approved target names

Use these exact names unless the operator gives a later written override:

| Surface | Old | New |
| --- | --- | --- |
| Display name | Zer0pa Energy / Energy | Energy Physics Pipeline |
| GitHub owner | `Zer0pa` | `Zer0pa` |
| GitHub repo slug | `Energy` | `Energy-Physics-Pipeline` |
| Canonical GitHub URL | `https://github.com/Zer0pa/Energy` | `https://github.com/Zer0pa/Energy-Physics-Pipeline` |
| Python distribution | `energy_pipeline` | `energy-physics-pipeline` |
| Python import root | `energy_pipeline` | `energy_physics_pipeline` |
| Console script | `energy` | `energy-physics` |
| Front-door identifier | `Energy` | `Energy Physics Pipeline` |

Allowed natural-language usage after the rename:

- The word `energy` may still appear as a scientific domain noun.
- `EnergyConfig`, ENERGY environment variables, and the boundary phrase may remain if they are semantically part of the runtime contract. Do not rename `ENERGY_*` env vars in this wave unless every doc, test, and runtime path is updated and the full suite remains green.
- Historical docs may mention the old name only in a dedicated rename/audit context, not as the active repo identity.

Forbidden active-identity remnants after completion:

- `https://github.com/Zer0pa/Energy` in README, active startup prompts, handoffs, runbooks, PRDs, or quick-start commands.
- `Zer0pa/Energy` as canonical repo.
- `Zer0pa Energy` as the project name.
- `energy_pipeline` as import root, package directory, console entry point, coverage source, MCP module path, or test import.
- `energy` as the console script in active instructions.

## Non-negotiable completion standard

The agent must not declare done unless all are true:

1. GitHub repo is renamed to `Zer0pa/Energy-Physics-Pipeline`.
2. Visibility is unchanged.
3. Local `origin` points to `https://github.com/Zer0pa/Energy-Physics-Pipeline.git`.
4. Python package directory is `energy_physics_pipeline/`.
5. `import energy_physics_pipeline` works in a fresh venv.
6. `import energy_pipeline` fails in a fresh venv unless the operator explicitly requested a compatibility alias, which they have not.
7. Console script is `energy-physics`; old `energy` script is not the active documented command.
8. Full strict suite passes.
9. GitHub main is pushed.
10. GitHub main is re-read after push.
11. Final head SHA and README blob SHA are recorded in a rename receipt.

If any item fails, the agent must keep fixing. If external permissions block the GitHub rename, commit all local rename work that can safely land, create `RENAME-BLOCKED-REPORT.md` with the exact error and next command, push if possible, and do not claim completion.

## Starting assumptions

The executing agent has zero conversation context. The repo has previously been an internal live lab workstream with:

- a Lab Front Door README spine;
- CPU-first Energy Physics Pipeline implementation;
- Runpod readiness evidence;
- H100 enterprise completion plan;
- active boundary restrictions.

There are no currently active dependent agents. Still, the executing agent must verify GitHub state before editing.

## Required first actions

Run these before edits:

```bash
gh repo view Zer0pa/Energy --json name,nameWithOwner,visibility,defaultBranchRef,url
gh pr list --repo Zer0pa/Energy --state open --limit 50
gh issue list --repo Zer0pa/Energy --state open --limit 50
git fetch origin --tags
git checkout main
git pull --ff-only origin main
git status --short --branch
```

Rules:

- Do not change repository visibility.
- If there are open PRs, inspect them before proceeding. Do not overwrite active work.
- If there is an open issue that directly changes the rename instruction, follow the issue only if it is newer and operator-authored. Otherwise follow this PRD.
- Work from a clean tree. If the tree is dirty before you edit, identify whether changes are yours. Do not discard user changes.

## Execution order

### Phase 1 - Inventory

Inventory all active old-identity strings before editing:

```bash
rg -n --hidden \
  -g '!*.pyc' \
  -g '!__pycache__/**' \
  -g '!audit_log/**' \
  -g '!kg_store/**' \
  -g '!htmlcov/**' \
  -g '!.venv/**' \
  -e 'energy_pipeline' \
  -e 'Zer0pa/Energy\b' \
  -e 'github.com/Zer0pa/Energy\b' \
  -e 'Zer0pa Energy' \
  -e 'Energy Pipeline' \
  -e 'energy = "energy_pipeline' \
  .
```

Do not blindly replace every occurrence of the word `Energy`. The scientific domain term remains valid. Replace identity and module strings deliberately.

### Phase 2 - Python package/module rename

Required changes:

1. Rename the source directory:

   ```bash
   git mv energy_pipeline energy_physics_pipeline
   ```

2. Replace imports and module strings across source, tests, scripts, tools, docs, MCP registry, CLI uvicorn strings, and pyproject:

   - `from energy_pipeline...` -> `from energy_physics_pipeline...`
   - `import energy_pipeline...` -> `import energy_physics_pipeline...`
   - `energy_pipeline.` -> `energy_physics_pipeline.`
   - `"energy_pipeline...` -> `"energy_physics_pipeline...`
   - `energy_pipeline/rest/app.py` path docs -> `energy_physics_pipeline/rest/app.py`
   - `energy_pipeline.mcp_servers.*` -> `energy_physics_pipeline.mcp_servers.*`
   - `energy_pipeline.cli.main:app` -> `energy_physics_pipeline.cli.main:app`

3. Update internal docstrings where they describe the package identity.

4. Do not leave a compatibility package named `energy_pipeline`. This is pre-public; clean rename is preferred over alias debt.

5. Remove stale generated metadata if tracked:

   ```bash
   git ls-files '*egg-info*'
   ```

   If old `energy_pipeline.egg-info` files are tracked, remove them from git and regenerate only if the repo intentionally tracks metadata. Prefer not tracking generated egg-info.

### Phase 3 - `pyproject.toml`

Required target state:

```toml
[project]
name = "energy-physics-pipeline"
description = "Energy Physics Pipeline - CPU-first in silico research infrastructure for electrochemistry and fusion / plasma physics."

[project.scripts]
energy-physics = "energy_physics_pipeline.cli.main:app"

[tool.setuptools.packages.find]
include = ["energy_physics_pipeline*"]

[tool.coverage.run]
source = ["energy_physics_pipeline"]
omit = [
  "energy_physics_pipeline/mcp_servers/__main__*",
  "*/__init__.py",
]
```

Do not leave the old distribution name or script name active.

### Phase 4 - CLI and runtime strings

Required updates:

- Typer app title/table names may say `Energy Physics Pipeline`.
- Uvicorn target must be `energy_physics_pipeline.rest.app:app`.
- Docs and quick starts must invoke `energy-physics`, not `energy`.
- Tests must not import `energy_pipeline`.
- MCP registry module strings must point to `energy_physics_pipeline`.
- Any command that uses `python -m energy_pipeline...` must become `python -m energy_physics_pipeline...`.

Validation:

```bash
.venv/bin/python - <<'PY'
import importlib
import energy_physics_pipeline
print("new import OK", energy_physics_pipeline.__name__)
try:
    importlib.import_module("energy_pipeline")
except ModuleNotFoundError:
    print("old import correctly absent")
else:
    raise SystemExit("FAIL: old import root energy_pipeline still imports")
PY
```

Run this in a fresh venv, not an old dirty editable environment.

### Phase 5 - README front door

Keep the Lab Front Door first-ten spine exactly:

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

Required README target:

- Title: `# Energy Physics Pipeline`
- Lead: <=30 words.
- Boundary block remains verbatim.
- Repo Identity URL becomes `https://github.com/Zer0pa/Energy-Physics-Pipeline`.
- Package row becomes `energy_physics_pipeline`.
- Quick Start clone URL becomes `https://github.com/Zer0pa/Energy-Physics-Pipeline`.
- Quick Start folder becomes `Energy-Physics-Pipeline`.
- CLI command becomes `energy-physics`.
- Preserve blockers and non-claims: Runpod migration can begin, enterprise H100 completion is active/not complete.
- Exactly four Key Metrics rows.
- No more than six Proof Anchors.
- Every Proof Anchor path must resolve on GitHub main after push.

### Phase 6 - Active docs and agent docs

Update active docs, prompts, and handoffs. This includes at minimum:

- `BOUNDARY.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `MODUS-OPERANDI.md`
- `PRD.md`
- `RUNBOOK.md`
- `RUNPOD-READINESS.md`
- `H100-ENTERPRISE-COMPLETION-PLAN.md`
- `FINAL-REPORT.md`
- `EXECUTION-STATE.md`
- `NEXT-WAVE-PLAN.md`
- `FRONT-DOOR-RECEIPT-2026-05-02.md`
- `HANDOFF-*.md`
- `ORCHESTRATOR-STARTUP-PROMPT.md`
- `OVERNIGHT-EXECUTOR-STARTUP-PROMPT.md`
- `WAVE4-*.md`
- any future startup prompt or receipt file added during this rename.

Rules:

- Update canonical repo URLs to `https://github.com/Zer0pa/Energy-Physics-Pipeline`.
- Update active role names to Energy Physics Pipeline where it refers to this repo/project.
- Preserve domain references to energy science where scientifically meaningful.
- Preserve the boundary exactly.
- Preserve no-cross-workstream-substrate sharing.
- Preserve H100 completion estimates and anti-demo posture.
- Preserve historical chronology, but do not let historical text read as current canonical identity.

### Phase 7 - Tests, scripts, and tools

Update every test import and script reference.

Required target checks:

```bash
rg -n --hidden \
  -g '!*.pyc' \
  -g '!__pycache__/**' \
  -g '!audit_log/**' \
  -g '!kg_store/**' \
  -g '!htmlcov/**' \
  -g '!.venv/**' \
  -e 'from energy_pipeline' \
  -e 'import energy_pipeline' \
  -e 'energy_pipeline\.' \
  -e 'energy_pipeline/' \
  -e 'energy_pipeline:' \
  -e 'energy = "energy_pipeline' \
  .
```

This command must return no active code/test/doc hits. If it only hits this PRD or a rename receipt, that is allowed if the file clearly identifies the string as historical old identity.

### Phase 8 - Clean generated files

Before test execution:

```bash
bash scripts/clean_runtime.sh || true
find . -type d -name '__pycache__' -prune -exec rm -rf {} +
find . -type f -name '*.pyc' -delete
rm -rf .pytest_cache .ruff_cache htmlcov .coverage coverage.xml
```

Do not remove source fixtures, source manifests, docs, or receipts.

### Phase 9 - Fresh venv install and full verification

Use a fresh venv to avoid old editable package residue:

```bash
rm -rf .venv-rename
python3.12 -m venv .venv-rename || python3.13 -m venv .venv-rename || python3 -m venv .venv-rename
.venv-rename/bin/python -m pip install --upgrade pip
.venv-rename/bin/pip install -e '.[test,tda,mcp]'
.venv-rename/bin/pip install pybamm pybop pypsa pvlib cantera pyscf netCDF4 freegs omas pyrokinetics qiskit mcp ripser persim
```

Run:

```bash
.venv-rename/bin/python -m ruff check energy_physics_pipeline tests scripts tools
.venv-rename/bin/python -m pytest tests -q --tb=short
tmp_audit=$(mktemp -d)
tmp_kg=$(mktemp -d)
ENERGY_AUDIT_DIR="$tmp_audit" ENERGY_AUDIT_DB_PATH="$tmp_audit/audit.duckdb" ENERGY_KG_DIR="$tmp_kg" bash scripts/full_check.sh
.venv-rename/bin/python tools/verify_sources.py --dry-run
.venv-rename/bin/python tools/runpod_cutover_checklist.py
.venv-rename/bin/python - <<'PY'
import importlib
import energy_physics_pipeline
print("new import OK", energy_physics_pipeline.__name__)
try:
    importlib.import_module("energy_pipeline")
except ModuleNotFoundError:
    print("old import correctly absent")
else:
    raise SystemExit("FAIL: old import root energy_pipeline still imports")
PY
energy-physics --help
```

If `energy-physics` is not on PATH inside the shell, use:

```bash
.venv-rename/bin/energy-physics --help
```

Full-suite failures must be fixed, not waived. Do not downgrade tests to make the rename pass.

### Phase 10 - Local rename receipt

Create `RENAME-RECEIPT-YYYY-MM-DD.md` after the local verification passes.

It must include:

- boundary block;
- old and new names table;
- local commit SHA;
- verification commands and pass/fail summaries;
- old-name search summary;
- GitHub rename command used;
- remote head SHA;
- README blob SHA;
- `pyproject.toml` blob SHA;
- final visibility;
- explicit statement that enterprise H100 completion remains active/not complete.

## GitHub repository rename

Only after local code/doc rename and tests pass:

1. Commit local rename changes:

   ```bash
   git status --short
   git add -A
   git commit -m "Rename repo to Energy Physics Pipeline"
   ```

2. Push to current canonical remote:

   ```bash
   git push origin main
   ```

3. Rename GitHub repo without changing visibility. Use the GitHub API because it is explicit:

   ```bash
   gh api -X PATCH repos/Zer0pa/Energy -f name='Energy-Physics-Pipeline'
   ```

   If the repo is already renamed, verify and continue:

   ```bash
   gh repo view Zer0pa/Energy-Physics-Pipeline --json name,nameWithOwner,visibility,defaultBranchRef,url
   ```

4. Update local remote:

   ```bash
   git remote set-url origin https://github.com/Zer0pa/Energy-Physics-Pipeline.git
   git fetch origin --tags
   git status --short --branch
   ```

5. If the rename happened before the final receipt commit, push the receipt to the new remote:

   ```bash
   git push origin main
   ```

Do not change visibility. Verify visibility before and after.

## Remote verification

After the final push, re-read GitHub main:

```bash
gh repo view Zer0pa/Energy-Physics-Pipeline --json name,nameWithOwner,visibility,defaultBranchRef,url
gh api repos/Zer0pa/Energy-Physics-Pipeline/commits/main --jq '{sha: .sha, date: .commit.committer.date, message: .commit.message}'
gh api 'repos/Zer0pa/Energy-Physics-Pipeline/contents/README.md?ref=main' --jq '{sha: .sha, path: .path, size: .size}'
gh api 'repos/Zer0pa/Energy-Physics-Pipeline/contents/pyproject.toml?ref=main' --jq '{sha: .sha, path: .path, size: .size}'
```

Validate the remote README first-ten zones from GitHub, not local:

```bash
gh api 'repos/Zer0pa/Energy-Physics-Pipeline/contents/README.md?ref=main' --jq .content \
  | base64 --decode \
  | awk 'BEGIN{n=0} /^## /{n++; if(n<=10) print} END{print "HEADINGS", n}'
```

Validate remote Key Metrics and Proof Anchors counts:

```bash
gh api 'repos/Zer0pa/Energy-Physics-Pipeline/contents/README.md?ref=main' --jq .content \
  | base64 --decode \
  | awk 'BEGIN{s=0;c=0} /^## Key Metrics/{s=1; next} /^## Repo Identity/{s=0} s && /^\|/ && $0 !~ /^\| ---/{c++} END{print c-1}'

gh api 'repos/Zer0pa/Energy-Physics-Pipeline/contents/README.md?ref=main' --jq .content \
  | base64 --decode \
  | awk 'BEGIN{s=0;c=0} /^## Proof Anchors/{s=1; next} /^## Repo Shape/{s=0} s && /^\|/ && $0 !~ /^\| ---/{c++} END{print c-1}'
```

Every proof anchor must resolve remotely:

```bash
for p in RUNPOD-READINESS.md H100-ENTERPRISE-COMPLETION-PLAN.md FINAL-REPORT.md PRD.md tests/integration/test_runpod_same_endpoint.py sources_log/verification_summary.md; do
  gh api "repos/Zer0pa/Energy-Physics-Pipeline/contents/$p?ref=main" --jq '.path + " " + .sha'
done
```

## Required final state

Required local tree:

```text
energy_physics_pipeline/
tests/
scripts/
tools/
pyproject.toml
README.md
RENAME-RECEIPT-YYYY-MM-DD.md
```

Forbidden active tree:

```text
energy_pipeline/
energy_pipeline.egg-info/
```

Forbidden active imports:

```python
import energy_pipeline
from energy_pipeline...
```

Required active imports:

```python
import energy_physics_pipeline
from energy_physics_pipeline...
```

Required active CLI:

```bash
energy-physics --help
```

## Expected final answer from the executing agent

The final answer must be short and evidence-first:

- final repo URL;
- final GitHub head SHA;
- README blob SHA;
- `pyproject.toml` blob SHA;
- package import verification result;
- CLI verification result;
- full-suite verification summary;
- old-name search summary;
- any residual old-name mentions and why they are allowed;
- statement that visibility was unchanged;
- statement that enterprise H100 completion remains active/not complete.

Do not include a motivational summary. Do not claim completion unless the gates above passed.

## Failure handling

If blocked:

1. Do not rename visibility.
2. Do not leave a half-renamed Python package without a committed blocker report.
3. Create `RENAME-BLOCKED-REPORT.md`.
4. Include exact failing command, stderr, current git status, and next command.
5. Push the report if GitHub is reachable.
6. Final answer must say `BLOCKED`, not `done`.
