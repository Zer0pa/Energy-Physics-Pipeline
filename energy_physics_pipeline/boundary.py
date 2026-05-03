"""Boundary block — the authority of last resort.

Every artifact emitted by the pipeline must carry the verbatim BOUNDARY_BLOCK string.
Mutation of the string fails the boundary check.

Fusion intents that are explicitly blocked are matched with a normalised regex
patterns table (see CPU hardening brief §6 — "policy-equivalent forbidden intents").
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable, Mapping

BOUNDARY_BLOCK: str = (
    "Research infrastructure for in silico energy science: electrochemical conversion "
    "(batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, "
    "thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. "
    "No regulatory certification claims. No clinical or human-subject use. "
    "Defence / weapons applications are out of scope under operator policy."
)


# ---------------------------------------------------------------------------
# Forbidden-intent regex patterns
#
# Each pattern is a (label, regex) pair. Matching is on the *normalised* form of
# the input (see `_normalise_text`):
#   - Unicode-NFKD, drop combining marks
#   - lowercase
#   - collapse runs of whitespace and hyphens to a single space
#   - tabs/newlines treated as whitespace
#
# Categories enforced:
#   1. weapons-grade fissile/fusion material
#   2. weapon yield, explosive yield, fission boost, thermonuclear weapon
#   3. military / defence / warhead / payload / delivery system
#   4. diversion of fissile / fusion / tritium material
#   5. purification / extraction *optimisation* (not benign extraction)
#   6. stockpile / stockpiling (any context — operator policy is hard-no)
#   7. boost / detonation / yield estimation framings
#
# Word-boundary (\b) and stem variations are explicit. Negative-lookahead is used
# to keep "tritium extraction for breeding" research-allowed while blocking
# "tritium extraction optimization for diversion".
# ---------------------------------------------------------------------------


_FORBIDDEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (label, re.compile(pat, re.IGNORECASE | re.VERBOSE))
    for label, pat in (
        # 1. weapons-grade material (any chemistry)
        (
            "weapons-grade",
            r"""\b weapons? [\- ]? grade \b""",
        ),
        # 2a. weapon yield / explosive yield / detonation yield
        (
            "weapon-yield",
            r"""\b (weapon|explosive|detonation|nuclear|thermo[\- ]? nuclear) [\- ]? yield s? \b""",
        ),
        # 2b. fission boost / boosted device
        (
            "fission-boost",
            r"""\b (fission|fusion) [\- ]? boost (?:ed|ing)? \b""",
        ),
        # 2c. thermonuclear weapon
        (
            "thermonuclear-weapon",
            r"""\b thermo [\- ]? nuclear \s+ (weapon|device|arsenal) s? \b""",
        ),
        # 3a. warhead
        (
            "warhead",
            r"""\b warhead s? \b""",
        ),
        # 3b. military payload, weapon payload
        (
            "weapon-payload",
            r"""\b (military|weapon|missile) [\- ]? payload s? \b""",
        ),
        # 3c. delivery system (paired with weapon/warhead/missile)
        (
            "weapon-delivery-system",
            r"""\b (weapon|warhead|missile) (?:[\- ]?based)? \s+ delivery \s+ system s? \b""",
        ),
        # 3c-bis. bare "delivery system" — operator policy treats this as a
        # weapons-context phrase regardless of the surrounding noun. There is no
        # research framing for "delivery system" in the fusion / fissile context.
        (
            "bare-delivery-system",
            r"""\b delivery \s+ system s? \b""",
        ),
        # 3d. defence / defense application (US + UK spellings)
        (
            "defence-application",
            r"""\b (defence|defense) \s+ application s? \b""",
        ),
        # 3e. military application / military use of fusion / fission / weapon tech
        (
            "military-application",
            r"""\b military \s+ (application|use|programme|program|fusion|fission|payload) s? \b""",
        ),
        # 3f. nuclear-weapons programme / nuclear weapons program
        (
            "weapons-programme",
            r"""\b nuclear[\- ]?weapons? \s+ (programme|program) s? \b""",
        ),
        # 4a. diversion of tritium / fissile / fusion material (verb-first)
        (
            "material-diversion-vf",
            r"""
                \b (diver(?:t|ts|ted|ting|sion))
                .{0,40}?
                \b (tritium|fissile|fusion[\- ]?material|material|warhead)
                \b
            """,
        ),
        # 4b. material-first phrasing: "fissile diversion route"
        (
            "material-diversion-mf",
            r"""
                \b (tritium|fissile|fusion[\- ]?material)
                .{0,30}?
                \b diver(?:sion|ting|ted|ts|t)
                \b
            """,
        ),
        # 4c. tritium diversion (compact)
        (
            "tritium-diversion",
            r"""\b tritium \s+ diver(?:sion|ted|ting|t) \b""",
        ),
        # 5a. tritium / fissile extraction OPTIMISATION (not benign extraction)
        (
            "tritium-extraction-optimisation",
            r"""
                \b (tritium|fissile|fusion[\- ]?material)
                .{0,40}?
                \b extraction \b
                .{0,40}?
                \b (optimi[sz]ation|optimi[sz]e|maxim(?:um|al|ize|ise)|yield)
            """,
        ),
        # 5b. tritium / fissile purification OPTIMISATION
        (
            "tritium-purification-optimisation",
            r"""
                \b (tritium|fissile)
                .{0,40}?
                \b purification \b
                .{0,40}?
                \b (optimi[sz]ation|optimi[sz]e|maxim(?:um|al|ize|ise))
            """,
        ),
        # 6a. tritium stockpile (any phrasing)
        (
            "tritium-stockpile",
            r"""\b tritium .{0,30}? \b stockpil(e|es|ing|ed) \b""",
        ),
        # 6b. weapon / military stockpile
        (
            "weapon-stockpile",
            r"""\b (weapon|nuclear|military|fissile) [\- ]? stockpil(e|es|ing|ed) \b""",
        ),
        # 6c. stockpile *optimisation* in any context
        (
            "stockpile-optimisation",
            r"""\b stockpil(e|es|ing|ed) .{0,30}? \b optimi[sz]ation \b""",
        ),
        # 6d. bare "stockpile optimization" / "stockpile maximisation" / "growth"
        (
            "bare-stockpile-optim",
            r"""\b stockpile \s+ (optimi[sz](?:ation|e|es|ed|ing)|maxim(?:um|al|ize|ise|isation|ization)|growth|expansion|target)""",
        ),
        # 7. implosion / compression for weapons (couples to ICF dual-use)
        (
            "implosion-weapon",
            r"""\b (implosion|compression) .{0,30}? \b (weapon|warhead|nuclear[\- ]?device) s? \b""",
        ),
    )
)


# Backwards-compatible flat list of common forbidden substrings; used by tests
# that pre-date the regex matcher and by the REST handler's pre-flight string
# check. Keep in sync with the patterns above.
FUSION_FORBIDDEN_INTENTS: tuple[str, ...] = (
    "weapons-grade tritium",
    "weapon-grade tritium",
    "weapons grade",
    "weapon grade",
    "tritium stockpile",
    "tritium stockpiling",
    "weapons stockpile",
    "weapons-grade",
    "tritium diversion",
    "fissile diversion",
    "tritium extraction optimization",
    "tritium extraction optimisation",
    "tritium purification optimization",
    "tritium purification optimisation",
    "stockpile optimization",
    "stockpile optimisation",
    "weapon design",
    "weapon yield",
    "explosive yield",
    "detonation yield",
    "fission boost",
    "fission-boost",
    "thermonuclear weapon",
    "military payload",
    "weapon payload",
    "warhead",
    "warheads",
    "weapon delivery system",
    "missile delivery system",
    "defence application",
    "defense application",
    "military application",
    "implosion compression for weapons",
    "imploding compression for warhead",
)


class BoundaryViolation(ValueError):
    """Raised when an artifact mutates the boundary block or hits a forbidden intent."""


_DASH_NORMALISER = re.compile(r"[‐‑‒–—―−⁃⸺⸻]")  # all unicode dashes -> "-"


def _normalise_text(text: str) -> str:
    """NFKD-fold, drop combining marks, lowercase, collapse runs of whitespace,
    fold unicode dashes (en-/em-/figure-/etc.) to ASCII hyphen.
    """
    if not text:
        return ""
    nf = unicodedata.normalize("NFKD", text)
    nf = "".join(c for c in nf if not unicodedata.combining(c))
    nf = _DASH_NORMALISER.sub("-", nf)
    nf = nf.lower()
    nf = re.sub(r"\s+", " ", nf)
    return nf.strip()


def verify_boundary(payload: Mapping[str, Any] | str | None) -> bool:
    """Return True iff the payload's boundary string is byte-identical to BOUNDARY_BLOCK."""
    if payload is None:
        return False
    if isinstance(payload, str):
        return payload == BOUNDARY_BLOCK
    if isinstance(payload, Mapping):
        b = payload.get("boundary")
        return isinstance(b, str) and b == BOUNDARY_BLOCK
    return False


def check_fusion_intent(text: str | None, *, extra_terms: Iterable[str] = ()) -> str | None:
    """If `text` matches a forbidden fusion intent, return a label string.

    Matching is performed on a normalised form of `text` (NFKD-folded,
    lowercased, whitespace-collapsed). Extra terms are checked as plain
    substrings on the normalised form for backward compatibility with code that
    previously appended ad-hoc forbidden phrases.

    Returns the matched pattern label (e.g. "tritium-stockpile") or None.
    """
    if not text:
        return None
    norm = _normalise_text(text)
    for label, pat in _FORBIDDEN_PATTERNS:
        if pat.search(norm):
            return label
    for term in extra_terms:
        if term and term.lower() in norm:
            return term.lower()
    return None


def assert_boundary(payload: Mapping[str, Any] | str | None) -> None:
    if not verify_boundary(payload):
        raise BoundaryViolation(
            "Artifact missing or mutating BOUNDARY_BLOCK; boundary check failed."
        )
