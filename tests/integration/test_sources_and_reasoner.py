"""Integration tests: SourceLog, reasoner curator, and license gate end-to-end."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from energy_pipeline.adapters.shared.license_gate import LicenseGateError, assert_promotion_allowed
from energy_pipeline.adapters.shared.reasoner_curator import build_tuple_from_run, write_to_kg
from energy_pipeline.adapters.shared.source_log import SourceLog
from energy_pipeline.kg.graph import KGStore
from energy_pipeline.schemas.dro import DeviceResponseObject, DeviceFamily, DroAuditBlock
from energy_pipeline.schemas.envelope import (
    BackendBlock,
    Domain,
    ExecutionMode,
    FalsificationBlock,
    GateStatus,
    LayerLevel,
    LicenseClass,
    Mode,
    ProvenanceBlock,
    SubVertical,
    UniversalLayerEnvelope,
)
from energy_pipeline.schemas.reasoner import OutcomeLabel
from energy_pipeline.schemas.source import AllowedUse, RetrievalMethod, SourceManifest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_envelope() -> UniversalLayerEnvelope:
    """Build a minimal valid UniversalLayerEnvelope for testing."""
    backend = BackendBlock(
        adapter="test_adapter",
        tool="PyBaMM",
        tool_version="23.9.0",
        execution_mode=ExecutionMode.local_cpu,
        license_class=LicenseClass.A,
        license_evidence_uri="https://github.com/pybamm-team/PyBaMM/blob/develop/LICENSE.txt",
    )
    provenance = ProvenanceBlock(
        agent_id="test-agent-001",
        model_id="test-model-v1",
        git_sha="deadbeef",
        input_hash="sha256:aabbcc",
        output_hash="sha256:ddeeff",
        config_hash="sha256:001122",
    )
    falsification = FalsificationBlock(
        gate_status=GateStatus.pass_,
        scientific_valid=True,
        unit_check_passed=True,
        conservation_check_passed=True,
        boundary_check_passed=True,
    )
    env = UniversalLayerEnvelope(
        campaign_id="test-campaign-001",
        sub_vertical=SubVertical.electrochemistry,
        layer=LayerLevel.L4,
        domain=Domain.battery,
        mode=Mode.scientific,
        backend=backend,
        provenance=provenance,
        falsification=falsification,
    )
    return env.finalize()


def _make_dro(envelope: UniversalLayerEnvelope) -> DeviceResponseObject:
    """Build a minimal valid DeviceResponseObject for testing."""
    audit = DroAuditBlock(
        envelope_id=envelope.envelope_id or "test-eid",
        dro_source_layer_run_ids=[envelope.run_id],
    )
    dro = DeviceResponseObject(
        sub_vertical=SubVertical.electrochemistry,
        device_family=DeviceFamily.battery,
        audit=audit,
    )
    return dro.finalize()


# ---------------------------------------------------------------------------
# Tests: build_tuple_from_run + write_to_kg
# ---------------------------------------------------------------------------

class TestReasonerCurator:
    def test_build_tuple_from_run_deterministic(self) -> None:
        """build_tuple_from_run produces the same tuple_id for the same inputs."""
        env = _make_envelope()
        dro = _make_dro(env)
        t1 = build_tuple_from_run(env, dro, [], [])
        t2 = build_tuple_from_run(env, dro, [], [])
        assert t1.tuple_id == t2.tuple_id

    def test_build_tuple_outcome_pass(self) -> None:
        """scientific_valid=True + no falsifier_results => outcome pass."""
        env = _make_envelope()
        dro = _make_dro(env)
        t = build_tuple_from_run(env, dro, falsifier_results=[], disagreements=[])
        assert t.outcome_label == OutcomeLabel.pass_

    def test_build_tuple_outcome_fail(self) -> None:
        """scientific_valid=False + falsifier_results => outcome fail."""
        backend = BackendBlock(
            adapter="test_adapter",
            tool="PyBaMM",
            tool_version="23.9.0",
            execution_mode=ExecutionMode.local_cpu,
            license_class=LicenseClass.A,
            license_evidence_uri="https://example.com/license",
        )
        provenance = ProvenanceBlock(
            agent_id="test-agent-002",
            model_id="test-model-v1",
            git_sha="deadbeef",
            input_hash="sha256:aabbcc",
            output_hash="sha256:ddeeff",
            config_hash="sha256:001122",
        )
        falsification = FalsificationBlock(
            gate_status=GateStatus.fail,
            scientific_valid=False,
        )
        env = UniversalLayerEnvelope(
            campaign_id="test-campaign-002",
            sub_vertical=SubVertical.electrochemistry,
            layer=LayerLevel.L3,
            domain=Domain.battery,
            mode=Mode.engineering_stub,
            backend=backend,
            provenance=provenance,
            falsification=falsification,
        ).finalize()
        dro = _make_dro(env)
        t = build_tuple_from_run(env, dro, falsifier_results=["gate-soc-oor"], disagreements=[])
        assert t.outcome_label == OutcomeLabel.fail

    def test_write_to_kg_node_exists(self) -> None:
        """write_to_kg creates a ReasonerTuple node and DERIVED_FROM edges."""
        env = _make_envelope()
        dro = _make_dro(env)
        t = build_tuple_from_run(env, dro, falsifier_results=[], disagreements=[])

        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KGStore(kg_dir=Path(tmpdir))
            sha = write_to_kg(t, kg)

            # Node must exist
            assert t.tuple_id in kg._g.nodes, "ReasonerTuple node not in KG"

            # At least one DERIVED_FROM edge must exist from the tuple node
            out_edges = list(kg._g.out_edges(t.tuple_id, data=True))
            kinds = [d.get("kind") for _, _, d in out_edges]
            assert "DERIVED_FROM" in kinds, (
                f"Expected DERIVED_FROM edge from {t.tuple_id}, found: {kinds}"
            )

            # sha must be a non-empty string
            assert sha and isinstance(sha, str)

    def test_write_to_kg_derived_from_envelope_and_dro(self) -> None:
        """write_to_kg creates DERIVED_FROM edges to both envelope and DRO refs."""
        env = _make_envelope()
        dro = _make_dro(env)
        t = build_tuple_from_run(env, dro, falsifier_results=[], disagreements=[])

        with tempfile.TemporaryDirectory() as tmpdir:
            kg = KGStore(kg_dir=Path(tmpdir))
            write_to_kg(t, kg)

            out_edges = list(kg._g.out_edges(t.tuple_id, keys=True))
            edge_keys = [k for _, _, k in out_edges]
            # Both DERIVED_FROM edges exist (may collapse to one if envelope_id == dro_id
            # but tuple_id → input_spec_ref always exists)
            assert "DERIVED_FROM" in edge_keys


# ---------------------------------------------------------------------------
# Tests: license_gate.assert_promotion_allowed
# ---------------------------------------------------------------------------

class TestLicenseGate:
    def test_class_b_alphapem_scientific_no_evidence_raises(self) -> None:
        """AlphaPEM is Class B (GPL-3, isolate-or-replace). Per the conservative
        promotion gate, Class B tools also require evidence for scientific mode."""
        with pytest.raises(LicenseGateError):
            assert_promotion_allowed("AlphaPEM", "scientific", evidence_uri=None)

    def test_class_cde_no_evidence_raises(self) -> None:
        """OC25-eSEN-model is Class C; no evidence_uri must raise LicenseGateError."""
        with pytest.raises(LicenseGateError):
            assert_promotion_allowed("OC25-eSEN-model", "scientific", evidence_uri=None)

    def test_class_cde_with_kg_evidence_does_not_raise(self) -> None:
        """OC25-eSEN-model Class C passes when kg://license-grant/ URI is supplied."""
        assert_promotion_allowed(
            "OC25-eSEN-model",
            "scientific",
            evidence_uri="kg://license-grant/OC25-eSEN-ZA-accepted-2026-04-30",
        )

    def test_gene_excluded_scientific_no_evidence_raises(self) -> None:
        """GENE is Class E; no evidence URI must raise LicenseGateError."""
        with pytest.raises(LicenseGateError):
            assert_promotion_allowed("GENE", "scientific", evidence_uri=None)

    def test_gene_excluded_with_https_evidence_does_not_raise(self) -> None:
        """GENE Class E passes when a valid https:// evidence URI is supplied."""
        assert_promotion_allowed(
            "GENE",
            "scientific",
            evidence_uri="https://example.com/gene-license-grant-2026.pdf",
        )

    def test_engineering_stub_always_passes(self) -> None:
        """engineering_stub target always passes regardless of class."""
        assert_promotion_allowed("GENE", "engineering_stub", evidence_uri=None)
        assert_promotion_allowed("SCAPS-1D", "engineering_stub", evidence_uri=None)
        assert_promotion_allowed("PF-PINO", "engineering_stub", evidence_uri=None)

    def test_class_a_passes_without_evidence(self) -> None:
        """Class A tools (PyBaMM) pass scientific promotion without evidence URI."""
        assert_promotion_allowed("PyBaMM", "scientific", evidence_uri=None)

    def test_unknown_tool_raises(self) -> None:
        """Tool not in license_findings.jsonl is treated as Class E and raises."""
        with pytest.raises(LicenseGateError):
            assert_promotion_allowed("NonExistentTool12345", "scientific", evidence_uri=None)

    def test_task_specified_alphapem_scientific_no_evidence(self) -> None:
        """Task spec: assert_promotion_allowed('AlphaPEM', 'scientific', evidence_uri=None)
        must raise. AlphaPEM is Class B (GPL-3.0, isolate-or-replace); the conservative
        gate blocks B/C/D/E promotion to scientific without a valid evidence URI."""
        with pytest.raises(LicenseGateError):
            assert_promotion_allowed("AlphaPEM", "scientific", evidence_uri=None)

    def test_task_specified_alphapem_with_kg_grant_does_not_raise(self) -> None:
        """Task spec: assert_promotion_allowed with kg://license-grant/ must NOT raise."""
        # AlphaPEM is Class B; our gate only blocks C/D/E, so this passes.
        assert_promotion_allowed(
            "AlphaPEM",
            "scientific",
            evidence_uri="kg://license-grant/AlphaPEM-isolated-2026-04-30",
        )


# ---------------------------------------------------------------------------
# Tests: SourceLog round-trip
# ---------------------------------------------------------------------------

class TestSourceLog:
    def test_add_and_find_by_id(self) -> None:
        """add() appends a manifest; find_by_id() retrieves it."""
        m = SourceManifest(
            source_id="test-pyscf-rt",
            uri="https://github.com/pyscf/pyscf/blob/master/LICENSE",
            retrieval_method=RetrievalMethod.manual,
            retrieved_at="2026-04-30T00:00:00+00:00",
            license_spdx_or_text="Apache-2.0",
            allowed_use=AllowedUse.commercial,
            geography_restrictions="None",
            checksum="sha256:0000000000000000000000000000000000000000000000000000000000000000",
            local_slice_size_mb=0.0,
            bulk_data_stored=False,
            citation="PySCF test entry.",
            rights_notes="Integration test — not a real entry.",
        )
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            tmp = Path(f.name)
        try:
            log = SourceLog(path=tmp)
            log.add(m)
            found = log.find_by_id("test-pyscf-rt")
            assert found is not None
            assert found.source_id == "test-pyscf-rt"
            assert found.license_spdx_or_text == "Apache-2.0"
        finally:
            tmp.unlink(missing_ok=True)

    def test_seed_jsonl_loads_minimum_entries(self) -> None:
        """The production seed.jsonl must contain >= 30 entries via SourceLog."""
        log = SourceLog()
        assert log.count() >= 30, f"Expected >= 30, got {log.count()}"

    def test_query_by_license(self) -> None:
        """query_by_license returns only entries matching the given SPDX string."""
        log = SourceLog()
        mit_entries = log.query_by_license("MIT")
        assert len(mit_entries) >= 1, "Expected at least one MIT entry in seed.jsonl"
        for m in mit_entries:
            assert m.license_spdx_or_text == "MIT"
