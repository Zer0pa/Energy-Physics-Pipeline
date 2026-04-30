# Changelog

## [unreleased] — overnight CPU-first build

### Added — foundation (chief engineer / Opus Max)
- Boundary block (`BOUNDARY_BLOCK`) and verifier (`verify_boundary`, `check_fusion_intent`).
- Canonical-JSON serialiser + content-addressable `sha256:` IDs.
- `UniversalLayerEnvelope` + `DeviceResponseObject` + `CrossModelDisagreementRecord`
  + `EarlyWarningSignal` + `SourceManifest` + `ReasonerTuple` Pydantic-v2 schemas.
- `AuditWriter` (JSONL + DuckDB) with mandatory boundary check + provenance fields.
- `KGStore` (JSONL + NetworkX MultiDiGraph) with the PRD's 14 node types and 12 edge
  types, plus GraphML export.
- L6 control plane: `EnergyConfig` (ENERGY_* env flags), `AdapterRegistry` seeded with
  17 adapters across both sub-verticals, falsifier router with 4 generic falsifiers.
- FastAPI REST stubs for L1-L5 endpoints (electrochem + fusion) with config-flag
  cutover scaffolding for Runpod backends.
- Typer CLI: `health`, `boundary`, `registry`, `smoke`, `serve-rest`,
  `falsification-wave`, `electrochem-e2e`, `fusion-phase0`.
- Foundation contract tests: 61 tests covering schemas, audit, KG, L6, REST stubs,
  plug-replaceability, canonical JSON.

### Added — adapter stacks (parallel subagents)

#### Electrochem L1-L5 (Sonnet subagent — DONE)
- L1: `ElectronicStructureAdapter` (PySCF 2.13.0 H2 RHF/STO-3G real CPU; Marcus / optical-spectrum analytic fixtures).
- L2: `MLIPManifestAdapter` (manifest-only with license gate); deterministic synthetic MSD.
- L3: parser-first VTK/HDF5 manifest with synthetic tortuosity / effective diffusivity.
- L4: `PyBaMMBatteryAdapter` (DFN P2D Chen2020 real CPU), `SolcorePvAdapter` (Solcore failed pip on 3.13 → analytic Shockley-Queisser fallback), `CanteraSofcAdapter` (GRI30 real CPU), `PemAdapter` (analytic Butler-Volmer; AlphaPEM GPL-3 isolated), `ThermoelectricAdapter` (analytic).
- L5: `PyPSALcoeAdapter` (PyPSA 1.2.0 + HiGHS real CPU + 200-sample MC LCOE), `PvlibYieldAdapter` (pvlib 0.15.1 Ineichen Sandton clear-sky), `PySAMLcoeAdapter` (analytic).
- 29 tests green in 5.8s.

#### Fusion L1-L5 + reasoning bench (Opus subagent — STALLED mid-test-write; orchestrator finished tests)
- L1: `OpenMcManifestAdapter` (CPU-fixture transport + nuclear library manifests for ENDF/B-VIII.1, JEFF-4.0, JENDL-5, FENDL-3.2c, TENDL, IRDFF-II with sha256 placeholders).
- L2: `TglfReducedAdapter` (analytic gyroBohm reduced transport), `CgyroNonlinearAdapter` (REST-stub Runpod-parked), `GyroSwinSurrogateAdapter` (REST-stub).
- L3: `FreeGS4eAdapter` (freegs 0.8.2 diverted equilibrium real CPU), `JorekDryRunAdapter`, `BoutDryRunAdapter` (parser-only).
- L4: `imas_fixture.write_fixture/read_fixture` (netCDF4 IDS-shaped equilibrium + core_profiles fixture, COCOS=11, DD=3.41.0), `ImasPythonAdapter`, `OmasConverterAdapter`, `ReducedTransportCpuAdapter` (0D ITER H98(y,2) scaling — emits envelope + DRO), `DuqtoolsConfigAdapter`.
- L5: `ParamakGeometryAdapter` (Paramak when installable; CSG fallback), `OpenmcCsgFixedSourceAdapter`, `OpenmcR2sAdapter` (analytic activation stub).
- `FusionReasoningBench`: 50 tasks across 5 categories (imas_ids, q_profile, disruption, blanket_tbr, forbidden); rules-based scorer; **refusal_recall=1.0** on the 10 forbidden tasks.
- 20 tests green in 15.7s.

#### MCP server suite (Sonnet subagent — DONE)
- `mcp 1.27.0` FastMCP installed; 9 servers, 9 tools.
- Servers: `pybamm_mcp`, `pvlib_mcp`, `solcore_mcp`, `cantera_mcp`, `pypsa_mcp`, `pysam_mcp`, `openmc_mcp`, `imas_codex_mcp` (read-only), `aiida_mcp`.
- Boundary block in every tool description; fusion intent gate on fusion tools.
- 33 tests green in 3.6s.

#### TDA + 12-test falsification wave (Sonnet subagent — DONE)
- ripser+persim CPU detector with Takens embedding; persistence entropy + max H0/H1 lifetimes.
- Cross-domain pre-canned configs for battery thermal runaway, fuel-cell membrane breakdown, electrolyser stack degradation, SOFC delamination, plasma disruption.
- No-leakage guard (no future leakage, pulse-level split, normalisation fitted on train only).
- 12-of-12 falsification wave passes (boundary mutation, license promotion, stub validity, units, COCOS, T<0, n<0, fill-factor>1, above-Carnot, SoC out-of-range, missing IDS, cross-model disagreement).
- 63 tests green in 7.0s.

#### Source manifests + reasoner curator + decision log (Sonnet subagent — DONE)
- 41 source manifests covering every tool referenced in the PRD (PySCF through JEFF-4.0).
- 41 license findings with per-tool class A-E + SPDX + verdict + promotion status.
- `SourceLog`, `license_gate`, `reasoner_curator` helpers.
- 4 decision docs: 000-overview, 001-license-policy, 004-data-sovereignty, 005-deviations-from-prd.
- 63 tests green in 1.2s.

### Added — handoff
- `BOUNDARY.md` — verbatim boundary block + fusion specialisation rule.
- `scripts/full_check.sh`, `scripts/clean_runtime.sh`, `scripts/quick_demo.py`.

### Notes
- Python 3.13.12 venv (system 3.9 supported but PyBaMM/Cantera prefer 3.11+).
- All artifacts carry the boundary block verbatim. Mutation -> boundary fails closed.
- No bulk datasets vendored. All external sources are manifest-only with sha256
  placeholders until a separate verification wave fills real checksums.
- Class C/D/E backends gated: scientific mode requires `kg://license-grant/*` or
  `https://` or `file://` evidence URI.
- Stubs cannot set `scientific_valid=True` (validator-enforced).
