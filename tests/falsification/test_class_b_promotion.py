"""Class B promotion gate tests — per CPU hardening §5.

ADR-001 says GPL Class B requires isolation/grant evidence before scientific or
product promotion. The schema-level validator only catches Class C/D/E. This
test set proves the production `gpl_isolation_falsifier` catches:

  - GPL tools (AlphaPEM, LBPM, etc.) escalated to scientific mode without evidence.
  - Llama-family conditional licenses without evidence.

And does NOT block:

  - LGPL tools (e.g. FreeGS, OMAS) — dynamic linking is allowed.
  - Class A tools (e.g. PyBaMM, OpenMC) — no gate.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from energy_pipeline.l6 import (
    apply_default_falsifiers,
    gpl_isolation_falsifier,
)
from energy_pipeline.schemas import (
    BackendBlock,
    Domain,
    ExecutionMode,
    GateStatus,
    LayerLevel,
    LicenseClass,
    Mode,
    SubVertical,
    UniversalLayerEnvelope,
)
from energy_pipeline.schemas.envelope import (
    FalsificationBlock,
    IOBlock,
    ProvenanceBlock,
)


def _envelope(
    *,
    tool: str,
    license_class: LicenseClass,
    license_evidence_uri: str,
    mode: Mode = Mode.scientific,
) -> UniversalLayerEnvelope:
    return UniversalLayerEnvelope(
        campaign_id="class-b-test",
        sub_vertical=SubVertical.electrochemistry,
        layer=LayerLevel.L4,
        domain=Domain.battery,
        mode=mode,
        backend=BackendBlock(
            adapter=f"adapter::{tool}",
            tool=tool,
            tool_version="1.0",
            execution_mode=ExecutionMode.local_cpu,
            license_class=license_class,
            license_evidence_uri=license_evidence_uri,
        ),
        outputs=IOBlock(payload={"quantities": {"x": {"value": 1.0, "unit": "V"}}}),
        falsification=FalsificationBlock(
            gate_status=GateStatus.pass_,
            scientific_valid=True,
            unit_check_passed=True,
            conservation_check_passed=True,
            boundary_check_passed=True,
        ),
        provenance=ProvenanceBlock(
            agent_id="t",
            model_id="t",
            git_sha="t",
            input_hash="0" * 64,
            output_hash="0" * 64,
            config_hash="0" * 64,
        ),
    )


# ---------------------------------------------------------------------------
# GPL tools (Class B, copyleft) — must be blocked from scientific without evidence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tool",
    [
        "AlphaPEM",  # GPL-3
        "LBPM",  # GPL-3
        "MOOSE",  # LGPL but listed as requiring isolation evidence
        "MOOSE+RACCOON",
        "LAMMPS",  # GPL-2
        "CP2K",  # GPL-2
        "GPAW",  # GPL-3
        "DeepSeek-R1-Distill-Llama-70B",  # Llama-conditional
    ],
)
def test_gpl_or_conditional_tool_in_scientific_without_evidence_is_blocked(tool: str):
    env = _envelope(tool=tool, license_class=LicenseClass.B, license_evidence_uri="")
    failures = gpl_isolation_falsifier(env)
    assert failures is not None and len(failures) >= 1
    assert any(f.gate_id == "gpl_isolation_required" for f in failures)


@pytest.mark.parametrize(
    "tool,evidence",
    [
        ("AlphaPEM", "kg://license-grant/AlphaPEM-isolated-2026-04-30"),
        ("LBPM", "kg://license-grant/LBPM-subprocess-isolated-v1"),
        ("LAMMPS", "file:///etc/zer0pa/license-grants/LAMMPS.txt"),
        ("CP2K", "file:///etc/zer0pa/license-grants/CP2K-2026-04-30.json"),
    ],
)
def test_gpl_tool_with_explicit_evidence_passes(tool: str, evidence: str):
    """Wave 4 §5: only `kg://license-grant/...` or
    `file:///etc/zer0pa/license-grants/...` count as isolation evidence."""
    env = _envelope(tool=tool, license_class=LicenseClass.B, license_evidence_uri=evidence)
    failures = gpl_isolation_falsifier(env)
    assert failures is None


@pytest.mark.parametrize(
    "evidence",
    [
        "https://github.com/gassraphael/AlphaPEM/blob/main/LICENSE",
        "https://license-grants.zer0pa.internal/AlphaPEM",  # external host, not file://
        "file:///tmp/some-other-grant.txt",  # not the canonical local prefix
        "",  # empty
    ],
)
def test_gpl_tool_with_bare_https_or_unvetted_evidence_blocked(evidence: str):
    """Wave 4 §5: bare HTTPS LICENSE URLs and ad-hoc local paths are NOT
    acceptable isolation evidence — public license pages aren't isolation grants."""
    env = _envelope(tool="AlphaPEM", license_class=LicenseClass.B, license_evidence_uri=evidence)
    failures = gpl_isolation_falsifier(env)
    assert failures is not None
    assert any(f.gate_id == "gpl_isolation_required" for f in failures)


# ---------------------------------------------------------------------------
# Class A tools — no gate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tool", ["PyBaMM", "OpenMC", "PyPSA", "pvlib", "Cantera"])
def test_class_a_tool_no_gate(tool: str):
    env = _envelope(tool=tool, license_class=LicenseClass.A, license_evidence_uri="")
    failures = gpl_isolation_falsifier(env)
    assert failures is None


# ---------------------------------------------------------------------------
# Class B LGPL (FreeGS, OMAS) — only blocked if tool is in the explicit
# isolation-required set. Most LGPL tools are NOT in the set.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tool", ["FreeGS", "OMAS", "Solcore", "BOUT++", "JOREK"])
def test_lgpl_tool_not_in_isolation_set_passes(tool: str):
    env = _envelope(tool=tool, license_class=LicenseClass.B, license_evidence_uri="")
    failures = gpl_isolation_falsifier(env)
    assert failures is None, (
        f"{tool} must NOT require isolation evidence under the LGPL→Class-B-permissive policy"
    )


# ---------------------------------------------------------------------------
# Class C/D/E — blocked by schema validator at construct time
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "license_class",
    [LicenseClass.C, LicenseClass.D, LicenseClass.E],
)
def test_class_cde_scientific_without_evidence_blocked_by_schema(license_class: LicenseClass):
    with pytest.raises(ValidationError):
        _envelope(
            tool="some-tool",
            license_class=license_class,
            license_evidence_uri="",
            mode=Mode.scientific,
        )


# ---------------------------------------------------------------------------
# Default falsifier set integrates the gpl_isolation gate
# ---------------------------------------------------------------------------


def test_default_set_blocks_gpl_in_scientific():
    env = _envelope(tool="AlphaPEM", license_class=LicenseClass.B, license_evidence_uri="")
    gated = apply_default_falsifiers(env)
    assert gated.falsification.gate_status in (GateStatus.fail, GateStatus.quarantine)
    assert any(
        f.gate_id == "gpl_isolation_required" for f in gated.falsification.failures
    )
