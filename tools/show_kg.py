"""Inspect the local kg_store and export GraphML.

Usage:
  .venv/bin/python tools/show_kg.py                   # summary
  .venv/bin/python tools/show_kg.py --export kg.graphml
"""
from __future__ import annotations

import argparse
from pathlib import Path

from energy_pipeline.kg import KGStore


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--export", help="path to write GraphML")
    args = p.parse_args()
    kg = KGStore()
    s = kg.stats()
    print(f"nodes: {s['nodes']}, edges: {s['edges']}")
    if args.export:
        out = kg.export_graphml(Path(args.export))
        print(f"GraphML written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
