"""Data-pointer manifest adapters — OPTIMADE / Materials Project / NOMAD.

Wave 4 §7: every PRD-listed structure-data source must have a manifest-only
pointer adapter that stores no bulk data, only metadata + a verifiable
provenance handle.

The pointer manifests carry:
  * source_kind   — "optimade", "materials_project", "nomad"
  * source_uri    — the canonical query URL (no payload bytes ever stored)
  * query_string  — the OPTIMADE/MP/NOMAD query DSL string the caller used
  * checksum      — sha256 of the canonical manifest body itself (not the data)
  * license       — license/rights notes per upstream (see sources_log)
  * downstream_layer — which pipeline layer consumes the materials this
                       pointer references (typically L1 electronic structure)
  * accessed_at   — ISO-8601 timestamp

These are intentionally manifest-only. Bulk download is a Runpod-side concern
because cross-section / structure datasets are GB-scale and policy-restricted
on the lab Mac (`ENERGY_ALLOW_BULK_DATA=false`).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from energy_pipeline.l6 import accept_envelope
from energy_pipeline.schemas import (
    BackendBlock,
    Domain,
    ExecutionMode,
    GateStatus,
    LayerLevel,
    LicenseClass,
    Mode,
    SubVertical,
    UniversalLayerEnvelope,
)
from energy_pipeline.schemas.canonical import sha256_of
from energy_pipeline.schemas.envelope import (
    FalsificationBlock,
    IOBlock,
    ProvenanceBlock,
)


PointerKind = Literal["optimade", "materials_project", "nomad"]


@dataclass(frozen=True)
class DataPointerSpec:
    kind: PointerKind
    source_uri: str
    query_string: str
    intended_downstream_layer: LayerLevel = LayerLevel.L1
    intended_downstream_domain: Domain = Domain.battery
    # Empty default means "use the per-kind canonical license below"
    license_spdx_or_text: str = ""
    rights_notes: str = ""
    notes: dict[str, Any] | None = None
    campaign_id: str = "data-pointer-manifest"


# ---------------------------------------------------------------------------
# Per-kind canonical defaults — used when a caller does not specify them.
# ---------------------------------------------------------------------------


_DEFAULTS: dict[PointerKind, dict[str, Any]] = {
    "optimade": {
        "tool": "OPTIMADE-pointer",
        "tool_version": "v1.2",
        "source_uri": "https://providers.optimade.org/index/links",
        "license_spdx_or_text": "varies-per-provider",
        "license_evidence_uri": "kg://license-grant/optimade-public-aggregator",
        "rights_notes": (
            "OPTIMADE federates open-data crystal-structure providers. "
            "Per-provider license applies — store only the query, not the bytes."
        ),
    },
    "materials_project": {
        "tool": "Materials-Project-pointer",
        "tool_version": "MP-API-2025",
        "source_uri": "https://api.materialsproject.org",
        "license_spdx_or_text": "CC-BY-4.0",
        "license_evidence_uri": "kg://license-grant/materials-project-CC-BY-4.0",
        "rights_notes": (
            "Materials Project structure data licensed CC-BY-4.0 per "
            "https://next-gen.materialsproject.org/about/license. Citation required."
        ),
    },
    "nomad": {
        "tool": "NOMAD-pointer",
        "tool_version": "v1.3",
        "source_uri": "https://nomad-lab.eu/prod/v1/api/v1",
        "license_spdx_or_text": "CC-BY-4.0",
        "license_evidence_uri": "kg://license-grant/nomad-CC-BY-4.0",
        "rights_notes": (
            "NOMAD Repository data is published under CC-BY-4.0 by default. "
            "Per-entry license can vary; per-record check required before "
            "redistribution. https://nomad-lab.eu/nomad-lab/about.html"
        ),
    },
}


class DataPointerAdapter:
    """Emit a manifest-only envelope describing a query into one of the three
    structure-data sources (OPTIMADE, Materials Project, NOMAD).

    No bulk data is ever fetched, parsed, or stored. The envelope captures the
    query as the input payload and the canonical manifest as the output payload.
    """

    ADAPTER_NAME = "electrochem.data_pointers"

    def emit(
        self,
        spec: DataPointerSpec,
        *,
        write_audit: bool = True,
        write_kg: bool = True,
    ) -> UniversalLayerEnvelope:
        defaults = _DEFAULTS[spec.kind]
        manifest = {
            "source_kind": spec.kind,
            "source_uri": spec.source_uri or defaults["source_uri"],
            "query_string": spec.query_string,
            "license_spdx_or_text": spec.license_spdx_or_text or defaults["license_spdx_or_text"],
            "rights_notes": spec.rights_notes or defaults["rights_notes"],
            "intended_downstream_layer": spec.intended_downstream_layer.value,
            "intended_downstream_domain": spec.intended_downstream_domain.value,
            "accessed_at": datetime.now(timezone.utc).isoformat(),
            "bulk_data_stored": False,
            "notes": dict(spec.notes or {}),
        }
        manifest_sha = sha256_of(manifest)

        env = UniversalLayerEnvelope(
            campaign_id=spec.campaign_id,
            sub_vertical=SubVertical.electrochemistry,
            layer=spec.intended_downstream_layer,
            domain=spec.intended_downstream_domain,
            mode=Mode.engineering_stub,
            backend=BackendBlock(
                adapter=f"{self.ADAPTER_NAME}::{spec.kind}",
                tool=defaults["tool"],
                tool_version=defaults["tool_version"],
                execution_mode=ExecutionMode.local_cpu,
                license_class=LicenseClass.A,
                license_evidence_uri=defaults["license_evidence_uri"],
            ),
            inputs=IOBlock(
                payload={
                    "kind": spec.kind,
                    "query_string": spec.query_string,
                    "intended_downstream_layer": spec.intended_downstream_layer.value,
                    "intended_downstream_domain": spec.intended_downstream_domain.value,
                }
            ),
            outputs=IOBlock(
                payload={
                    **manifest,
                    "manifest_sha256": manifest_sha,
                    "manifest_only": True,
                }
            ),
            falsification=FalsificationBlock(
                gate_status=GateStatus.warn,
                scientific_valid=False,
                unit_check_passed=True,
                conservation_check_passed=True,
                boundary_check_passed=True,
            ),
            provenance=ProvenanceBlock(
                agent_id=self.ADAPTER_NAME,
                model_id="pointer-manifest",
                git_sha="local",
                input_hash=sha256_of({"kind": spec.kind, "query": spec.query_string}),
                output_hash=manifest_sha,
                config_hash="0" * 64,
                created_at=datetime.now(timezone.utc),
            ),
        ).finalize()

        return accept_envelope(env, write_audit=write_audit, write_kg=write_kg)


# ---------------------------------------------------------------------------
# Convenience factories
# ---------------------------------------------------------------------------


def optimade_pointer(
    *,
    query_string: str,
    intended_downstream_layer: LayerLevel = LayerLevel.L1,
    intended_downstream_domain: Domain = Domain.battery,
    notes: Optional[dict[str, Any]] = None,
) -> DataPointerSpec:
    return DataPointerSpec(
        kind="optimade",
        source_uri=_DEFAULTS["optimade"]["source_uri"],
        query_string=query_string,
        intended_downstream_layer=intended_downstream_layer,
        intended_downstream_domain=intended_downstream_domain,
        rights_notes=_DEFAULTS["optimade"]["rights_notes"],
        notes=notes or {},
    )


def materials_project_pointer(
    *,
    query_string: str,
    intended_downstream_layer: LayerLevel = LayerLevel.L1,
    intended_downstream_domain: Domain = Domain.battery,
    notes: Optional[dict[str, Any]] = None,
) -> DataPointerSpec:
    return DataPointerSpec(
        kind="materials_project",
        source_uri=_DEFAULTS["materials_project"]["source_uri"],
        query_string=query_string,
        intended_downstream_layer=intended_downstream_layer,
        intended_downstream_domain=intended_downstream_domain,
        rights_notes=_DEFAULTS["materials_project"]["rights_notes"],
        notes=notes or {},
    )


def nomad_pointer(
    *,
    query_string: str,
    intended_downstream_layer: LayerLevel = LayerLevel.L1,
    intended_downstream_domain: Domain = Domain.battery,
    notes: Optional[dict[str, Any]] = None,
) -> DataPointerSpec:
    return DataPointerSpec(
        kind="nomad",
        source_uri=_DEFAULTS["nomad"]["source_uri"],
        query_string=query_string,
        intended_downstream_layer=intended_downstream_layer,
        intended_downstream_domain=intended_downstream_domain,
        rights_notes=_DEFAULTS["nomad"]["rights_notes"],
        notes=notes or {},
    )
