# ADR 005 — Deviations from PRD

**Status:** Active (running log)  
**Date created:** 2026-04-30

---

## Purpose

This document records any deviations from the PRD made by the overnight executor or subsequent subagents. Each entry must include a timestamp, the agent or subagent responsible, the PRD section deviated from, and the rationale.

The overnight executor proceeds under PRD defaults and does not wait for open-question resolution (PRD §Open Questions: "The overnight executor must not wait for these answers. It proceeds under the defaults in this PRD and logs decisions.").

---

## Deviation Log

_No deviations recorded at 2026-04-30T00:00:00Z. All files produced by the seed-log executor conform to the PRD's License And Status Findings section and the schema contracts defined in energy_pipeline/schemas/._

---

## Instructions for Future Entries

When a subagent or executor deviates from the PRD, append an entry in this format:

```
### DEV-<NNN> — <short title>
**Date:** YYYY-MM-DDThh:mm:ssZ
**Agent:** <agent or subagent name>
**PRD section:** §<section name>
**Deviation:** <what was done differently>
**Rationale:** <why this deviation was necessary or beneficial>
**Reversible:** yes | no | partial
```
