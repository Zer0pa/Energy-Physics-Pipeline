"""Runpod dispatch adapter — the live cutover surface.

When `ENERGY_RUNPOD_BASE_URL` is set, the L6 backend resolver routes layer ops
through this adapter instead of the local CPU implementation. The adapter:

  1. POSTs canonical-JSON of the spec to `<base_url>/v1/runpod/<layer>/<domain>/<op>`.
  2. Receives a JSON envelope from the upstream.
  3. Validates it against `UniversalLayerEnvelope`.
  4. Returns the envelope (caller pipes through `accept_envelope`).

Two failure modes are surfaced explicitly:

  - `ENERGY_RUNPOD_BASE_URL` empty → structured fail envelope with
    `gate_id="runpod_not_configured"`, no upstream call attempted.
  - Upstream call raises (timeout, refused, 4xx, 5xx) → structured fail envelope
    with `gate_id="runpod_dispatch_error"`. Caller sees it and `accept_envelope`
    refuses it under `ENERGY_BOUNDARY_GATE=strict`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from energy_physics_pipeline.boundary import BOUNDARY_BLOCK
from energy_physics_pipeline.l6.config import get_config
from energy_physics_pipeline.schemas import (
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
from energy_physics_pipeline.schemas.canonical import sha256_of
from energy_physics_pipeline.schemas.envelope import (
    FailureRecord,
    FalsificationBlock,
    IOBlock,
    ProvenanceBlock,
)


class RunpodRestAdapter:
    """Forward a layer/domain/op to a configured Runpod upstream.

    Pure HTTP forwarder. No physics; no fallback. The local-CPU adapter remains
    the fallback when `ENERGY_L?_BACKEND != runpod_rest`.
    """

    ADAPTER_NAME = "runpod.rest_dispatch"
    TOOL_NAME = "Runpod-REST"
    TOOL_VERSION = "0.1"

    def __init__(
        self,
        *,
        agent_id: str = "runpod.rest",
        git_sha: str = "n/a",
        http_client: httpx.Client | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.git_sha = git_sha
        # Tests inject `http_client` with `httpx.MockTransport` for golden-fixture
        # invariance proofs without a live server.
        self._http_client = http_client

    def dispatch(
        self,
        *,
        layer: LayerLevel,
        domain: Domain,
        sub_vertical: SubVertical,
        op: str,
        spec: dict[str, Any],
        campaign_id: str = "runpod-dispatch",
    ) -> UniversalLayerEnvelope:
        cfg = get_config()
        base_url = cfg.runpod_base_url

        if not base_url:
            return _structured_failure(
                campaign_id=campaign_id,
                sub_vertical=sub_vertical,
                layer=layer,
                domain=domain,
                spec=spec,
                gate_id="runpod_not_configured",
                message=(
                    "ENERGY_L?_BACKEND=runpod_rest but ENERGY_RUNPOD_BASE_URL is empty. "
                    "Set the upstream URL and retry."
                ),
                agent_id=self.agent_id,
                git_sha=self.git_sha,
            )

        url = f"{base_url.rstrip('/')}/v1/runpod/{layer.value}/{domain.value}/{op}"
        try:
            if self._http_client is not None:
                resp = self._http_client.post(url, json={"spec": spec, "campaign_id": campaign_id})
            else:
                with httpx.Client(timeout=cfg.runpod_request_timeout_s) as client:
                    resp = client.post(url, json={"spec": spec, "campaign_id": campaign_id})
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPError as e:
            return _structured_failure(
                campaign_id=campaign_id,
                sub_vertical=sub_vertical,
                layer=layer,
                domain=domain,
                spec=spec,
                gate_id="runpod_dispatch_error",
                message=f"Runpod upstream error: {type(e).__name__}: {str(e)[:200]}",
                agent_id=self.agent_id,
                git_sha=self.git_sha,
            )
        except ValueError as e:
            return _structured_failure(
                campaign_id=campaign_id,
                sub_vertical=sub_vertical,
                layer=layer,
                domain=domain,
                spec=spec,
                gate_id="runpod_dispatch_error",
                message=f"Runpod upstream returned non-JSON: {str(e)[:200]}",
                agent_id=self.agent_id,
                git_sha=self.git_sha,
            )

        if not isinstance(payload, dict):
            return _structured_failure(
                campaign_id=campaign_id,
                sub_vertical=sub_vertical,
                layer=layer,
                domain=domain,
                spec=spec,
                gate_id="runpod_dispatch_error",
                message=f"Runpod upstream returned non-dict payload: {type(payload).__name__}",
                agent_id=self.agent_id,
                git_sha=self.git_sha,
            )

        # Validate envelope shape end-to-end. If invalid, surface as structured failure.
        try:
            envelope = UniversalLayerEnvelope.model_validate(payload)
        except Exception as e:  # noqa: BLE001
            return _structured_failure(
                campaign_id=campaign_id,
                sub_vertical=sub_vertical,
                layer=layer,
                domain=domain,
                spec=spec,
                gate_id="runpod_envelope_invalid",
                message=f"Runpod upstream envelope failed validation: {type(e).__name__}: {str(e)[:200]}",
                agent_id=self.agent_id,
                git_sha=self.git_sha,
            )

        # Force backend.execution_mode to runpod_rest so downstream falsifiers
        # know this came over the wire even if the upstream forgot to set it.
        if envelope.backend.execution_mode != ExecutionMode.runpod_rest:
            envelope = envelope.model_copy(
                update={
                    "backend": envelope.backend.model_copy(
                        update={"execution_mode": ExecutionMode.runpod_rest}
                    )
                }
            )
        # Ensure boundary is preserved (the validator already enforces this; this is
        # belt-and-braces against future schema drift).
        if envelope.boundary != BOUNDARY_BLOCK:
            return _structured_failure(
                campaign_id=campaign_id,
                sub_vertical=sub_vertical,
                layer=layer,
                domain=domain,
                spec=spec,
                gate_id="runpod_boundary_drift",
                message="Upstream returned an envelope with a non-canonical boundary block.",
                agent_id=self.agent_id,
                git_sha=self.git_sha,
            )
        return envelope.finalize()


def _structured_failure(
    *,
    campaign_id: str,
    sub_vertical: SubVertical,
    layer: LayerLevel,
    domain: Domain,
    spec: dict[str, Any],
    gate_id: str,
    message: str,
    agent_id: str,
    git_sha: str,
) -> UniversalLayerEnvelope:
    return UniversalLayerEnvelope(
        campaign_id=campaign_id,
        sub_vertical=sub_vertical,
        layer=layer,
        domain=domain,
        mode=Mode.engineering_stub,
        backend=BackendBlock(
            adapter="runpod.rest_dispatch",
            tool="Runpod-REST",
            tool_version="0.1",
            execution_mode=ExecutionMode.runpod_rest,
            license_class=LicenseClass.A,
            license_evidence_uri="kg://license-grant/runpod-internal",
        ),
        inputs=IOBlock(payload={"spec": spec}),
        outputs=IOBlock(payload={}),
        falsification=FalsificationBlock(
            gate_status=GateStatus.fail,
            scientific_valid=False,
            unit_check_passed=True,
            conservation_check_passed=False,
            boundary_check_passed=True,
            failures=[FailureRecord(gate_id=gate_id, severity="fail", message=message)],
        ),
        provenance=ProvenanceBlock(
            agent_id=agent_id,
            model_id="runpod-dispatch",
            git_sha=git_sha,
            input_hash=sha256_of({"spec": spec, "layer": layer.value, "domain": domain.value}),
            output_hash="0" * 64,
            config_hash=sha256_of({"runpod_base_url": get_config().runpod_base_url}),
            created_at=datetime.now(timezone.utc),
        ),
    ).finalize()
