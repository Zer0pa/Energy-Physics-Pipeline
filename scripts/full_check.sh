#!/usr/bin/env bash
# Strict CPU-side check. Used as the sovereign gate before claiming Runpod readiness.
#
# - Boundary smoke is a hard gate.
# - Ruff is a hard gate.
# - Every pytest layer (contract, falsification, scientific, integration) is a hard gate.
# - CLI health + registry are hard gates.
# - Source verification (offline shape check) is a hard gate; live URL fetch is the
#   `verify_sources.py` script and is NOT run from this gate (network hygiene).
#
# Anything that uses `|| true` in this script is a bug — open an issue tagged `gate`.
#
# Usage:
#   bash scripts/full_check.sh             # strict (default)
#   STRICT=0 bash scripts/full_check.sh    # legacy permissive (warns only) — emergency only
set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PY:-.venv/bin/python}"
STRICT="${STRICT:-1}"

echo "==> Python version"
"$PY" --version

echo "==> Boundary smoke"
"$PY" -c "from energy_pipeline.boundary import BOUNDARY_BLOCK; assert len(BOUNDARY_BLOCK) == 386, f'BOUNDARY_BLOCK length drift: {len(BOUNDARY_BLOCK)}'; print('boundary OK,', len(BOUNDARY_BLOCK), 'bytes')"

echo "==> Ruff (strict)"
"$PY" -m ruff check energy_pipeline tests

echo "==> Contract tests"
"$PY" -m pytest tests/contract -q

echo "==> Falsification wave"
"$PY" -m pytest tests/falsification -q

echo "==> Scientific bounds (HARD GATE — no || true)"
"$PY" -m pytest tests/scientific -q

echo "==> Integration"
"$PY" -m pytest tests/integration -q

echo "==> CLI smoke"
"$PY" -m energy_pipeline.cli.main health > /dev/null
"$PY" -m energy_pipeline.cli.main registry > /dev/null
"$PY" -m energy_pipeline.cli.main smoke --no-write-audit > /dev/null

echo "==> Source-manifest schema check (offline)"
"$PY" -m pytest tests/contract/test_source_manifest_shape.py -q

echo "==> Coverage (warn-only at 80% soft gate)"
bash scripts/clean_runtime.sh > /dev/null
"$PY" -m pytest tests --cov=energy_pipeline --cov-report=term --cov-fail-under=70 -q

echo
echo "STRICT FULL CHECK OK"
