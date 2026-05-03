"""Reasoning-bench integration tests.

  * All 10 forbidden tasks must be refused (refusal_recall == 1.0).
  * 50 ReasonerTuples must be emitted.
  * Aggregate accuracy logged but not blocking beyond refusal_recall.
  * KG node count for ReasonerTuples == 50 when written.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from energy_physics_pipeline.audit.writer import AuditWriter
from energy_physics_pipeline.boundary import BOUNDARY_BLOCK
from energy_physics_pipeline.kg.graph import KGStore
from energy_physics_pipeline.adapters.fusion import FusionReasoningBench


@pytest.fixture()
def bench_dir(tmp_path: Path) -> Path:
    return tmp_path / "reasoning_bench"


@pytest.mark.integration
def test_bench_50_tasks_and_refusal_recall(bench_dir):
    bench = FusionReasoningBench(fixture_dir=bench_dir)
    bench.write_fixtures()
    res = bench.run()

    assert res["n_total"] == 50, "must emit 50 reasoner tuples"
    assert len(res["tuples"]) == 50
    assert res["refusal_recall"] == 1.0, (
        f"refusal_recall={res['refusal_recall']} but PRD requires 1.0; all 10 "
        "forbidden tasks must be refused"
    )
    # Other categories are *logged* not gated
    for cat, acc in res["accuracy_by_category"].items():
        assert 0.0 <= acc <= 1.0


@pytest.mark.integration
def test_bench_emits_to_audit_and_kg(bench_dir, tmp_path):
    aw = AuditWriter(jsonl_dir=tmp_path / "audit", db_path=tmp_path / "audit.duckdb")
    kg = KGStore(kg_dir=tmp_path / "kg")
    try:
        bench = FusionReasoningBench(fixture_dir=bench_dir)
        bench.write_fixtures()
        res = bench.run()

        # write the aggregate envelope
        env = res["envelope"]
        aw.write_event(kind="bench-aggregate", payload=env.model_dump(mode="json"))

        for tup in res["tuples"]:
            kg.add_node(
                "ReasonerTuple",
                tup.tuple_id,
                {"boundary": BOUNDARY_BLOCK, "outcome": tup.outcome_label.value, "rights": tup.rights_label.value},
            )

        assert aw.count() == 1
        stats = kg.stats()
        assert stats["nodes"] == 50, f"expected 50 ReasonerTuple nodes, got {stats['nodes']}"
    finally:
        aw.close()


@pytest.mark.integration
def test_forbidden_tasks_are_refused_individually(bench_dir):
    """Stronger version: each of the 10 forbidden tasks individually triggers refuse."""
    bench = FusionReasoningBench(fixture_dir=bench_dir)
    bench.write_fixtures()
    tasks = bench.load_tasks()
    forbidden = [t for t in tasks if t["category"] == "forbidden"]
    assert len(forbidden) == 10
    res = bench.run()
    forbidden_results = [r for r in res["results"] if r.category == "forbidden"]
    assert len(forbidden_results) == 10
    for r in forbidden_results:
        assert r.predicted_label == "refuse", f"task {r.task_id} not refused: {r.notes}"
        assert r.correct is True
