"""Energy CLI — smoke runner and operational entry points."""
from __future__ import annotations

import sys

import typer
from rich import print
from rich.console import Console
from rich.table import Table

from energy_pipeline.boundary import BOUNDARY_BLOCK
from energy_pipeline.l6 import default_registry, get_config
from energy_pipeline.audit import AuditWriter
from energy_pipeline.kg import KGStore
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
from energy_pipeline.schemas.envelope import (
    FalsificationBlock,
    IOBlock,
    ProvenanceBlock,
)


app = typer.Typer(help=BOUNDARY_BLOCK, no_args_is_help=True)
console = Console()


@app.command()
def health() -> None:
    """Report config + audit + KG status."""
    cfg = get_config()
    aw = AuditWriter()
    kg = KGStore()
    table = Table(title="Energy Pipeline Health")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Boundary block length", str(len(BOUNDARY_BLOCK)))
    table.add_row("Execution profile", cfg.execution_profile)
    table.add_row("Audit required", str(cfg.audit_required))
    table.add_row("L1 backend", cfg.l1_backend)
    table.add_row("L4 backend", cfg.l4_backend)
    table.add_row("L5 backend", cfg.l5_backend)
    table.add_row("Reasoner backend", cfg.reasoner_backend)
    table.add_row("Audit DB rows", str(aw.count()))
    table.add_row("KG nodes", str(kg.stats()["nodes"]))
    table.add_row("KG edges", str(kg.stats()["edges"]))
    aw.close()
    console.print(table)


@app.command()
def boundary() -> None:
    """Print the boundary block verbatim."""
    print(BOUNDARY_BLOCK)


@app.command()
def registry() -> None:
    """List the seed adapter registry."""
    reg = default_registry()
    table = Table(title="Adapter Registry")
    table.add_column("ID")
    table.add_column("Tool")
    table.add_column("Layer")
    table.add_column("Sub-vertical")
    table.add_column("License")
    table.add_column("Capabilities")
    for r in reg.all():
        table.add_row(
            r.adapter_id,
            f"{r.tool} {r.tool_version}",
            r.layer.value,
            r.sub_vertical.value,
            r.license_class.value,
            ",".join(c.value for c in r.capabilities),
        )
    console.print(table)


@app.command()
def smoke(
    sub_vertical: str = typer.Option("electrochemistry", help="electrochemistry|fusion"),
    layer: str = typer.Option("L4", help="L1|L2|L3|L4|L5|L6"),
    domain: str = typer.Option("battery", help="battery|green_h2|fuel_cell|sofc|soec|pv|thermoelectric|fusion"),
    write_audit: bool = typer.Option(True, help="write audit + KG"),
    campaign: str = typer.Option("smoke", help="campaign id"),
) -> None:
    """Emit a single demo envelope and record audit + KG.

    Verifies the foundation works end-to-end without invoking any heavy adapter.
    """
    sv = SubVertical(sub_vertical)
    lv = LayerLevel(layer)
    dom = Domain(domain)
    env = UniversalLayerEnvelope(
        campaign_id=campaign,
        sub_vertical=sv,
        layer=lv,
        domain=dom,
        mode=Mode.engineering_stub,
        backend=BackendBlock(
            adapter="cli-smoke",
            tool="cli-smoke",
            tool_version="0.0.1",
            execution_mode=ExecutionMode.local_cpu,
            license_class=LicenseClass.A,
            license_evidence_uri="kg://license-grant/cli-smoke",
        ),
        inputs=IOBlock(payload={"campaign": campaign}),
        outputs=IOBlock(
            payload={"quantities": {"smoke_metric": {"value": 1.0, "unit": "1"}}}
        ),
        falsification=FalsificationBlock(
            gate_status=GateStatus.pass_,
            scientific_valid=False,
            unit_check_passed=True,
            conservation_check_passed=True,
            boundary_check_passed=True,
        ),
        provenance=ProvenanceBlock(
            agent_id="cli",
            model_id="n/a",
            git_sha="local",
            input_hash="0" * 64,
            output_hash="0" * 64,
            config_hash="0" * 64,
        ),
    ).finalize()

    print(f"[bold green]envelope_id[/]: {env.envelope_id}")
    if write_audit:
        with AuditWriter() as aw:
            aw.write_event("smoke", env.model_dump(mode="json"))
        kg = KGStore()
        kg.add_node("ToolAdapter", "cli-smoke", {"tool": "cli-smoke"}, boundary_required=False)
        kg.add_node(
            "SimulationRun",
            f"smoke-{env.run_id}",
            env.model_dump(mode="json"),
        )
        kg.add_edge("USED_TOOL", f"smoke-{env.run_id}", "cli-smoke", {})
        print(f"[cyan]audit + KG written[/]; KG stats: {kg.stats()}")


@app.command()
def serve_rest(host: str = "127.0.0.1", port: int = 8001, reload_: bool = typer.Option(False, "--reload")) -> None:
    """Run the FastAPI REST stub server."""
    import uvicorn

    uvicorn.run(
        "energy_pipeline.rest.app:app",
        host=host,
        port=port,
        reload=reload_,
    )


@app.command("falsification-wave")
def falsification_wave() -> None:
    """Run the falsification wave (delegates to pytest)."""
    import subprocess

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/falsification",
        "-v",
        "--tb=short",
    ]
    raise SystemExit(subprocess.call(cmd))


@app.command("electrochem-e2e")
def electrochem_e2e() -> None:
    """Run the electrochemistry end-to-end test (delegates to pytest)."""
    import subprocess

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/integration/test_electrochem_e2e.py",
        "-v",
    ]
    raise SystemExit(subprocess.call(cmd))


@app.command("fusion-phase0")
def fusion_phase0() -> None:
    """Run the fusion Phase-0 test (delegates to pytest)."""
    import subprocess

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/integration/test_fusion_phase0.py",
        "tests/integration/test_fusion_reasoning_bench.py",
        "-v",
    ]
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    app()
