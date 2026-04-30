#!/usr/bin/env bash
# Clears local runtime side effects (audit_log, kg_store, caches) so the repo state
# committed to git stays minimal.
set -euo pipefail

cd "$(dirname "$0")/.."

rm -rf audit_log kg_store .pytest_cache .ruff_cache .mypy_cache htmlcov
mkdir -p audit_log kg_store
touch audit_log/.keep kg_store/.keep
echo "Runtime cleaned."
