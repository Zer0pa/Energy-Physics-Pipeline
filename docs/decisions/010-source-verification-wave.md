# 010 — Source manifest verification wave

**Boundary:** Research infrastructure for in silico energy science: electrochemical conversion (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. No regulatory certification claims. No clinical or human-subject use. Defence / weapons applications are out of scope under operator policy.

## Decision

The 41 entries in `sources_log/seed.jsonl` were produced manually with placeholder sha256 digests (`sha256:0000...0000`). To make the license trail content-addressable, we run a `tools/verify_sources.py` script that:

1. Fetches every URI via `urllib.request` (no body retained — only sha256).
2. Replaces the placeholder with `sha256:<real-hex>`.
3. Updates `retrieval_method` from `manual` to `api`.
4. Updates `retrieved_at` to the actual fetch timestamp.
5. Writes the verified copy to `sources_log/seed_verified.jsonl` (does not overwrite the seed).
6. Emits `sources_log/verification_summary.md` with a per-entry verdict.

Failure modes are recorded inline (HTTP 4xx/5xx, URL errors, timeouts) and the corresponding entry retains its placeholder digest with the failure reason appended to `rights_notes`. The verified copy is never the authoritative source — `seed.jsonl` stays as the operator-curated set.

## Why a separate file

`seed.jsonl` is the operator's curated, hand-checked list. The verified file diverges by run; pinning real sha256s in the seed would conflate "what should be here" with "what we observed at fetch time." Two files capture both intents.

## Run

```bash
.venv/bin/python tools/verify_sources.py
```

First run on 2026-04-30: 35 of 41 verified; 6 returned HTTP 404 (URL drift since PRD authoring). Failures recorded; no false negatives.
