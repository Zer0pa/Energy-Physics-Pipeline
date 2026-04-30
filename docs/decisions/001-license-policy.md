# ADR 001 — License Policy: Class A–E and Promotion Gate

**Status:** Active  
**Date:** 2026-04-30  
**Source:** PRD §License And Status Findings; `energy_pipeline/schemas/envelope.py` (`_class_cde_promotion_gate`); `energy_pipeline/adapters/shared/license_gate.py`

---

## Context

The pipeline integrates scientific software spanning a wide range of open-source licenses. A uniform classification scheme is required so that every adapter, stub, and tool can be evaluated for commercial use, copyleft isolation, and scientific-mode promotion eligibility without bespoke review on each integration.

---

## License Class Definitions

| Class | License type | Commercial use | Scientific-mode promotion | Isolation required |
|-------|-------------|----------------|--------------------------|-------------------|
| **A** | Permissive (MIT, BSD-2/3, Apache-2.0, Public Domain, Simplified BSD) | Yes | Allowed without evidence URI | No |
| **B** | Copyleft (GPL-2, GPL-3, AGPL) | Blocked in linked product | Blocked without explicit isolation/grant evidence URI | Yes — process boundary or replace |
| **C** | Weak copyleft / conditional (LGPL-2.1, LGPL-3, FAIR Chemistry License, OECD/NEA, Llama-inherited) | Conditional on LGPL boundary or licensor grant | Blocked without evidence URI | LGPL boundary required |
| **D** | Ambiguous / unverified (MIT-indicated but top-level LICENSE absent, unknown pyproject) | Pending verification | Blocked pending verification | Productization-gated |
| **E** | Excluded / academic-only / no visible license | No | Excluded | Not integrated until license grant |

---

## Class C/D/E Promotion Gate

A tool with license_class C, D, or E **cannot** be used in `mode=scientific` inside a `UniversalLayerEnvelope` unless `backend.license_evidence_uri` begins with one of:

- `file://` — local signed grant document
- `https://` — publicly accessible license confirmation page or signed agreement
- `kg://license-grant/` — internal knowledge-graph grant node

This gate is enforced at two layers:

1. **Schema layer** — `UniversalLayerEnvelope._class_cde_promotion_gate()` model validator (energy_pipeline/schemas/envelope.py).
2. **Application layer** — `assert_promotion_allowed()` in energy_pipeline/adapters/shared/license_gate.py.

Both layers raise immediately; neither can be bypassed without a valid evidence URI.

---

## Currently Excluded Tools

The following tools are Class E and **disabled by default** until a specific license grant is obtained and recorded in `kg://license-grant/`:

| Tool | Reason | Primary source |
|------|--------|----------------|
| **SCAPS-1D** | Academic-only; no negotiated commercial rights | https://scaps.elis.ugent.be |
| **GENE** | Academic/evaluation only; non-academic entities must approach GDT | https://www.genecode.org/license.html |
| **PF-PINO** | No visible root LICENSE in repository | https://github.com/NanxiiChen/PF-PINO |
| **PiNN/PiNet2** | License not confirmed from primary source | https://github.com/Teoroo-CMC/PiNN |

The following tool is Class D (ambiguous), non-commercial only, and **not MVP-gating**:

| Tool | Reason | Primary source |
|------|--------|----------------|
| **AQCat25** | CC-BY-NC-SA-4.0 — non-commercial only | https://huggingface.co/datasets/SandboxAQ/aqcat25-dataset |

---

## Notable Corrections from PRD §License And Status Findings

- **AlphaPEM** — GPL-3.0 (was previously unlabelled); Class B — isolate or replace.
- **LBPM** — GPL-3.0, NOT Apache as previously stated; Class B.
- **DAGMC** — Simplified BSD, NOT MIT; Class A.
- **MACE** — Code is MIT (Class A); weights may be non-commercial or research-gated — separate manifests required per weight set.
- **OC25/eSEN model** — FAIR Chemistry License (Class C); ZA production deploy requires gated acceptance verification.
- **DeepSeek-R1-Distill-Llama-70B** — Inherits Llama licensing (Class C); research/prototype only; keep Qwen-family Apache alternatives.
