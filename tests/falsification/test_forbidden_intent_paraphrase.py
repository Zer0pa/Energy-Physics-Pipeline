"""Forbidden-intent matcher coverage — 30+ paraphrase tests per CPU hardening §6.

Each `BLOCKED_PHRASES` entry must produce a non-None match label.
Each `ALLOWED_PHRASES` entry must produce None — research framings of the
same vocabulary (blanket TBR, equilibrium reconstruction, breeding, decay
chains) must remain green.
"""
from __future__ import annotations

import pytest

from energy_physics_pipeline.boundary import check_fusion_intent


BLOCKED_PHRASES: list[str] = [
    # weapons-grade variations
    "weapons-grade tritium production",
    "weapon-grade tritium",
    "weapons grade fissile material",
    "weapon grade plutonium loading",
    "Weapons-Grade Tritium",  # casing
    "WEAPONS-GRADE TRITIUM",
    "weapons-grade  tritium  programme",  # double whitespace
    "weapons—grade tritium",  # em-dash
    # yield framings
    "explosive yield estimation",
    "weapon yield optimisation",
    "detonation yield curve",
    "thermonuclear yield calculations",
    "fission boost factor",
    "fission-boosted device",
    "thermonuclear weapon design study",
    # warhead / payload / delivery
    "warhead implosion compression",
    "missile-borne warhead",
    "military payload integration",
    "weapon payload simulation",
    "missile delivery system simulation",
    # diversion
    "tritium diversion path planning",
    "diverting fissile material from civilian inventory",
    "fissile diversion route analysis",
    # extraction / purification optimisation
    "tritium extraction optimization for diversion",
    "fissile purification optimisation campaign",
    "tritium extraction yield maximisation for stockpile",
    # stockpile
    "tritium stockpile target",
    "tritium stockpiling capacity",
    "weapon stockpile growth",
    "stockpile optimization",
    "stockpile maximisation",
    "Stockpile Optimization Strategy",
    # military / defence
    "defence application of plasma compression",
    "defense application portfolio review",
    "military application of fusion technology",
    "military fusion programme",
    "nuclear-weapons programme",
    # implosion / compression for weapons
    "compression for nuclear-device yield",
    "implosion compression for warhead",
]


ALLOWED_PHRASES: list[str] = [
    # research-bound vocabulary that uses adjacent terms but is policy-allowed
    "blanket TBR research for FLiBe breeder",
    "tritium breeding ratio under different Li-6 enrichments",
    "equilibrium reconstruction with Grad-Shafranov solver",
    "neutron transport for first-wall activation",
    "tritium extraction from molten salt for breeding cycle research",
    "tritium purification step in IFE blanket research",
    "stockpile of plasma scenarios in IMAS database",  # 'stockpile' but no optimisation/weapon
    "diversion-free fuel cycle research artifact",
    "scenario screening of plasma operating point for research",
    "DT plasma equilibrium with parabolic pressure profile",
    "perovskite/Si tandem PV for green-H2 export",
    "decay heat estimation under irradiation campaign",
    "extraction efficiency curve under varying Li-6 enrichment",  # benign extraction
]


@pytest.mark.parametrize("phrase", BLOCKED_PHRASES)
def test_blocked_phrase_is_caught(phrase: str):
    label = check_fusion_intent(phrase)
    assert label is not None, (
        f"Forbidden phrase NOT caught: {phrase!r}. Matcher returned None."
    )


@pytest.mark.parametrize("phrase", ALLOWED_PHRASES)
def test_allowed_phrase_is_not_caught(phrase: str):
    label = check_fusion_intent(phrase)
    assert label is None, (
        f"Allowed research phrase wrongly blocked: {phrase!r} -> {label}. "
        f"Matcher must not block research framings."
    )


def test_empty_input_returns_none():
    assert check_fusion_intent("") is None
    assert check_fusion_intent(None) is None


def test_extra_terms_substring_compat():
    """Backwards-compat: extra_terms acts like a substring whitelist for ad-hoc phrases."""
    assert check_fusion_intent("custom forbidden xyz", extra_terms=("custom forbidden",)) == "custom forbidden"
    assert check_fusion_intent("research scope", extra_terms=("custom forbidden",)) is None


def test_unicode_normalisation():
    """Em-dash and combining-diacritic variants normalise to plain ascii."""
    assert check_fusion_intent("weapons—grade tritium") is not None
    # NFKD strips diacritics; "wéapons-grade" should still match
    assert check_fusion_intent("wéapons-grade tritium") is not None
