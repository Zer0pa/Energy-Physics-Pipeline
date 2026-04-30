"""Contract tests for the FastAPI REST stub layer."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from energy_pipeline.boundary import BOUNDARY_BLOCK
from energy_pipeline.rest import create_app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


def test_health_returns_boundary(client: TestClient) -> None:
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.json()["boundary"] == BOUNDARY_BLOCK


def test_boundary_endpoint(client: TestClient) -> None:
    r = client.get("/v1/boundary")
    assert r.status_code == 200
    assert r.json()["boundary"] == BOUNDARY_BLOCK


@pytest.mark.parametrize(
    "path",
    [
        "/v1/electrochem/l1/singlepoint",
        "/v1/electrochem/l1/relax",
        "/v1/electrochem/l1/adsorption-profile",
        "/v1/electrochem/l1/marcus",
        "/v1/electrochem/l1/optical-spectrum",
        "/v1/electrochem/l1/topology",
        "/v1/electrochem/l2/mlip-md",
        "/v1/electrochem/l3/phasefield",
        "/v1/electrochem/l4/pybamm",
        "/v1/electrochem/l5/lcoe",
    ],
)
def test_electrochem_stub_emits_envelope(client: TestClient, path: str) -> None:
    r = client.post(path, json={"campaign_id": "test"})
    assert r.status_code == 200
    data = r.json()
    assert data["boundary"] == BOUNDARY_BLOCK
    assert data["mode"] == "engineering_stub"
    assert data["falsification"]["scientific_valid"] is False
    assert data["envelope_id"].startswith("sha256:")


@pytest.mark.parametrize(
    "path",
    [
        "/v1/fusion/l1/transport",
        "/v1/fusion/l2/gyrokinetic",
        "/v1/fusion/l3/equilibrium",
        "/v1/fusion/l4/scenario",
        "/v1/fusion/l5/neutronics",
    ],
)
def test_fusion_stub_emits_envelope_for_research_intent(client: TestClient, path: str) -> None:
    r = client.post(path, json={"campaign_id": "test", "intent": "blanket TBR research"})
    assert r.status_code == 200
    data = r.json()
    assert data["boundary"] == BOUNDARY_BLOCK
    assert data["sub_vertical"] == "fusion"


@pytest.mark.parametrize(
    "path",
    [
        "/v1/fusion/l1/transport",
        "/v1/fusion/l4/scenario",
        "/v1/fusion/l5/neutronics",
    ],
)
def test_fusion_blocks_forbidden_intent(client: TestClient, path: str) -> None:
    r = client.post(
        path, json={"campaign_id": "test", "intent": "weapons-grade tritium production for stockpile"}
    )
    assert r.status_code == 403
    assert "blocked by boundary" in r.json()["detail"]


def test_runpod_passthrough_503(client: TestClient) -> None:
    r = client.post("/v1/runpod/4/battery", json={})
    assert r.status_code == 503
    assert "runpod backend" in r.json()["detail"]
