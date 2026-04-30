"""Introspect the repo and print a build summary suitable for the final report.

Walks the repo looking for:
- adapter modules (CPU vs stub)
- fixture counts
- test counts (without actually running)
- registered MCP tools
- source manifests + license findings
- KG/audit row counts (live)

No external imports beyond stdlib + project modules.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("rb") as f:
        return sum(1 for _ in f)


def list_modules(dirpath: Path) -> list[str]:
    if not dirpath.exists():
        return []
    return sorted(p.stem for p in dirpath.glob("*.py") if p.stem != "__init__")


def count_tests(testdir: Path) -> int:
    """Approximate: count `def test_` occurrences."""
    if not testdir.exists():
        return 0
    n = 0
    for p in testdir.rglob("test_*.py"):
        with p.open() as f:
            for line in f:
                if line.lstrip().startswith("def test_"):
                    n += 1
    return n


def main() -> int:
    print("# Build summary")
    print()

    # Adapters
    ec_dir = ROOT / "energy_pipeline" / "adapters" / "electrochem"
    fu_dir = ROOT / "energy_pipeline" / "adapters" / "fusion"
    sh_dir = ROOT / "energy_pipeline" / "adapters" / "shared"
    print("## Adapters")
    print(f"- Electrochem modules: {list_modules(ec_dir)}")
    print(f"- Fusion modules: {list_modules(fu_dir)}")
    print(f"- Shared modules: {list_modules(sh_dir)}")
    print()

    # MCP servers
    mcp_dir = ROOT / "energy_pipeline" / "mcp_servers"
    print("## MCP servers")
    print(f"- Modules: {list_modules(mcp_dir)}")
    print()

    # TDA
    tda_dir = ROOT / "energy_pipeline" / "tda"
    print("## TDA")
    print(f"- Modules: {list_modules(tda_dir)}")
    print()

    # Fixtures
    print("## Fixtures")
    for sub in ("electrochem", "fusion", "negative"):
        d = ROOT / "fixtures" / sub
        n_json = len(list(d.glob("*.json"))) if d.exists() else 0
        n_yaml = len(list(d.glob("*.yaml"))) if d.exists() else 0
        n_nc = len(list(d.glob("*.nc"))) if d.exists() else 0
        rb_dir = d / "reasoning_bench"
        n_rb = len(list(rb_dir.glob("*.json"))) if rb_dir.exists() else 0
        print(f"- {sub}: json={n_json} yaml={n_yaml} nc={n_nc} reasoning_bench={n_rb}")
    print()

    # Tests
    print("## Tests")
    for sub in ("contract", "falsification", "scientific", "integration"):
        d = ROOT / "tests" / sub
        print(f"- tests/{sub}: ~{count_tests(d)} test functions")
    print()

    # Source manifests
    sl = ROOT / "sources_log"
    print("## Source manifests + license findings")
    print(f"- seed.jsonl: {count_lines(sl/'seed.jsonl')} entries")
    print(f"- license_findings.jsonl: {count_lines(sl/'license_findings.jsonl')} entries")
    print()

    # Decision log
    dd = ROOT / "docs" / "decisions"
    print("## Decision docs")
    if dd.exists():
        for p in sorted(dd.glob("*.md")):
            print(f"- {p.name}")
    print()

    # Live audit / KG (best-effort)
    try:
        from energy_pipeline.audit import AuditWriter
        from energy_pipeline.kg import KGStore

        aw = AuditWriter()
        kg = KGStore()
        print("## Live runtime")
        print(f"- audit rows: {aw.count()}")
        print(f"- kg nodes: {kg.stats()['nodes']}")
        print(f"- kg edges: {kg.stats()['edges']}")
        aw.close()
    except Exception as exc:
        print(f"## Live runtime: error introspecting ({exc!r})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
