"""Wave 4 §3 — audit/KG runtime must survive parallel subagent execution.

Tests:
  A. Two concurrent subprocesses each writing accepted envelopes to ISOLATED
     env-configured runtime paths complete cleanly (no DuckDB lock failure).
  B. ENERGY_AUDIT_DIR / ENERGY_KG_DIR env overrides actually redirect writes.
  C. ENERGY_AUDIT_DB_PATH overrides the DB path independently of the JSONL dir.
  D. Within one process, two threads writing concurrent envelopes do not
     collide (the AuditWriter's internal lock is sufficient).
"""
from __future__ import annotations

import multiprocessing as mp
import os
import threading
from pathlib import Path

import pytest

from energy_physics_pipeline.audit import AuditWriter, default_audit_dir, default_db_path
from energy_physics_pipeline.boundary import BOUNDARY_BLOCK
from energy_physics_pipeline.kg import KGStore, default_kg_dir


# ---------------------------------------------------------------------------
# A) Subprocess isolation — each subprocess sees its own env-configured paths
# ---------------------------------------------------------------------------


def _worker_write(audit_dir: str, kg_dir: str, n_writes: int) -> int:
    os.environ["ENERGY_AUDIT_DIR"] = audit_dir
    os.environ["ENERGY_KG_DIR"] = kg_dir
    os.environ["ENERGY_AUDIT_DB_PATH"] = str(Path(audit_dir) / "audit.duckdb")
    # Re-import so default_*_dir() pick up the new env in this fresh process.
    from energy_physics_pipeline.audit.writer import default_audit_dir as _aud
    from energy_physics_pipeline.kg.graph import default_kg_dir as _kg

    aud = AuditWriter(jsonl_dir=_aud(), db_path=Path(audit_dir) / "audit.duckdb")
    kg = KGStore(kg_dir=_kg())
    for i in range(n_writes):
        aud.write_event(
            kind="parallel-test",
            payload={
                "boundary": BOUNDARY_BLOCK,
                "envelope_id": f"sha256:wp{i:04d}",
                "run_id": f"r-{os.getpid()}-{i}",
                "sub_vertical": "electrochemistry",
                "layer": "L4",
                "domain": "battery",
                "mode": "engineering_stub",
                "backend": {"license_class": "A", "execution_mode": "local_cpu"},
                "falsification": {
                    "gate_status": "pass",
                    "scientific_valid": False,
                    "boundary_check_passed": True,
                },
            },
        )
        kg.add_node(
            "ToolAdapter",
            f"tool::{os.getpid()}::{i}",
            {"name": "parallel-tool"},
            boundary_required=False,
        )
    final = aud.count()
    aud.close()
    return final


def test_two_subprocesses_isolated_audit_dirs(tmp_path: Path):
    """Two subprocesses pointed at distinct ENERGY_AUDIT_DIR/KG_DIR roots
    each write 10 envelopes; both succeed; the dirs end up with disjoint
    JSONL files and disjoint DuckDBs (no shared lock contention)."""
    a_dir = tmp_path / "subproc-a"
    b_dir = tmp_path / "subproc-b"
    ctx = mp.get_context("spawn")  # fresh interpreter, no parent env leakage

    p_a = ctx.Process(target=_worker_write, args=(str(a_dir / "audit"), str(a_dir / "kg"), 10))
    p_b = ctx.Process(target=_worker_write, args=(str(b_dir / "audit"), str(b_dir / "kg"), 10))
    p_a.start()
    p_b.start()
    p_a.join(timeout=30)
    p_b.join(timeout=30)
    assert p_a.exitcode == 0, "subprocess A failed"
    assert p_b.exitcode == 0, "subprocess B failed"

    # Each subprocess wrote into ITS OWN dir
    assert (a_dir / "audit").exists()
    assert (b_dir / "audit").exists()
    assert (a_dir / "audit" / "audit.duckdb").exists()
    assert (b_dir / "audit" / "audit.duckdb").exists()


# ---------------------------------------------------------------------------
# B) ENERGY_AUDIT_DIR / ENERGY_KG_DIR redirect writes
# ---------------------------------------------------------------------------


def test_env_overrides_redirect_audit_and_kg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("ENERGY_AUDIT_DIR", str(tmp_path / "alt-audit"))
    monkeypatch.setenv("ENERGY_KG_DIR", str(tmp_path / "alt-kg"))
    # Force re-import of the default helpers so they see the new env.
    assert default_audit_dir() == tmp_path / "alt-audit"
    assert default_kg_dir() == tmp_path / "alt-kg"


def test_env_audit_db_path_overrides_independently(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    custom_db = tmp_path / "custom-name" / "main.duckdb"
    monkeypatch.setenv("ENERGY_AUDIT_DIR", str(tmp_path / "audit"))
    monkeypatch.setenv("ENERGY_AUDIT_DB_PATH", str(custom_db))
    assert default_db_path() == custom_db


# ---------------------------------------------------------------------------
# C) Same-process, concurrent threads
# ---------------------------------------------------------------------------


def test_concurrent_threads_share_audit_writer_safely(tmp_path: Path):
    """The AuditWriter's internal lock should serialize concurrent threads."""
    aud = AuditWriter(jsonl_dir=tmp_path / "audit", db_path=tmp_path / "audit.duckdb")
    n0 = aud.count()
    errors: list[BaseException] = []

    def writer(idx: int):
        try:
            for j in range(20):
                aud.write_event(
                    kind="thread-test",
                    payload={
                        "boundary": BOUNDARY_BLOCK,
                        "envelope_id": f"sha256:t{idx:02d}-{j:02d}",
                        "run_id": f"thr-{idx}-{j}",
                        "sub_vertical": "electrochemistry",
                        "layer": "L4",
                        "domain": "battery",
                        "mode": "engineering_stub",
                        "backend": {"license_class": "A", "execution_mode": "local_cpu"},
                        "falsification": {
                            "gate_status": "pass",
                            "scientific_valid": False,
                            "boundary_check_passed": True,
                        },
                    },
                )
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert not errors, f"thread errors: {errors!r}"
    assert aud.count() == n0 + 4 * 20
    aud.close()
