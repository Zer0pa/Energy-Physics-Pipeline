"""SourceLog — JSONL-backed read/write/query helper for SourceManifest records.

Backed by sources_log/seed.jsonl (relative to the project root).
All writes append to that file; reads load from it fresh.
Validates every entry against the SourceManifest Pydantic model.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Callable

from energy_pipeline.schemas.source import SourceManifest


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_path() -> Path:
    return _project_root() / "sources_log" / "seed.jsonl"


class SourceLog:
    """Append-only JSONL store for SourceManifest records.

    Args:
        path: Explicit JSONL file path. Defaults to sources_log/seed.jsonl
              relative to the project root.
    """

    def __init__(self, path: Path | str | None = None) -> None:
        self._path = Path(path) if path is not None else _default_path()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def add(self, manifest: SourceManifest) -> None:
        """Append *manifest* to the backing JSONL file.

        Validates the manifest against the SourceManifest schema before writing.
        Raises ``pydantic.ValidationError`` if validation fails.
        """
        # Round-trip validation (also catches extra fields on subclasses).
        validated = SourceManifest.model_validate(manifest.model_dump(mode="json"))
        line = validated.model_dump_json() + "\n"
        with self._lock:
            with self._path.open("a", encoding="utf-8") as fp:
                fp.write(line)

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def _iter_manifests(self) -> list[SourceManifest]:
        """Return all manifests from the backing file, skipping blank lines."""
        if not self._path.exists():
            return []
        results: list[SourceManifest] = []
        with self._path.open("r", encoding="utf-8") as fp:
            for raw in fp:
                raw = raw.strip()
                if not raw:
                    continue
                obj = json.loads(raw)
                results.append(SourceManifest.model_validate(obj))
        return results

    def all(self) -> list[SourceManifest]:
        """Return all SourceManifest records."""
        return self._iter_manifests()

    def find_by_id(self, source_id: str) -> SourceManifest | None:
        """Return the first manifest whose ``source_id`` matches, or None."""
        for m in self._iter_manifests():
            if m.source_id == source_id:
                return m
        return None

    def find_by_uri(self, uri: str) -> SourceManifest | None:
        """Return the first manifest whose ``uri`` matches exactly, or None."""
        for m in self._iter_manifests():
            if m.uri == uri:
                return m
        return None

    def query_by_license(self, spdx: str) -> list[SourceManifest]:
        """Return all manifests whose ``license_spdx_or_text`` equals *spdx*."""
        return [m for m in self._iter_manifests() if m.license_spdx_or_text == spdx]

    def query(self, predicate: Callable[[SourceManifest], bool]) -> list[SourceManifest]:
        """Return all manifests for which *predicate* returns True."""
        return [m for m in self._iter_manifests() if predicate(m)]

    def count(self) -> int:
        """Return the number of valid manifest records in the backing file."""
        return len(self._iter_manifests())
