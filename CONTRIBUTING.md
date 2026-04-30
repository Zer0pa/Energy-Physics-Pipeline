# Contributing — Zer0pa Energy

Boundary: research infrastructure for in silico energy science. No regulatory, clinical,
human-subject, defence, or weapons applications. See `BOUNDARY.md`.

## Dev environment

```bash
python3.13 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/pip install -e '.[electrochem]'   # optional heavy
.venv/bin/pip install -e '.[fusion]'        # optional heavy
.venv/bin/pip install -e '.[tda]'
```

Heavy adapters (PyBaMM, PyPSA, Solcore, Cantera, OpenMC, FreeGS) install lazily; the
adapter modules degrade to deterministic CPU fixtures if a library is unavailable.

## Discipline

1. **Boundary first.** Every artifact (envelope, DRO, source manifest, KG node,
   REST response, MCP tool description) carries `BOUNDARY_BLOCK` verbatim. Mutation
   is a fail-closed condition.
2. **No bulk datasets vendored.** Manifests + small synthetic fixtures only.
3. **Stubs cannot claim scientific validity.** `mode=engineering_stub` with
   `scientific_valid=True` is a validator failure.
4. **Class C/D/E backends gated.** Promotion to `scientific` mode requires a
   `kg://license-grant/...` or `https://` or `file://` evidence URI.
5. **Cross-model disagreement is a first-class quantity.** Never average a
   failed disagreement away.
6. **Within-Energy sharing only.** Electrochemistry and fusion share L6 + the L4
   `DeviceResponseObject`. Across Energy / Health / Materials, no substrate
   sharing — even where conceptually identical.

## Testing

```bash
./scripts/full_check.sh
```

Or piecewise:

```bash
.venv/bin/python -m pytest tests/contract -v
.venv/bin/python -m pytest tests/falsification -v
.venv/bin/python -m pytest tests/scientific -v
.venv/bin/python -m pytest tests/integration -v
```

## File ownership during overnight build

- `energy_pipeline/{schemas,audit,kg,rest,l6,boundary.py,cli}` — chief engineer.
- `energy_pipeline/adapters/electrochem/*` — electrochem subagent.
- `energy_pipeline/adapters/fusion/*` — fusion subagent.
- `energy_pipeline/adapters/shared/*` — sources/reasoner subagent.
- `energy_pipeline/mcp_servers/*` — MCP subagent.
- `energy_pipeline/tda/*` — TDA subagent.
- Tests partitioned by directory; each subagent owns its named files.
