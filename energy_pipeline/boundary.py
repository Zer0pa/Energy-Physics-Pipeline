"""Boundary block — the authority of last resort.

Every artifact emitted by the pipeline must carry the verbatim BOUNDARY_BLOCK string.
Mutation of the string fails the boundary check.

Fusion intents that are explicitly blocked are listed in FUSION_FORBIDDEN_INTENTS.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

BOUNDARY_BLOCK: str = (
    "Research infrastructure for in silico energy science: electrochemical conversion "
    "(batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, "
    "thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. "
    "No regulatory certification claims. No clinical or human-subject use. "
    "Defence / weapons applications are out of scope under operator policy."
)

FUSION_FORBIDDEN_INTENTS: tuple[str, ...] = (
    "weapons-grade tritium",
    "tritium stockpile",
    "tritium diversion",
    "tritium extraction optimization",
    "tritium purification optimization",
    "stockpile optimization",
    "weapon design",
    "weapon yield",
    "explosive yield",
    "fission boost",
    "thermonuclear weapon",
    "military payload",
    "warhead",
    "implosion compression for weapons",
    "delivery system",
    "defence application",
    "defense application",
)


class BoundaryViolation(ValueError):
    """Raised when an artifact mutates the boundary block or hits a forbidden intent."""


def verify_boundary(payload: Mapping[str, Any] | str | None) -> bool:
    """Return True iff the payload's boundary string is byte-identical to BOUNDARY_BLOCK.

    Accepts either a raw string or a mapping containing a 'boundary' key. Anything else
    is considered missing-boundary and fails.
    """
    if payload is None:
        return False
    if isinstance(payload, str):
        return payload == BOUNDARY_BLOCK
    if isinstance(payload, Mapping):
        b = payload.get("boundary")
        return isinstance(b, str) and b == BOUNDARY_BLOCK
    return False


def check_fusion_intent(text: str | None, *, extra_terms: Iterable[str] = ()) -> str | None:
    """If `text` matches a forbidden fusion intent (case-insensitive), return the matched term.

    Returns None if clean.
    """
    if not text:
        return None
    s = text.lower()
    for term in (*FUSION_FORBIDDEN_INTENTS, *(t.lower() for t in extra_terms)):
        if term in s:
            return term
    return None


def assert_boundary(payload: Mapping[str, Any] | str | None) -> None:
    if not verify_boundary(payload):
        raise BoundaryViolation(
            "Artifact missing or mutating BOUNDARY_BLOCK; boundary check failed."
        )
