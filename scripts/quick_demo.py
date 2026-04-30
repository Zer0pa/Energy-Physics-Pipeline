"""Stand-alone demo: emit one full envelope+DRO+audit+KG cycle without adapters.

Used as a self-contained smoke check that the foundation is correct independent of any
adapter or subagent work. Not a substitute for the integration tests.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from uuid import uuid4

from energy_pipeline.audit import AuditWriter
from energy_pipeline.boundary import BOUNDARY_BLOCK
from energy_pipeline.kg import KGStore
from energy_pipeline.schemas import (
    BackendBlock,
    Curve,
    CurveType,
    DeviceFamily,
    DeviceResponseObject,
    Domain,
    ExecutionMode,
    GateStatus,
    LayerLevel,
    LicenseClass,
    Mode,
    ScalarMetrics,
    SubVertical,
    UniversalLayerEnvelope,
)
from energy_pipeline.schemas.dro import (
    Axis,
    CurveAxis,
    DroAuditBlock,
    OperatingConditions,
    ResponseBlock,
)
from energy_pipeline.schemas.envelope import (
    FalsificationBlock,
    IOBlock,
    ProvenanceBlock,
)


def main() -> int:
    aw = AuditWriter()
    kg = KGStore()

    # Synthetic Butler-Volmer V(j) for a PEM electrolyser at 80°C
    j = [0.0, 100.0, 500.0, 1000.0, 2000.0]  # A/m^2
    eta_act = [0.0, 0.18, 0.31, 0.40, 0.49]
    eta_ohm = [0.0, 0.05, 0.25, 0.50, 1.00]
    V = [1.23 + a + o for a, o in zip(eta_act, eta_ohm)]

    env = UniversalLayerEnvelope(
        campaign_id="quick-demo",
        sub_vertical=SubVertical.electrochemistry,
        layer=LayerLevel.L4,
        domain=Domain.green_h2,
        mode=Mode.engineering_stub,
        backend=BackendBlock(
            adapter="quick-demo::butler-volmer",
            tool="analytic-bv",
            tool_version="0.0.1",
            execution_mode=ExecutionMode.local_cpu,
            license_class=LicenseClass.A,
            license_evidence_uri="kg://license-grant/quick-demo",
        ),
        inputs=IOBlock(payload={"T_C": 80, "membrane": "Nafion117"}),
        outputs=IOBlock(
            payload={
                "quantities": {
                    "j_max": {"value": max(j), "unit": "A/m^2"},
                    "V_at_j_max": {"value": V[-1], "unit": "V"},
                }
            }
        ),
        falsification=FalsificationBlock(
            gate_status=GateStatus.pass_,
            scientific_valid=False,
            unit_check_passed=True,
            conservation_check_passed=True,
            boundary_check_passed=True,
        ),
        provenance=ProvenanceBlock(
            agent_id="quick-demo",
            model_id="analytic",
            git_sha="local",
            input_hash="0" * 64,
            output_hash="0" * 64,
            config_hash="0" * 64,
        ),
    ).finalize()

    aw.write_event("envelope.v0.1", env.model_dump(mode="json"))
    kg.add_node("ToolAdapter", "analytic-bv", {"tool": "analytic-bv"}, boundary_required=False)
    kg.add_node("SimulationRun", f"sim-{env.run_id}", env.model_dump(mode="json"))
    kg.add_edge("USED_TOOL", f"sim-{env.run_id}", "analytic-bv")

    dro = DeviceResponseObject(
        sub_vertical=SubVertical.electrochemistry,
        device_family=DeviceFamily.pem_electrolyzer,
        operating_conditions=OperatingConditions(
            axes=[Axis(name="j", unit="A/m^2", values=j)], fixed={"T_C": 80}
        ),
        response=ResponseBlock(
            curves=[
                Curve(
                    curve_type=CurveType.V_vs_j,
                    x=CurveAxis(quantity="j", unit="A/m^2", values=j),
                    y=CurveAxis(quantity="V", unit="V", values=V),
                )
            ],
            scalar_metrics=ScalarMetrics(
                ocv_V=1.23, overpotential_V_at_target_j=V[-1] - 1.23
            ),
        ),
        audit=DroAuditBlock(envelope_id=env.envelope_id or "sha256:none"),
    ).finalize()

    aw.write_event("dro.v0.1", dro.model_dump(mode="json"))
    kg.add_node(
        "DeviceResponseObject", f"dro-{dro.dro_id}", dro.model_dump(mode="json")
    )
    kg.add_edge("PRODUCED", f"sim-{env.run_id}", f"dro-{dro.dro_id}")

    print(f"envelope_id: {env.envelope_id}")
    print(f"dro_id: {dro.dro_id}")
    print(f"audit rows: {aw.count()}")
    print(f"kg stats: {kg.stats()}")
    aw.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
