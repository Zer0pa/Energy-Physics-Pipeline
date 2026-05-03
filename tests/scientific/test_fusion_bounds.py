"""Scientific bounds tests for fusion adapters.

Boundary, COCOS, IDS-version, monotonicity, and q>0 must all be enforced at the
adapter level. Forbidden-intent strings raise BoundaryViolation immediately and
emit no envelope.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from energy_physics_pipeline.adapters.fusion import (
    FreeGS4eAdapter,
    ImasPythonAdapter,
    OpenMcManifestAdapter,
    ParamakGeometryAdapter,
    ReducedTransportCpuAdapter,
    read_imas_fixture,
    write_imas_fixture,
)
from energy_physics_pipeline.adapters.fusion.l1 import OpenMcSpec
from energy_physics_pipeline.adapters.fusion.l3 import EquilibriumSpec
from energy_physics_pipeline.adapters.fusion.l4 import (
    ImasReadSpec,
    TokamakScenarioSpec,
)
from energy_physics_pipeline.adapters.fusion.l5 import BlanketGeomSpec
from energy_physics_pipeline.boundary import BoundaryViolation


@pytest.fixture()
def tmp_imas_path(tmp_path: Path) -> Path:
    p = tmp_path / "imas_demo.nc"
    write_imas_fixture(p)
    return p


# ---------------------------------------------------------------------------
# Boundary intent gate (every layer must refuse forbidden intents)
# ---------------------------------------------------------------------------


def test_l1_forbidden_intent_raises():
    with pytest.raises(BoundaryViolation):
        OpenMcManifestAdapter().run(
            OpenMcSpec(intent="weapons-grade tritium production for stockpile")
        )


def test_l3_forbidden_intent_raises():
    with pytest.raises(BoundaryViolation):
        FreeGS4eAdapter().run(
            EquilibriumSpec(intent="weapon yield optimisation campaign")
        )


def test_l4_imas_forbidden_intent_raises(tmp_imas_path: Path):
    with pytest.raises(BoundaryViolation):
        ImasPythonAdapter().run(
            ImasReadSpec(intent="stockpile optimization", path=tmp_imas_path)
        )


def test_l4_scenario_forbidden_intent_raises():
    with pytest.raises(BoundaryViolation):
        ReducedTransportCpuAdapter().run(
            TokamakScenarioSpec(intent="warhead implosion compression study")
        )


def test_l5_forbidden_intent_raises():
    with pytest.raises(BoundaryViolation):
        ParamakGeometryAdapter().run(
            BlanketGeomSpec(intent="tritium diversion path planning")
        )


def test_l5_tbr_as_sole_objective_blocked():
    with pytest.raises(BoundaryViolation):
        ParamakGeometryAdapter().run(
            BlanketGeomSpec(intent="research-bound blanket TBR study"),
            optimization_target="tbr",
        )


# ---------------------------------------------------------------------------
# IMAS fixture / DD / COCOS / monotonicity
# ---------------------------------------------------------------------------


def test_imas_fixture_carries_dd_version_and_cocos(tmp_imas_path: Path):
    data = read_imas_fixture(tmp_imas_path)
    meta = data["metadata"]
    assert meta.get("data_dictionary_version") == "3.41.0"
    assert int(meta.get("COCOS")) == 11


def test_imas_blank_dd_raises(tmp_imas_path: Path):
    """Blank DD attribute should be refused by adapter (`if not dd: raise`)."""
    import netCDF4  # type: ignore[import-not-found]

    with netCDF4.Dataset(str(tmp_imas_path), "r+") as ds:
        ds.setncattr("data_dictionary_version", "")
    with pytest.raises(ValueError, match="data_dictionary_version"):
        ImasPythonAdapter().run(ImasReadSpec(path=tmp_imas_path))


def test_imas_invalid_cocos_logs_warn(tmp_imas_path: Path):
    """A non-11 COCOS value yields a `imas.cocos` warn FailureRecord, not a raise.

    The adapter raises only when the meta dict carries `cocos=None`; the netCDF backend
    falls back to -1 if the attribute is absent, so detection is via the inequality
    branch which appends a warn-level FailureRecord.
    """
    import netCDF4  # type: ignore[import-not-found]

    with netCDF4.Dataset(str(tmp_imas_path), "r+") as ds:
        ds.setncattr("COCOS", 17)  # invalid
    env = ImasPythonAdapter().run(ImasReadSpec(path=tmp_imas_path))
    assert any(f.gate_id == "imas.cocos" for f in env.falsification.failures)


def test_imas_q_le_zero_raises(tmp_imas_path: Path):
    """Mutate q inside the `equilibrium` group and confirm refusal."""
    import netCDF4  # type: ignore[import-not-found]

    with netCDF4.Dataset(str(tmp_imas_path), "r+") as ds:
        eq = ds.groups["equilibrium"]
        q = eq.variables["profiles_1d_q"][:]
        q[0, 0] = -1.0
        eq.variables["profiles_1d_q"][:] = q
    with pytest.raises(ValueError, match="q\\["):
        ImasPythonAdapter().run(ImasReadSpec(path=tmp_imas_path))


def test_imas_non_monotonic_time_raises(tmp_imas_path: Path):
    import netCDF4  # type: ignore[import-not-found]

    with netCDF4.Dataset(str(tmp_imas_path), "r+") as ds:
        eq = ds.groups["equilibrium"]
        t = eq.variables["time"][:]
        t = t[::-1]
        eq.variables["time"][:] = t
    with pytest.raises(ValueError, match="time is not strictly monotonic"):
        ImasPythonAdapter().run(ImasReadSpec(path=tmp_imas_path))


def test_imas_non_monotonic_rho_raises(tmp_imas_path: Path):
    import netCDF4  # type: ignore[import-not-found]

    with netCDF4.Dataset(str(tmp_imas_path), "r+") as ds:
        eq = ds.groups["equilibrium"]
        r = eq.variables["profiles_1d_rho_tor_norm"][:]
        r = r[:, ::-1]
        eq.variables["profiles_1d_rho_tor_norm"][:] = r
    with pytest.raises(ValueError, match="rho_tor_norm is not strictly monotonic"):
        ImasPythonAdapter().run(ImasReadSpec(path=tmp_imas_path))
