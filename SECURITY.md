# Security & Boundary Posture — Energy Physics Pipeline

## Boundary block (authority of last resort)

Every artifact carries the verbatim boundary block. See `BOUNDARY.md`. Mutation of the
block is detected by Pydantic validators on every schema (`UniversalLayerEnvelope`,
`DeviceResponseObject`) and by the audit writer (rejects any payload missing the block).

## Fusion-specific intent gate

Forbidden intents (case-insensitive substring match):

- weapons-grade tritium / stockpile / diversion / extraction optimization /
  purification optimization
- weapon design / yield / fission boost / thermonuclear weapon
- military payload / warhead / delivery system
- defence / defense application

Enforcement points:

1. `energy_physics_pipeline.boundary.check_fusion_intent(text)` — used in REST stubs
   (`/v1/fusion/...`), every fusion adapter L1/L4/L5 input pre-flight, every MCP fusion
   tool call.
2. Returns the matched forbidden term; raises `BoundaryViolation` or HTTP 403.
3. The pipeline emits **no** technical optimization output for blocked intents.

## License gate

Class A (permissive — Apache-2.0, MIT, BSD-3): no gate.
Class B (copyleft permissive boundary — LGPL): allowed in `scientific` mode if linked
dynamically; AGPL and GPL handled by isolation (subprocess) or replacement.
Class C/D/E (academic-only, vendor-license, unknown): blocked from `scientific` mode
without `kg://license-grant/...` or `https://...` or `file://...` evidence URI.

## Data sovereignty

- Customer owns proprietary input structures, pulse/scenario configs, customer lab
  data, and campaign-specific outputs.
- Zer0pa owns orchestration code, generic schemas, adapter abstractions, non-customer-
  specific priors, anonymized method improvements only where contract permits.
- Fine-tunes default to customer-isolated artifacts unless customer opts into shared-
  core improvement.

## Reporting

Internal: file an issue tagged `boundary` or `license`. External: do not file public
disclosures of internal boundary or licence enforcement details.
