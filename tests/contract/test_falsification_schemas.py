"""Contract tests for falsification schemas (CrossModelDisagreementRecord, EarlyWarningSignal)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from energy_physics_pipeline.schemas import (
    CrossModelDisagreementRecord,
    DisagreementMetric,
    DisagreementStatus,
    EarlyWarningSignal,
    EarlyWarningStatus,
)
from energy_physics_pipeline.schemas.falsification import EarlyWarningFeatures, WindowSpec


def _disagreement(**overrides):
    base = dict(
        record_id="rec1",
        object_id="obj1",
        quantity="energy",
        unit="eV",
        models_compared=["modelA", "modelB"],
        values=[1.0, 1.05],
        uncertainties=[0.01, 0.02],
        metric=DisagreementMetric.absolute,
        pass_threshold=0.05,
        warn_threshold=0.10,
        fail_threshold=0.25,
        status=DisagreementStatus.pass_,
        resolution_action="rerun",
    )
    base.update(overrides)
    return CrossModelDisagreementRecord(**base)


def test_disagreement_requires_two_models():
    with pytest.raises(ValidationError):
        _disagreement(models_compared=["onlyone"], values=[1.0])


def test_disagreement_value_count_must_match():
    with pytest.raises(ValidationError):
        _disagreement(values=[1.0])  # 2 models, 1 value


def test_disagreement_thresholds_ordered():
    with pytest.raises(ValidationError):
        _disagreement(pass_threshold=0.5, warn_threshold=0.1, fail_threshold=0.05)


def test_disagreement_pass_construct_ok():
    rec = _disagreement()
    assert rec.status == DisagreementStatus.pass_


def test_early_warning_signal_construct_ok():
    sig = EarlyWarningSignal(
        signal_id="ew1",
        source_object_id="ts1",
        domain="battery",
        window_spec=WindowSpec(length_s=10.0, stride_s=1.0, embedding_dim=3, delay_s=0.1),
        features=EarlyWarningFeatures(
            persistence_entropy=0.5,
            max_lifetime_h0=0.2,
            max_lifetime_h1=0.0,
        ),
        warning_score=0.3,
        lead_time_estimate_s=5.0,
        false_positive_rate_estimate=0.05,
        status=EarlyWarningStatus.watch,
    )
    assert sig.status == EarlyWarningStatus.watch
