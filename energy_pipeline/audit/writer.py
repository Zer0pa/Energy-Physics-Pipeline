"""Audit writer — JSONL + DuckDB. Every artifact passes a boundary check before write."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import duckdb

from energy_pipeline.boundary import BoundaryViolation, verify_boundary
from energy_pipeline.schemas.canonical import canonical_json, sha256_of


_LOCK = threading.RLock()


def _project_root() -> Path:
    here = Path(__file__).resolve()
    # energy_pipeline/audit/writer.py -> repo root is parents[2]
    return here.parents[2]


def default_audit_dir() -> Path:
    """Audit JSONL directory. Reads `ENERGY_AUDIT_DIR` env to enable parallel-safe
    runtime per worktree/subagent (Wave 4 §3)."""
    import os as _os

    override = _os.environ.get("ENERGY_AUDIT_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return _project_root() / "audit_log"


def default_db_path() -> Path:
    """DuckDB index path. Reads `ENERGY_AUDIT_DB_PATH` first, then falls back to
    `<ENERGY_AUDIT_DIR>/audit.duckdb`."""
    import os as _os

    override = _os.environ.get("ENERGY_AUDIT_DB_PATH", "").strip()
    if override:
        return Path(override).expanduser()
    return default_audit_dir() / "audit.duckdb"


class AuditWriter:
    """Append-only JSONL + DuckDB index. Thread-safe within a process.

    JSONL is the canonical form; DuckDB is a queryable index over it.
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS audit_events (
        ts TIMESTAMP,
        kind VARCHAR,
        envelope_id VARCHAR,
        run_id VARCHAR,
        sub_vertical VARCHAR,
        layer VARCHAR,
        domain VARCHAR,
        mode VARCHAR,
        license_class VARCHAR,
        execution_mode VARCHAR,
        gate_status VARCHAR,
        scientific_valid BOOLEAN,
        boundary_check_passed BOOLEAN,
        payload_sha256 VARCHAR,
        payload JSON
    );
    CREATE INDEX IF NOT EXISTS idx_envelope_id ON audit_events(envelope_id);
    CREATE INDEX IF NOT EXISTS idx_run_id ON audit_events(run_id);
    CREATE INDEX IF NOT EXISTS idx_layer ON audit_events(layer);
    CREATE INDEX IF NOT EXISTS idx_domain ON audit_events(domain);
    CREATE INDEX IF NOT EXISTS idx_kind ON audit_events(kind);
    """

    def __init__(self, jsonl_dir: Path | None = None, db_path: Path | None = None) -> None:
        self.jsonl_dir = Path(jsonl_dir or default_audit_dir())
        self.jsonl_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(db_path or default_db_path())
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._con = duckdb.connect(str(self.db_path))
        for stmt in self.SCHEMA.strip().split(";"):
            s = stmt.strip()
            if s:
                self._con.execute(s)

    def close(self) -> None:
        try:
            self._con.close()
        except Exception:
            pass

    def __enter__(self) -> "AuditWriter":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    @staticmethod
    def _today_jsonl(jsonl_dir: Path) -> Path:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d")
        return jsonl_dir / f"audit-{ts}.jsonl"

    def write_event(self, kind: str, payload: Mapping[str, Any]) -> str:
        """Append one audit event. payload must contain the boundary block.

        Returns the sha256 of the canonical JSON of the payload.
        """
        if not verify_boundary(payload):
            raise BoundaryViolation(f"audit refused: boundary check failed for kind={kind}")
        sha = sha256_of(payload)
        envelope_id = payload.get("envelope_id") or payload.get("dro_id") or sha
        run_id = str(payload.get("run_id", ""))
        sub_vertical = str(payload.get("sub_vertical", ""))
        layer = str(payload.get("layer", ""))
        domain = str(payload.get("domain", ""))
        mode = str(payload.get("mode", ""))
        backend = payload.get("backend", {}) or {}
        license_class = str(backend.get("license_class", ""))
        execution_mode = str(backend.get("execution_mode", ""))
        falsification = payload.get("falsification", {}) or {}
        gate_status = str(falsification.get("gate_status", ""))
        scientific_valid = bool(falsification.get("scientific_valid", False))
        boundary_check_passed = bool(falsification.get("boundary_check_passed", True))
        ts = datetime.now(timezone.utc)
        line = canonical_json({"_ts": ts.isoformat(), "_kind": kind, **payload})
        with _LOCK:
            target = self._today_jsonl(self.jsonl_dir)
            with target.open("ab") as fp:
                fp.write(line)
                fp.write(b"\n")
            self._con.execute(
                """
                INSERT INTO audit_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    ts,
                    kind,
                    str(envelope_id),
                    run_id,
                    sub_vertical,
                    layer,
                    domain,
                    mode,
                    license_class,
                    execution_mode,
                    gate_status,
                    scientific_valid,
                    boundary_check_passed,
                    sha,
                    json.dumps(payload, default=str),
                ],
            )
        return sha

    def query(self, sql: str) -> list[tuple[Any, ...]]:
        with _LOCK:
            return self._con.execute(sql).fetchall()

    def count(self) -> int:
        with _LOCK:
            (n,) = self._con.execute("SELECT COUNT(*) FROM audit_events").fetchone()
            return int(n)


def write_envelope_event(writer: AuditWriter, envelope: Any) -> str:
    """Convenience: dump a Pydantic model to dict and write."""
    payload = envelope.model_dump(mode="json") if hasattr(envelope, "model_dump") else dict(envelope)
    kind = payload.get("schema_version", "envelope")
    return writer.write_event(kind=kind, payload=payload)
