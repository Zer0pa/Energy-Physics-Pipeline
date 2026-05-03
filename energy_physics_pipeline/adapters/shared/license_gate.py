"""License gate — verdict resolver and promotion guard.

Reads sources_log/license_findings.jsonl and exposes:

  license_verdict(tool)            -> dict with class, spdx, verdict, etc.
  assert_promotion_allowed(tool, target_mode, evidence_uri)
                                   -> raises LicenseGateError for Class C/D/E
                                      promoted to "scientific" without evidence.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal


class LicenseGateError(ValueError):
    """Raised when a Class C/D/E tool is promoted to scientific mode without evidence."""


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_findings_path() -> Path:
    return _project_root() / "sources_log" / "license_findings.jsonl"


def _load_findings(path: Path | None = None) -> dict[str, dict]:
    """Load license_findings.jsonl into a dict keyed by tool name (case-insensitive)."""
    fpath = Path(path) if path is not None else _default_findings_path()
    findings: dict[str, dict] = {}
    if not fpath.exists():
        return findings
    with fpath.open("r", encoding="utf-8") as fp:
        for raw in fp:
            raw = raw.strip()
            if not raw:
                continue
            record = json.loads(raw)
            key = record.get("tool", "").lower()
            if key:
                findings[key] = record
    return findings


def license_verdict(tool: str, *, findings_path: Path | None = None) -> dict:
    """Return the license finding record for *tool*.

    Performs a case-insensitive lookup.  Returns an empty dict if the tool
    is not found in license_findings.jsonl.

    Args:
        tool: Tool name as it appears in license_findings.jsonl.
        findings_path: Override path (defaults to sources_log/license_findings.jsonl).

    Returns:
        Mapping with keys: tool, license_class, spdx, verdict,
        promotion_to_scientific, evidence_uri, and optional notes.
    """
    findings = _load_findings(findings_path)
    return findings.get(tool.lower(), {})


_RESTRICTED_CLASSES = {"B", "C", "D", "E"}

_VALID_EVIDENCE_PREFIXES = ("file://", "https://", "kg://license-grant/")


def assert_promotion_allowed(
    tool: str,
    target_mode: Literal["scientific", "engineering_stub"],
    evidence_uri: str | None,
    *,
    findings_path: Path | None = None,
) -> None:
    """Assert that *tool* may be promoted to *target_mode*.

    For ``target_mode="engineering_stub"`` this always passes.

    For ``target_mode="scientific"``:
    - Class A tools pass unconditionally.
    - Class B/C/D/E tools require *evidence_uri* to start with one of
      ``file://``, ``https://``, or ``kg://license-grant/``; otherwise
      raises :exc:`LicenseGateError`.
    - Tools not present in license_findings.jsonl are treated as Class E
      (unknown → blocked).

    Args:
        tool: Tool name.
        target_mode: Promotion target (``"scientific"`` or ``"engineering_stub"``).
        evidence_uri: License grant evidence URI, or None.
        findings_path: Optional override for the findings file path.

    Raises:
        LicenseGateError: When promotion is not allowed.
    """
    if target_mode != "scientific":
        return

    findings = _load_findings(findings_path)
    record = findings.get(tool.lower())

    if record is None:
        raise LicenseGateError(
            f"Tool '{tool}' not found in license_findings.jsonl. "
            "Treat as Class E — promotion to scientific mode requires explicit license grant."
        )

    lc = record.get("license_class", "E")

    if lc not in _RESTRICTED_CLASSES:
        # Class A or B — no restriction on scientific promotion for this gate
        # (Class B still requires isolation at deploy time, but the gate here
        # is for the evidence URI requirement on C/D/E).
        return

    # Class C, D, or E — evidence URI is mandatory.
    if evidence_uri and any(evidence_uri.startswith(prefix) for prefix in _VALID_EVIDENCE_PREFIXES):
        return

    raise LicenseGateError(
        f"Tool '{tool}' has license_class={lc} and cannot be promoted to scientific mode "
        "without a valid license grant evidence URI (file://, https://, or kg://license-grant/). "
        f"Provided evidence_uri={evidence_uri!r}. "
        "Add a grant record to kg://license-grant/ or supply a valid https:// evidence link."
    )
