# ADR 004 — Data Sovereignty

**Status:** Active  
**Date:** 2026-04-30  
**Source:** PRD §Data Sovereignty; PRD §Open Questions (item 4)

---

## Context

The pipeline processes customer-supplied material and operating-condition data alongside Zer0pa-owned research artifacts and model weights. Clear ownership defaults are required to prevent accidental data co-mingling, protect customer confidentiality, and satisfy audit requirements for research artifacts.

---

## Defaults

### Customer Data Ownership

All raw inputs supplied by a customer (material compositions, experimental I-V curves, process parameters, device geometry files, operational telemetry) are **customer-owned by default**. Zer0pa holds no rights to these inputs beyond those strictly required to execute the requested simulation campaign.

- Customer-owned data is tagged `rights_label=customer_confidential` in `ReasonerTuple` and in KG nodes.
- Customer data is stored in isolated per-customer namespaces within the pipeline's artifact store. Cross-customer data access is prohibited without explicit written consent from both customers.
- Customer data is not used to improve Zer0pa shared models or weights without an explicit opt-in agreement recorded in writing and referenced via a `kg://rights-grant/<customer-id>` URI.

### Zer0pa Research Artifact Ownership

Simulation results, calibrated model parameters, reduced observables, and knowledge-graph nodes produced by the pipeline using Zer0pa infrastructure and Zer0pa-owned models are **Zer0pa-owned by default**, unless a specific customer agreement transfers ownership.

- Zer0pa-owned artifacts are tagged `rights_label=internal`.
- Published research artifacts (papers, public datasets) transition to `rights_label=public` upon publication.

### Fine-Tune and Posterior Isolation

MLIP fine-tunes (LoRA, full fine-tune, posterior samples) produced on customer data are **customer-owned isolated artifacts by default**. They are stored in a dedicated per-customer isolated store and are never merged into Zer0pa shared model checkpoints without explicit customer opt-in.

- Each fine-tune run produces a `ModelCheckpoint` KG node tagged with the originating customer namespace.
- Opt-in sharing requires a signed agreement; the agreement URI is recorded in `backend.license_evidence_uri` of the relevant envelope.

### Audit-Trail Joint Access

Both the customer and Zer0pa hold joint read access to the audit trail for any campaign run on customer data. This includes:

- The `UniversalLayerEnvelope` records for all layers.
- The `ReasonerTuple` records produced during the campaign.
- The `FalsifierResult` and `DisagreementRecord` KG nodes.
- The `SourceManifest` records for all tools used.

Audit-trail joint access does not grant the customer access to Zer0pa's internal model weights or to other customers' data.

---

## Open Question 4 (PRD §Open Questions)

> "MLIP fine-tunes and posteriors: customer-owned isolated artifacts by default, or shared-core improvement with opt-in?"

**Current default (this ADR):** Customer-owned isolated artifacts by default. Shared-core improvement requires explicit customer opt-in with written agreement. This decision may be revisited when the first commercial MLIP fine-tune campaign is underway and the customer's preference is known.
