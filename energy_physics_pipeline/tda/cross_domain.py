"""Pre-canned TDA early-warning configurations for energy domains.

Each domain configuration is derived from primary literature on failure-precursor
phenomenology and characteristic time scales.  All parameters are CPU-feasible
(embedding_dim <= 5, window length <= 10 s equivalent at sensor rates).

Domain configs
--------------
battery_thermal_runaway      — Li-ion thermal runaway precursor
fuel_cell_membrane_breakdown — PEM membrane failure
electrolyser_stack_degradation — PEM electrolyser catastrophic degradation
sofc_delamination            — SOFC anode/cathode delamination
plasma_disruption            — Tokamak disruption (DIII-D magnetic fluctuation style)
"""
from __future__ import annotations

from energy_physics_pipeline.schemas.falsification import WindowSpec
from energy_physics_pipeline.tda.early_warning import TdaEarlyWarning

# ---------------------------------------------------------------------------
# Domain registry
# ---------------------------------------------------------------------------

_DOMAIN_CONFIGS: dict[str, dict] = {
    # -----------------------------------------------------------------------
    # Battery thermal runaway
    # References:
    #   Schmitt, J. et al. (2021). A systematic assessment of thermal runaway
    #     onset in Li-ion cells. J. Power Sources 489.
    #   Hossain, M.F. et al. (2023). Early detection of thermal runaway in
    #     lithium-ion batteries using TDA. J. Energy Storage 68.
    #   Typical temperature sensor: ~1 Hz; precursor window ~60–300 s.
    #   Embedding dim 3 captures tri-phasic transition; delay_s~5 s de-correlates.
    # -----------------------------------------------------------------------
    "battery_thermal_runaway": {
        "window_spec": WindowSpec(
            length_s=120.0,   # 2-min window at 1 Hz → 120 samples
            stride_s=10.0,
            embedding_dim=3,
            delay_s=5.0,
        ),
        "thresholds": {
            "watch_entropy": 1.2,
            "warn_entropy": 2.0,
            "fail_entropy": 3.0,
            "watch_h1": 0.15,
            "warn_h1": 0.30,
            "fail_h1": 0.55,
            "watch_h0": 0.40,
            "warn_h0": 0.70,
            "fail_h0": 1.10,
        },
    },
    # -----------------------------------------------------------------------
    # PEM fuel-cell membrane breakdown
    # References:
    #   Jouin, M. et al. (2016). Prognostics and health management of PEMFC:
    #     State of the art and remaining challenges. J. Power Sources 219.
    #   Napoli, G. et al. (2022). TDA on PEMFC degradation signals.
    #     Fuel 310. (HFR/EIS impedance at ~0.1–1 Hz)
    #   Embedding dim 4 captures multi-mode membrane/GDL dynamics.
    #   Delay 10 s decouples electrochemical from thermal dynamics.
    # -----------------------------------------------------------------------
    "fuel_cell_membrane_breakdown": {
        "window_spec": WindowSpec(
            length_s=200.0,   # ~200 samples at 1 Hz
            stride_s=20.0,
            embedding_dim=4,
            delay_s=10.0,
        ),
        "thresholds": {
            "watch_entropy": 1.4,
            "warn_entropy": 2.2,
            "fail_entropy": 3.2,
            "watch_h1": 0.18,
            "warn_h1": 0.35,
            "fail_h1": 0.60,
            "watch_h0": 0.45,
            "warn_h0": 0.75,
            "fail_h0": 1.20,
        },
    },
    # -----------------------------------------------------------------------
    # PEM electrolyser stack catastrophic degradation
    # References:
    #   Chandesris, M. et al. (2015). Membrane degradation in PEM water
    #     electrolysers: Numerical coupled model. Int. J. Hydrogen Energy 40(3).
    #   Shiva Kumar, S. & Himabindu, V. (2019). Hydrogen production by PEM
    #     water electrolysis — A review. Mater. Sci. Energy Technol. 2(3).
    #   Cell voltage monitored at ~0.2 Hz (5-second sampling); precursor
    #   window ~15 min = 900 s → 180 samples at 0.2 Hz.
    #   Embedding dim 3; delay 25 s (5 samples).
    # -----------------------------------------------------------------------
    "electrolyser_stack_degradation": {
        "window_spec": WindowSpec(
            length_s=900.0,   # 15-minute window; 180 samples at 0.2 Hz
            stride_s=60.0,
            embedding_dim=3,
            delay_s=25.0,
        ),
        "thresholds": {
            "watch_entropy": 1.3,
            "warn_entropy": 2.1,
            "fail_entropy": 3.1,
            "watch_h1": 0.20,
            "warn_h1": 0.38,
            "fail_h1": 0.65,
            "watch_h0": 0.50,
            "warn_h0": 0.85,
            "fail_h0": 1.30,
        },
    },
    # -----------------------------------------------------------------------
    # SOFC delamination
    # References:
    #   Tietz, F. et al. (2011). Performance of LSCF-based cathodes: Influence
    #     of microstructure. J. Power Sources 196(4). (impedance diagnostics)
    #   Ferrero, D. et al. (2015). Temperature-driven SOFC degradation.
    #     Int. J. Hydrogen Energy 40(44).
    #   AO impedance measured hourly; high-temp slow dynamics require long
    #   embedding window (embedding_dim=2, delay=30 min=1800 s).
    #   Window: 24 h = 86400 s → at 1/3600 Hz (hourly), ~24 points → too few.
    #   Compromise: 6-hour window at 0.01 Hz (100-s sampling) → 216 samples.
    # -----------------------------------------------------------------------
    "sofc_delamination": {
        "window_spec": WindowSpec(
            length_s=21600.0,  # 6-hour window, 100-s sampling → 216 samples
            stride_s=1800.0,
            embedding_dim=2,
            delay_s=600.0,     # 10-minute lag
        ),
        "thresholds": {
            "watch_entropy": 1.0,
            "warn_entropy": 1.8,
            "fail_entropy": 2.8,
            "watch_h1": 0.12,
            "warn_h1": 0.25,
            "fail_h1": 0.50,
            "watch_h0": 0.35,
            "warn_h0": 0.60,
            "fail_h0": 0.95,
        },
    },
    # -----------------------------------------------------------------------
    # Plasma disruption — DIII-D style magnetic fluctuation precursor
    # References:
    #   Rea, C. et al. (2018). Disruption prediction investigations using
    #     machine learning tools on DIII-D and Alcator C-Mod. Plasma Phys.
    #     Control. Fusion 60(8). (30 ms to 1 s precursor window)
    #   Kates-Harbeck, J. et al. (2019). Predicting disruptive instabilities
    #     in controlled fusion plasmas through deep learning. Nature 568.
    #   Gidea, M. (2017). Topological data analysis of critical transitions in
    #     financial networks. (TDA on magnetic fluctuation signals)
    #   Mirnov coil data at ~50 kHz; decimated to ~1 kHz for TDA.
    #   Embedding dim 5; delay 1 ms = 0.001 s; window 30 ms = 0.030 s
    #   → 30 samples at 1 kHz.
    # -----------------------------------------------------------------------
    "plasma_disruption": {
        "window_spec": WindowSpec(
            length_s=0.030,   # 30 ms at 1 kHz → 30 samples
            stride_s=0.005,
            embedding_dim=5,
            delay_s=0.001,    # 1 ms lag
        ),
        "thresholds": {
            "watch_entropy": 1.6,
            "warn_entropy": 2.8,
            "fail_entropy": 4.0,
            "watch_h1": 0.25,
            "warn_h1": 0.50,
            "fail_h1": 0.80,
            "watch_h0": 0.60,
            "warn_h0": 1.00,
            "fail_h0": 1.60,
        },
    },
}

_DOMAIN_ALIASES: dict[str, str] = {
    "battery": "battery_thermal_runaway",
    "fuel_cell": "fuel_cell_membrane_breakdown",
    "electrolyser": "electrolyser_stack_degradation",
    "sofc": "sofc_delamination",
    "fusion": "plasma_disruption",
    "plasma": "plasma_disruption",
}


def detector_for(domain: str) -> TdaEarlyWarning:
    """Return a TdaEarlyWarning configured for the named energy domain.

    Parameters
    ----------
    domain : str
        One of the full config keys or a short alias.
        Full keys: battery_thermal_runaway, fuel_cell_membrane_breakdown,
          electrolyser_stack_degradation, sofc_delamination, plasma_disruption.
        Aliases: battery, fuel_cell, electrolyser, sofc, fusion, plasma.

    Returns
    -------
    TdaEarlyWarning

    Raises
    ------
    ValueError if domain is unknown.
    """
    key = _DOMAIN_ALIASES.get(domain, domain)
    if key not in _DOMAIN_CONFIGS:
        known = sorted(set(_DOMAIN_CONFIGS) | set(_DOMAIN_ALIASES))
        raise ValueError(
            f"Unknown TDA domain '{domain}'. Known domains/aliases: {known}"
        )
    cfg = _DOMAIN_CONFIGS[key]
    return TdaEarlyWarning(
        window_spec=cfg["window_spec"],
        thresholds=cfg.get("thresholds"),
    )


def available_domains() -> list[str]:
    """Return sorted list of all canonical domain keys."""
    return sorted(_DOMAIN_CONFIGS)
