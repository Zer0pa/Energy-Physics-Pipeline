"""Inspect the local audit_log/audit.duckdb interactively.

Usage:
  .venv/bin/python tools/show_audit.py             # summary
  .venv/bin/python tools/show_audit.py --layer L4  # filter by layer
"""
from __future__ import annotations

import argparse

from energy_pipeline.audit import AuditWriter


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--layer", default=None)
    p.add_argument("--domain", default=None)
    p.add_argument("--gate-status", default=None)
    p.add_argument("--limit", type=int, default=20)
    args = p.parse_args()

    aw = AuditWriter()
    print(f"audit rows: {aw.count()}")
    where = []
    if args.layer:
        where.append(f"layer = '{args.layer}'")
    if args.domain:
        where.append(f"domain = '{args.domain}'")
    if args.gate_status:
        where.append(f"gate_status = '{args.gate_status}'")
    sql = "SELECT ts, layer, sub_vertical, domain, mode, license_class, gate_status, scientific_valid, envelope_id FROM audit_events"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY ts DESC LIMIT {args.limit}"
    rows = aw.query(sql)
    for r in rows:
        print(r)
    aw.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
