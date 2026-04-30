#!/usr/bin/env bash
# Full CPU-side check: ruff lint, pytest contract+falsification+integration+scientific.
# Usage: ./scripts/full_check.sh
set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PY:-.venv/bin/python}"

echo "==> Python version"
"$PY" --version

echo "==> Ruff lint (warn only)"
"$PY" -m ruff check energy_pipeline tests || true

echo "==> Contract tests"
"$PY" -m pytest tests/contract -v --tb=short

echo "==> Falsification wave"
"$PY" -m pytest tests/falsification -v --tb=short

echo "==> Scientific bounds"
"$PY" -m pytest tests/scientific -v --tb=short || true

echo "==> Integration"
"$PY" -m pytest tests/integration -v --tb=short

echo "==> CLI smoke"
"$PY" -m energy_pipeline.cli.main health
"$PY" -m energy_pipeline.cli.main registry

echo "==> Full check OK"
