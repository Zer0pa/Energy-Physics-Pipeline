"""TDA early-warning sub-package.

CPU-only persistent homology via ripser + persim.
No giotto-tda (AGPL).  No GUDHI (requires module-level license whitelist).
"""
from energy_pipeline.tda.early_warning import TdaEarlyWarning
from energy_pipeline.tda.cross_domain import detector_for, available_domains
from energy_pipeline.tda.no_leakage import NoLeakageGuard

__all__ = [
    "TdaEarlyWarning",
    "detector_for",
    "available_domains",
    "NoLeakageGuard",
]
