"""Electrochemistry adapter stack — L1 through L5.

BOUNDARY_BLOCK: Research infrastructure for in silico energy science: electrochemical conversion
(batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics,
thermoelectrics) and fusion / plasma physics. Outputs are research artifacts.
No regulatory certification claims. No clinical or human-subject use.
Defence / weapons applications are out of scope under operator policy.
"""
from energy_physics_pipeline.adapters.electrochem.l1 import ElectronicStructureAdapter
from energy_physics_pipeline.adapters.electrochem.l2 import (
    MLIPManifestAdapter,
    trajectory_msd,
    reaction_ranking,
)
from energy_physics_pipeline.adapters.electrochem.l3 import (
    VTKManifestParser,
    HDF5ManifestParser,
    phasefield_stub,
)
from energy_physics_pipeline.adapters.electrochem.l4 import (
    PyBaMMBatteryAdapter,
    SolcorePvAdapter,
    CanteraSofcAdapter,
    PemAdapter,
    ThermoelectricAdapter,
    write_l4_artifacts,
)
from energy_physics_pipeline.adapters.electrochem.l5 import (
    PyPSALcoeAdapter,
    PvlibYieldAdapter,
    PySAMLcoeAdapter,
    write_l5_artifacts,
)

__all__ = [
    # L1
    "ElectronicStructureAdapter",
    # L2
    "MLIPManifestAdapter",
    "trajectory_msd",
    "reaction_ranking",
    # L3
    "VTKManifestParser",
    "HDF5ManifestParser",
    "phasefield_stub",
    # L4
    "PyBaMMBatteryAdapter",
    "SolcorePvAdapter",
    "CanteraSofcAdapter",
    "PemAdapter",
    "ThermoelectricAdapter",
    "write_l4_artifacts",
    # L5
    "PyPSALcoeAdapter",
    "PvlibYieldAdapter",
    "PySAMLcoeAdapter",
    "write_l5_artifacts",
]
