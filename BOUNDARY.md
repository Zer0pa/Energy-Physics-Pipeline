# Boundary Block — Energy Physics Pipeline

**Verbatim block (must appear in every artifact):**

> Research infrastructure for in silico energy science: electrochemical conversion (batteries, green hydrogen electrolysis, fuel cells, solid oxide cells, photovoltaics, thermoelectrics) and fusion / plasma physics. Outputs are research artifacts. No regulatory certification claims. No clinical or human-subject use. Defence / weapons applications are out of scope under operator policy.

**Authority:** This block is the authority of last resort. Any artifact, schema, REST stub, MCP tool, audit row, or KG node missing or altering this block fails its boundary check.

**Fusion specialisation rule:** Fusion blanket and breeding-blanket simulation is allowed as research. Weapons-grade tritium simulation, stockpile optimization, extraction/purification optimization, diversion, military use, and defence applications are blocked. The pipeline must emit no technical optimization output for blocked intents.

**Implementation:** see `energy_physics_pipeline/boundary.py` — `BOUNDARY_BLOCK`, `verify_boundary(payload)`, and `FUSION_FORBIDDEN_INTENTS`.
