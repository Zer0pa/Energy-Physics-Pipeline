"""Contract tests: every line of sources_log/seed.jsonl parses as SourceManifest."""
import json
from pathlib import Path

import pytest

from energy_physics_pipeline.schemas.source import SourceManifest

pytestmark = pytest.mark.contract

SEED_PATH = Path(__file__).resolve().parents[2] / "sources_log" / "seed.jsonl"


def _load_raw_lines() -> list[dict]:
    assert SEED_PATH.exists(), f"sources_log/seed.jsonl not found at {SEED_PATH}"
    lines = []
    with SEED_PATH.open("r", encoding="utf-8") as fp:
        for lineno, raw in enumerate(fp, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                pytest.fail(f"Line {lineno}: invalid JSON — {exc}")
            lines.append(obj)
    return lines


_RAW_LINES = _load_raw_lines()


@pytest.mark.parametrize("record", _RAW_LINES, ids=[r.get("source_id", f"line-{i}") for i, r in enumerate(_RAW_LINES)])
def test_source_manifest_parses(record: dict) -> None:
    """Each JSONL record must parse as a valid SourceManifest without error."""
    manifest = SourceManifest.model_validate(record)
    assert manifest.source_id, "source_id must be non-empty"
    assert manifest.uri, "uri must be non-empty"
    assert manifest.checksum.startswith("sha256:"), "checksum must start with 'sha256:'"
    assert manifest.local_slice_size_mb >= 0, "local_slice_size_mb must be >= 0"


def test_minimum_entry_count() -> None:
    """seed.jsonl must contain at least 30 SourceManifest entries."""
    assert len(_RAW_LINES) >= 30, (
        f"Expected >= 30 source manifest entries, found {len(_RAW_LINES)}. "
        "Add more entries to sources_log/seed.jsonl."
    )


def test_source_ids_unique() -> None:
    """source_id values must be unique across all entries."""
    ids = [r.get("source_id") for r in _RAW_LINES]
    duplicates = [sid for sid in set(ids) if ids.count(sid) > 1]
    assert not duplicates, f"Duplicate source_id values found: {duplicates}"


def test_all_have_rights_notes() -> None:
    """Every entry must have a non-empty rights_notes field."""
    for record in _RAW_LINES:
        manifest = SourceManifest.model_validate(record)
        assert manifest.rights_notes.strip(), (
            f"source_id={manifest.source_id!r} has empty rights_notes"
        )


def test_all_have_citation() -> None:
    """Every entry must have a non-empty citation field."""
    for record in _RAW_LINES:
        manifest = SourceManifest.model_validate(record)
        assert manifest.citation.strip(), (
            f"source_id={manifest.source_id!r} has empty citation"
        )
