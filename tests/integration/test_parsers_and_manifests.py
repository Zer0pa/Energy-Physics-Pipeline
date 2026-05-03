"""H10 — minimal parser/manifest adapters tests.

Covers:
  - CIF / xyz / SMILES parsers (real-CPU; mode=scientific on success)
  - ToolManifestAdapter for GPAW/CP2K/Wannier90/Z2Pack/MACE/fairchem-eSEN/
    LAMMPS/PEMD/PiNet2/OpenLB/LBPM/OpenModelica-FMI (all manifest-only)
"""
from __future__ import annotations

import pytest

from energy_physics_pipeline.adapters.electrochem.parsers import (
    StructureParserAdapter,
    ToolManifestAdapter,
    known_manifests,
    parse_cif,
    parse_smiles,
    parse_xyz,
)
from energy_physics_pipeline.boundary import BOUNDARY_BLOCK
from energy_physics_pipeline.l6 import reload as cfg_reload
from energy_physics_pipeline.schemas import Mode


# ---------------------------------------------------------------------------
# Pure parsers
# ---------------------------------------------------------------------------


_CIF_SAMPLE = """
data_NMC
_cell_length_a 2.85
_cell_length_b 2.85
_cell_length_c 14.20
_cell_angle_alpha 90.0
_cell_angle_beta 90.0
_cell_angle_gamma 120.0
loop_
_atom_site_label
_atom_site_type_symbol
Li1 Li
Ni1 Ni
"""

_XYZ_SAMPLE = """3
H2O example fixture
O 0.000 0.000 0.000
H 0.757 0.586 0.000
H -0.757 0.586 0.000
"""


def test_parse_cif_returns_cell_lengths():
    out = parse_cif(_CIF_SAMPLE)
    assert out["format"] == "CIF"
    assert pytest.approx(out["cell_lengths_ang"]["a"]) == 2.85
    assert pytest.approx(out["cell_lengths_ang"]["c"]) == 14.20
    assert out["cell_angles_deg"]["gamma"] == 120.0


def test_parse_xyz_returns_atoms():
    out = parse_xyz(_XYZ_SAMPLE)
    assert out["format"] == "xyz"
    assert out["atom_count"] == 3
    assert out["atoms"][0]["element"] == "O"
    assert out["atoms"][1]["element"] == "H"


def test_parse_xyz_count_mismatch_raises():
    bad = "5\ncomment\nO 0 0 0\n"
    with pytest.raises(ValueError):
        parse_xyz(bad)


def test_parse_smiles_accepts_canonical():
    out = parse_smiles("CC(=O)Oc1ccccc1C(=O)O")  # aspirin
    assert out["format"] == "SMILES"
    assert out["balanced"] is True


def test_parse_smiles_rejects_illegal_chars():
    with pytest.raises(ValueError):
        parse_smiles("C C ;DROP TABLE atoms;")


def test_parse_smiles_rejects_unbalanced():
    with pytest.raises(ValueError):
        parse_smiles("C(C(C")


# ---------------------------------------------------------------------------
# Adapter wrappers — envelopes pass production gate
# ---------------------------------------------------------------------------


def test_structure_parser_adapter_cif_returns_scientific_envelope(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENERGY_BOUNDARY_GATE", "warn")  # don't fail on warn-level
    cfg_reload()
    env = StructureParserAdapter().parse_cif(_CIF_SAMPLE)
    assert env.boundary == BOUNDARY_BLOCK
    assert env.mode == Mode.scientific
    assert env.outputs.payload["cell_lengths_ang"]["a"] == 2.85


def test_structure_parser_adapter_bad_smiles_yields_stub(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENERGY_BOUNDARY_GATE", "warn")
    cfg_reload()
    env = StructureParserAdapter().parse_smiles("not a smiles!!! @@##")
    assert env.mode == Mode.engineering_stub
    assert any(f.gate_id == "parser_failure" for f in env.falsification.failures)


# ---------------------------------------------------------------------------
# Manifest-only adapters — every tool emits a contract-shaped envelope
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tool_id", sorted(known_manifests().keys()))
def test_tool_manifest_envelope_for_each(tool_id: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENERGY_BOUNDARY_GATE", "warn")
    cfg_reload()
    spec = known_manifests()[tool_id]
    env = ToolManifestAdapter().emit(spec)
    assert env.boundary == BOUNDARY_BLOCK
    assert env.mode == Mode.engineering_stub
    assert env.outputs.payload["manifest_only"] is True
    assert env.outputs.payload["tool"] == spec.tool


def test_known_manifests_covers_prd_tools():
    """The known_manifests() dict must cover every PRD CPU-feasible tool that
    is not already wired as a real CPU adapter."""
    expected = {
        "gpaw", "cp2k", "wannier90", "z2pack",
        "mace", "fairchem-esen", "lammps", "pemd", "pinet2",
        "openlb", "lbpm",
        "openmodelica-fmi",
    }
    have = set(known_manifests().keys())
    missing = expected - have
    assert not missing, f"missing tool manifests: {missing}"
