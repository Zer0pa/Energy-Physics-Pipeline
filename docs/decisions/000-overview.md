# Architecture Decision Log — Overview

The Zer0pa Energy CPU-first pipeline is a research infrastructure for in-silico energy science covering electrochemical conversion (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma physics (PRD §Architecture). Every artifact emitted by the pipeline carries the verbatim `BOUNDARY_BLOCK` string; all outputs are research artifacts with no regulatory certification claims and no defence / weapons applications. The pipeline is structured as a layered adapter system (L1–L6) where every layer emits a `UniversalLayerEnvelope` and the L4→L5 handoff uses a `DeviceResponseObject`; the knowledge graph (`KGStore`) records every node and edge in append-only JSONL with full provenance. Source manifests (`SourceManifest`) are the authoritative record of every external tool, dataset, or model touched by the pipeline; license verdicts (`license_findings.jsonl`) and the license gate (`LicenseGateError`) enforce the class A–E policy at promotion time.

## Decision Index

- [001-license-policy.md](001-license-policy.md) — License class A–E definitions, C/D/E promotion gate, and excluded tools.
- [002 (reserved)](002-reserved.md) — Reserved for future adapter boundary decisions.
- [003 (reserved)](003-reserved.md) — Reserved for future KG schema evolution decisions.
- [004-data-sovereignty.md](004-data-sovereignty.md) — Customer data ownership, Zer0pa ownership, fine-tune isolation, and audit-trail joint access.
- [005-deviations-from-prd.md](005-deviations-from-prd.md) — Running log of executor deviations from PRD with rationale.
