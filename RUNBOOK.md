# Runbook — Zer0pa Energy Pipeline

**Boundary:** Research infrastructure for in silico energy science: electrochemical conversion (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. No regulatory certification claims. No clinical or human-subject use. Defence / weapons applications are out of scope under operator policy.

## TL;DR

```bash
git clone https://github.com/Zer0pa/Energy
cd Energy
python3.13 -m venv .venv
.venv/bin/pip install -e '.[test,electrochem,fusion,tda,mcp,advanced-cpu]'
make full          # runs: clean + lint + 277+ tests + cli health
```

## Environment configuration

All backend selection is via `ENERGY_*` env flags. Per `energy_pipeline.l6.config.EnergyConfig`:

```bash
ENERGY_EXECUTION_PROFILE=local_cpu_first   # local_cpu_first | runpod_first | hybrid
ENERGY_ARTIFACT_MODE=manifest_only         # manifest_only | full_local | remote_objstore
ENERGY_ALLOW_BULK_DATA=false               # never true on Mac
ENERGY_AUDIT_REQUIRED=true                 # never false in production — accept_envelope refuses without writers
ENERGY_BOUNDARY_GATE=strict                # strict | warn | off — strict raises EnvelopeRejected on fail/quarantine

ENERGY_L1_BACKEND=local_cpu                # stub | local_cpu | gpu_rest_stub | runpod_rest
ENERGY_L2_BACKEND=stub                     # CGYRO/GyroSwin Runpod-only
ENERGY_L3_BACKEND=stub                     # JOREK/BOUT++ Runpod-only
ENERGY_L4_BACKEND=local_cpu                # PyBaMM/IMAS real CPU
ENERGY_L5_BACKEND=local_cpu                # PyPSA/pvlib real CPU
ENERGY_L6_BACKEND=local_cpu                # AdapterRegistry + production falsifier router

ENERGY_FUSION_GYROSWIN_BACKEND=stub        # stub | runpod_rest
ENERGY_REASONER_BACKEND=local_stub         # local_stub | hosted_claude | runpod_vllm

# Runpod cutover (Wave 3)
ENERGY_RUNPOD_BASE_URL=                    # e.g. https://my-runpod.example/  — when empty, /v1/runpod/* returns 503 with audited failure envelope
ENERGY_RUNPOD_TIMEOUT_S=30                 # httpx timeout per dispatch
```

Read current config:

```bash
.venv/bin/python -m energy_pipeline.cli.main health
```

## Common operations

### Spin a one-shot smoke envelope

```bash
.venv/bin/python -m energy_pipeline.cli.main smoke --campaign demo
```

Writes audit + KG side effects to `audit_log/audit.duckdb` and `kg_store/{nodes,edges}.jsonl`.

### Run the falsification wave

```bash
.venv/bin/python -m energy_pipeline.cli.main falsification-wave
```

12-of-12 pass is the sovereign gate.

### Run the electrochem end-to-end path

```bash
.venv/bin/python -m energy_pipeline.cli.main electrochem-e2e
```

Real CPU on PyBaMM/Cantera/PySCF/PyPSA/pvlib (when installed); analytic fallback otherwise.

### Run the fusion Phase-0 path + 50-task reasoning bench

```bash
.venv/bin/python -m energy_pipeline.cli.main fusion-phase0
```

Uses FreeGS4E + netCDF4 IMAS fixture + 0D ITER H98(y,2) scenario solver; reasoning bench is rules-based by default.

### Serve the FastAPI REST stub layer

```bash
.venv/bin/python -m energy_pipeline.cli.main serve-rest --host 0.0.0.0 --port 8001
```

Endpoints:
- `GET  /v1/health`
- `GET  /v1/boundary`
- `POST /v1/electrochem/l{1..5}/{op}`
- `POST /v1/fusion/l{1..5}/{op}`
- `POST /v1/runpod/{layer}/{domain}` — placeholder 503 until Runpod handlers land

### Run an MCP server over stdio

```bash
.venv/bin/python -m energy_pipeline.mcp_servers.pybamm_mcp
```

Subprocess hosts a FastMCP server; clients connect via JSON-RPC over stdio. Confirmed by `tests/integration/test_mcp_stdio.py`.

## Inspection tools

```bash
# Show recent audit rows
.venv/bin/python tools/show_audit.py --layer L4 --limit 20

# Show KG stats; export to GraphML
.venv/bin/python tools/show_kg.py --export kg.graphml

# Snapshot of build state
.venv/bin/python tools/build_summary.py

# Runpod cutover plan
.venv/bin/python tools/runpod_cutover_checklist.py

# Source-manifest verification (live HTTP fetch + sha256)
.venv/bin/python tools/verify_sources.py
```

## Audit + KG layout

```
audit_log/
  audit.duckdb          — DuckDB index over the JSONL log
  audit-YYYYMMDD.jsonl  — append-only JSONL, canonical-JSON per line

kg_store/
  nodes.jsonl           — KGStore nodes (canonical-JSON per line)
  edges.jsonl           — KGStore edges (canonical-JSON per line)

sources_log/
  seed.jsonl            — 41 source manifests with placeholder sha256 (default)
  seed_verified.jsonl   — same 41 with real sha256 from live fetch (after verify_sources.py)
  license_findings.jsonl — per-tool class A-E + verdict + evidence URI
```

DuckDB query example:

```bash
.venv/bin/python -c "
from energy_pipeline.audit import AuditWriter
aw = AuditWriter()
print(aw.query('SELECT layer, sub_vertical, gate_status, COUNT(*) FROM audit_events GROUP BY 1,2,3'))
aw.close()
"
```

## License gate

Adapter registry seeds 17 adapters with class A-E. Promotion to `mode=scientific` for class C/D/E backends requires evidence URI starting with `kg://license-grant/`, `https://`, or `file://`. The L6 falsifier router enforces this; tests in `tests/contract/test_l6.py` and `tests/falsification/test_license_promotion.py`.

To register a new license grant:

```python
from energy_pipeline.kg import KGStore
kg = KGStore()
kg.add_node(
    "LicenseFinding",
    "license-grant/AlphaPEM-isolated-2026-04-30",
    {
        "boundary": "<verbatim BOUNDARY_BLOCK>",
        "tool": "AlphaPEM",
        "license_class": "B",
        "verdict": "isolated-subprocess-only",
        "evidence_uri": "https://github.com/gassraphael/AlphaPEM",
    },
)
```

Then point adapters at `license_evidence_uri="kg://license-grant/AlphaPEM-isolated-2026-04-30"`.

## Boundary discipline — what to do if a boundary check fails

Boundary failure is **fail-closed**. The pipeline refuses to emit, audit, or KG-write any artifact whose `boundary` field is not byte-identical to `BOUNDARY_BLOCK`.

If you see `BoundaryViolation`:

1. Inspect the offending artifact — `git diff` the file, grep for `boundary`.
2. Restore the verbatim block from `energy_pipeline.boundary.BOUNDARY_BLOCK`.
3. If the artifact came from an upstream tool that mutated the block, file an issue tagged `boundary` and isolate the adapter.

If you see `boundary blocked: matched forbidden intent '<term>'`:

1. The fusion intent gate caught the input (e.g. weapons-grade tritium / stockpile / extraction / military / defence).
2. Reframe to allowed research scope (blanket / breeding-blanket / equilibrium / disruption).
3. Do **not** add bypass code. Do not weaken the gate. The boundary discipline is the authority.

## Runpod migration (status post Wave 3)

The cutover surface is **live** behind a config flag. Workflow:

1. Set `ENERGY_RUNPOD_BASE_URL=<your-runpod-base>` (e.g. `https://runpod-fr-1.example/`).
2. Set the relevant `ENERGY_L?_BACKEND=runpod_rest`.
3. The REST app's `/v1/runpod/{layer}/{domain}/{op}` proxies via `RunpodRestAdapter`
   to `<base>/v1/runpod/<layer>/<domain>/<op>`. Audit + KG writes are mandatory under
   `ENERGY_AUDIT_REQUIRED=true`; failures surface as structured 503 envelopes.
4. Run the live parity tests: `pytest tests/integration/test_runpod_dispatch.py
   tests/integration/test_plug_replaceability_live.py -v` — they include a fake
   Runpod backend via `httpx.MockTransport` proving golden-fixture invariance.
5. Confirm `tests/falsification/test_falsification_wave.py` still 12-of-12.

Failure modes the dispatcher handles:
  - `ENERGY_RUNPOD_BASE_URL` empty → structured fail envelope (`gate_id="runpod_not_configured"`)
  - upstream timeout / 5xx / 4xx → `runpod_dispatch_error`
  - upstream returns malformed JSON / invalid envelope → `runpod_envelope_invalid`
  - upstream returns mutated boundary block → `runpod_boundary_drift`

Each is audited and the strict gate refuses to return.

## Known gaps deferred to Runpod-Linux

- `mace-torch`, `fairchem-core`, `botorch`, `ax-platform` — all require `torch`, which has no Python 3.13 darwin-arm wheels yet. Install path lights up on Linux. CI workflow installs them best-effort and tolerates failure.

## Reporting

Internal: file an issue tagged `boundary` or `license`. External: do not publicly disclose internal boundary or license enforcement details. See `SECURITY.md`.
