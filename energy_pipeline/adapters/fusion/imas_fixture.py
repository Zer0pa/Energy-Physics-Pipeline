"""IMAS fixture netCDF — tiny IDS-shaped equilibrium + core_profiles bundle.

Designed to give the L4 IMAS adapter a real netCDF file to read against,
without requiring the full IMAS Access Layer or any institutional account.
The structure mirrors a *very* abbreviated subset of IDS paths actually
emitted by IMAS:

  equilibrium/time_slice[i]/profiles_1d/{rho_tor_norm, q, pressure, j_phi}
  core_profiles/profiles_1d[i]/{rho_tor_norm, n_e, t_e, t_i}

Backend declared: backend="netcdf", URI="file://...", DD version 3.41.0,
COCOS=11. This is a research fixture, not an IMAS-blessed dataset.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np

IMAS_DD_VERSION = "3.41.0"
IMAS_BACKEND = "netcdf"
IMAS_OCCURRENCE = 0
IMAS_COCOS = 11


def _q_profile(n: int = 11) -> np.ndarray:
    rho = np.linspace(0.0, 1.0, n)
    return 1.05 + 2.6 * rho ** 2  # q0 ~ 1.05, q95 ~ 3.65


def _pressure_profile(n: int = 11) -> np.ndarray:
    rho = np.linspace(0.0, 1.0, n)
    p0 = 1.5e5  # 150 kPa axis
    return p0 * (1.0 - rho ** 2) ** 1.5


def _jphi_profile(n: int = 11) -> np.ndarray:
    rho = np.linspace(0.0, 1.0, n)
    return 1.2e6 * (1.0 - rho ** 2)  # 1.2 MA/m^2 axis


def _ne_profile(n: int = 11) -> np.ndarray:
    rho = np.linspace(0.0, 1.0, n)
    return 5.0e19 * (1.0 - 0.7 * rho ** 2)  # m^-3


def _te_profile(n: int = 11) -> np.ndarray:
    rho = np.linspace(0.0, 1.0, n)
    return 5.0e3 * (1.0 - rho ** 2) + 100.0  # eV (5 keV core, 100 eV edge)


def _ti_profile(n: int = 11) -> np.ndarray:
    rho = np.linspace(0.0, 1.0, n)
    return 5.5e3 * (1.0 - rho ** 2) + 100.0  # eV


def write_fixture(path: Path) -> dict[str, Any]:
    """Write the IMAS fixture netCDF and return its metadata block.

    Returns
    -------
    metadata : dict
      {
        'data_dictionary_version': '3.41.0',
        'backend': 'netcdf',
        'URI': 'file://...',
        'occurrence': 0,
        'COCOS': 11,
        'sha256': '<hex>',
        'source': 'fixture',
        'access_class': 'public',
      }
    """
    import netCDF4 as nc

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    n_psi = 11
    n_time = 2

    times = np.array([0.0, 0.1], dtype="f8")  # 100 ms apart
    rho = np.linspace(0.0, 1.0, n_psi).astype("f8")
    q = _q_profile(n_psi).astype("f8")
    p = _pressure_profile(n_psi).astype("f8")
    jphi = _jphi_profile(n_psi).astype("f8")
    ne = _ne_profile(n_psi).astype("f8")
    te = _te_profile(n_psi).astype("f8")
    ti = _ti_profile(n_psi).astype("f8")

    with nc.Dataset(path, "w", format="NETCDF4") as ds:
        # IMAS-style global metadata
        ds.data_dictionary_version = IMAS_DD_VERSION
        ds.backend = IMAS_BACKEND
        ds.URI = f"file://{path.resolve().as_posix()}"
        ds.occurrence = IMAS_OCCURRENCE
        ds.COCOS = IMAS_COCOS
        ds.source = "fixture"
        ds.access_class = "public"

        # Dimensions
        ds.createDimension("time", n_time)
        ds.createDimension("rho", n_psi)

        # equilibrium IDS
        eq = ds.createGroup("equilibrium")
        eq_t = eq.createVariable("time", "f8", ("time",))
        eq_t[:] = times
        eq_t.units = "s"
        eq_t.long_name = "equilibrium/time"

        eq_rho = eq.createVariable("profiles_1d_rho_tor_norm", "f8", ("time", "rho"))
        eq_rho[0, :] = rho
        eq_rho[1, :] = rho
        eq_rho.units = "1"
        eq_rho.long_name = "equilibrium/time_slice[]/profiles_1d/rho_tor_norm"

        eq_q = eq.createVariable("profiles_1d_q", "f8", ("time", "rho"))
        eq_q[0, :] = q
        eq_q[1, :] = q * 1.005  # tiny evolution
        eq_q.units = "1"
        eq_q.long_name = "equilibrium/time_slice[]/profiles_1d/q"

        eq_p = eq.createVariable("profiles_1d_pressure", "f8", ("time", "rho"))
        eq_p[0, :] = p
        eq_p[1, :] = p * 1.01
        eq_p.units = "Pa"
        eq_p.long_name = "equilibrium/time_slice[]/profiles_1d/pressure"

        eq_j = eq.createVariable("profiles_1d_j_phi", "f8", ("time", "rho"))
        eq_j[0, :] = jphi
        eq_j[1, :] = jphi * 1.005
        eq_j.units = "A.m^-2"
        eq_j.long_name = "equilibrium/time_slice[]/profiles_1d/j_phi"

        # core_profiles IDS
        cp = ds.createGroup("core_profiles")
        cp_t = cp.createVariable("time", "f8", ("time",))
        cp_t[:] = times
        cp_t.units = "s"
        cp_t.long_name = "core_profiles/time"

        cp_rho = cp.createVariable("profiles_1d_grid_rho_tor_norm", "f8", ("time", "rho"))
        cp_rho[0, :] = rho
        cp_rho[1, :] = rho
        cp_rho.units = "1"
        cp_rho.long_name = "core_profiles/profiles_1d[]/grid/rho_tor_norm"

        cp_ne = cp.createVariable("profiles_1d_electrons_density", "f8", ("time", "rho"))
        cp_ne[0, :] = ne
        cp_ne[1, :] = ne * 0.99
        cp_ne.units = "m^-3"
        cp_ne.long_name = "core_profiles/profiles_1d[]/electrons/density"

        cp_te = cp.createVariable("profiles_1d_electrons_temperature", "f8", ("time", "rho"))
        cp_te[0, :] = te
        cp_te[1, :] = te * 1.005
        cp_te.units = "eV"
        cp_te.long_name = "core_profiles/profiles_1d[]/electrons/temperature"

        cp_ti = cp.createVariable("profiles_1d_t_i_average", "f8", ("time", "rho"))
        cp_ti[0, :] = ti
        cp_ti[1, :] = ti * 1.005
        cp_ti.units = "eV"
        cp_ti.long_name = "core_profiles/profiles_1d[]/t_i_average"

    sha = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return {
        "data_dictionary_version": IMAS_DD_VERSION,
        "backend": IMAS_BACKEND,
        "URI": f"file://{path.resolve().as_posix()}",
        "occurrence": IMAS_OCCURRENCE,
        "COCOS": IMAS_COCOS,
        "sha256": sha,
        "source": "fixture",
        "access_class": "public",
    }


def read_fixture(path: Path) -> dict[str, Any]:
    """Read the IMAS fixture netCDF and return all profiles + metadata."""
    import netCDF4 as nc

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"IMAS fixture not found: {path}")
    with nc.Dataset(path, "r") as ds:
        meta = {
            "data_dictionary_version": getattr(ds, "data_dictionary_version", None),
            "backend": getattr(ds, "backend", None),
            "URI": getattr(ds, "URI", None),
            "occurrence": int(getattr(ds, "occurrence", -1)),
            "COCOS": int(getattr(ds, "COCOS", -1)),
            "source": getattr(ds, "source", None),
            "access_class": getattr(ds, "access_class", None),
        }
        eq = ds.groups["equilibrium"]
        cp = ds.groups["core_profiles"]
        out = {
            "metadata": meta,
            "ids_paths_used": [
                "equilibrium/time",
                "equilibrium/time_slice[]/profiles_1d/rho_tor_norm",
                "equilibrium/time_slice[]/profiles_1d/q",
                "equilibrium/time_slice[]/profiles_1d/pressure",
                "equilibrium/time_slice[]/profiles_1d/j_phi",
                "core_profiles/time",
                "core_profiles/profiles_1d[]/grid/rho_tor_norm",
                "core_profiles/profiles_1d[]/electrons/density",
                "core_profiles/profiles_1d[]/electrons/temperature",
                "core_profiles/profiles_1d[]/t_i_average",
            ],
            "equilibrium": {
                "time": eq.variables["time"][:].tolist(),
                "rho_tor_norm": eq.variables["profiles_1d_rho_tor_norm"][:].tolist(),
                "q": eq.variables["profiles_1d_q"][:].tolist(),
                "pressure": eq.variables["profiles_1d_pressure"][:].tolist(),
                "j_phi": eq.variables["profiles_1d_j_phi"][:].tolist(),
            },
            "core_profiles": {
                "time": cp.variables["time"][:].tolist(),
                "rho_tor_norm": cp.variables["profiles_1d_grid_rho_tor_norm"][:].tolist(),
                "n_e": cp.variables["profiles_1d_electrons_density"][:].tolist(),
                "t_e": cp.variables["profiles_1d_electrons_temperature"][:].tolist(),
                "t_i": cp.variables["profiles_1d_t_i_average"][:].tolist(),
            },
        }
    sha = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    out["metadata"]["sha256"] = sha
    return out
