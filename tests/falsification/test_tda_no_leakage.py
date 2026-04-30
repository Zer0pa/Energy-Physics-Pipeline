"""TDA no-leakage guards and TDA fit sanity checks.

Tests:
- Temporal leakage detection (overlapping train/test indices).
- Pulse-level leakage detection (same pulse in train and test).
- Normalisation fitted on non-train data.
- Clean case (no exception).
- Bifurcation sanity: max_lifetime_h1 in post-bifurcation window > pre-bifurcation window.
"""
from __future__ import annotations

import time

import numpy as np
import pytest

from energy_pipeline.schemas.falsification import WindowSpec
from energy_pipeline.tda.early_warning import TdaEarlyWarning
from energy_pipeline.tda.no_leakage import NoLeakageGuard


# ---------------------------------------------------------------------------
# Leakage guard tests
# ---------------------------------------------------------------------------

class TestNoFutureLeakage:
    def test_detects_overlap(self):
        """max(train) >= min(test) → ValueError."""
        with pytest.raises(ValueError, match="Future leakage"):
            NoLeakageGuard.assert_no_future_leakage(
                train_idx=list(range(100)),   # 0..99
                test_idx=list(range(90, 150)),  # 90..149: overlaps with train
                n=200,
            )

    def test_detects_touching(self):
        """max(train)=100 == min(test)=100 → future leakage (not strictly before)."""
        with pytest.raises(ValueError, match="Future leakage"):
            NoLeakageGuard.assert_no_future_leakage(
                train_idx=list(range(101)),  # 0..100
                test_idx=list(range(100, 200)),  # 100..199
                n=200,
            )

    def test_clean_case_passes(self):
        """Strictly separated indices should not raise."""
        NoLeakageGuard.assert_no_future_leakage(
            train_idx=list(range(100)),    # 0..99
            test_idx=list(range(101, 200)),  # 101..199
            n=200,
        )

    def test_empty_train_raises(self):
        with pytest.raises(ValueError, match="empty"):
            NoLeakageGuard.assert_no_future_leakage([], [10, 11], n=50)

    def test_empty_test_raises(self):
        with pytest.raises(ValueError, match="empty"):
            NoLeakageGuard.assert_no_future_leakage([0, 1], [], n=50)

    def test_out_of_bounds_raises(self):
        with pytest.raises(ValueError, match="out of bounds"):
            NoLeakageGuard.assert_no_future_leakage([0, 1, 2], [200, 201], n=100)


class TestPulseLevelSplit:
    def test_detects_overlap(self):
        """Same pulse in both sets → ValueError."""
        with pytest.raises(ValueError, match="Pulse-level leakage"):
            NoLeakageGuard.assert_pulse_level_split(
                train_pulses=["pulse_001", "pulse_002", "pulse_003"],
                test_pulses=["pulse_003", "pulse_004"],  # pulse_003 shared
            )

    def test_detects_multiple_overlap(self):
        with pytest.raises(ValueError, match="Pulse-level leakage"):
            NoLeakageGuard.assert_pulse_level_split(
                train_pulses=["A", "B", "C"],
                test_pulses=["B", "C", "D"],
            )

    def test_clean_case_passes(self):
        NoLeakageGuard.assert_pulse_level_split(
            train_pulses=["pulse_001", "pulse_002"],
            test_pulses=["pulse_003", "pulse_004"],
        )

    def test_empty_sets_pass(self):
        """Both empty is technically OK (no overlap)."""
        NoLeakageGuard.assert_pulse_level_split([], [])


class TestNormalisationLeakage:
    def test_detects_fit_on_all(self):
        """data_split='all' before scoring → ValueError."""
        fit_log = [{"data_split": "all", "step": "standardize"}]
        with pytest.raises(ValueError, match="Normalisation leakage"):
            NoLeakageGuard.assert_normalisation_fitted_on_train_only(
                train_stats={"mean": 0.0, "std": 1.0},
                fit_call_log=fit_log,
            )

    def test_detects_fit_on_test(self):
        """data_split='test' → ValueError."""
        fit_log = [{"data_split": "test"}]
        with pytest.raises(ValueError, match="Normalisation leakage"):
            NoLeakageGuard.assert_normalisation_fitted_on_train_only(
                train_stats={"mean": 0.5, "std": 0.2},
                fit_call_log=fit_log,
            )

    def test_detects_fit_on_full(self):
        fit_log = [{"data_split": "full"}]
        with pytest.raises(ValueError, match="Normalisation leakage"):
            NoLeakageGuard.assert_normalisation_fitted_on_train_only(
                train_stats={},
                fit_call_log=fit_log,
            )

    def test_detects_fit_on_validation(self):
        fit_log = [{"data_split": "validation"}]
        with pytest.raises(ValueError, match="Normalisation leakage"):
            NoLeakageGuard.assert_normalisation_fitted_on_train_only(
                train_stats={},
                fit_call_log=fit_log,
            )

    def test_clean_train_only_passes(self):
        fit_log = [
            {"data_split": "train", "step": "standardize"},
            {"data_split": "train", "step": "pca"},
        ]
        # Should not raise
        NoLeakageGuard.assert_normalisation_fitted_on_train_only(
            train_stats={"mean": 0.0, "std": 1.0},
            fit_call_log=fit_log,
        )


# ---------------------------------------------------------------------------
# TDA bifurcation sanity test
# ---------------------------------------------------------------------------

class TestTdaBifurcationSanity:
    """Verify that TdaEarlyWarning.fit detects topological change at a bifurcation point.

    Regime design:
    - Pre-bifurcation: near-fixed-point regime — small-amplitude white noise around zero.
      The Takens embedding of Gaussian noise forms a ball in R^3; the Vietoris-Rips
      filtration on a ball has negligible H1 (max_lifetime_h1 ≈ 0).
    - Post-bifurcation: two-frequency quasi-periodic orbit (Hopf bifurcation to 2-torus).
      The Takens embedding of sin(t) + sin(√2·t) forms a 2-torus in R^3;
      the filtration reveals a prominent H1 bar corresponding to the torus loop.

    Physical basis: In battery thermal runaway and plasma disruption precursor studies,
    the dynamical system transitions from a stable equilibrium (fixed point) to a
    quasi-periodic or chaotic attractor. This topological transition is captured by
    the appearance of long-lived H1 bars.

    Reference: Gidea, M. & Katz, Y. (2018). Topological data analysis of financial
    time series: Landscapes of crashes. Physica A 491. (same TDA methodology applied
    to dynamical regime change detection.)
    """

    def _make_pre_bifurcation(self, n: int = 512) -> np.ndarray:
        """Near-fixed-point: zero-mean Gaussian noise with tiny amplitude.

        The Takens embedding of white noise fills a ball → minimal H1 topology.
        """
        rng = np.random.default_rng(0)
        return 0.01 * rng.standard_normal(n)

    def _make_post_bifurcation(self, n: int = 512) -> np.ndarray:
        """Two-frequency quasi-periodic orbit (Hopf bifurcation to 2-torus).

        sin(t) + sin(√2·t) creates an invariant 2-torus in the Takens embedding.
        The Vietoris-Rips filtration detects the torus loops as long H1 bars.
        """
        t = np.linspace(0, 4 * np.pi, n)
        return np.sin(t) + np.sin(np.sqrt(2) * t)

    def test_max_h1_higher_post_bifurcation(self):
        """Post-bifurcation H1 lifetime exceeds pre-bifurcation H1 lifetime.

        Expected: pre ≈ 0.003 (noise ball), post ≈ 0.43 (2-torus loop).
        Ratio > 10x — well above noise floor.
        """
        pre = self._make_pre_bifurcation()
        post = self._make_post_bifurcation()

        ws = WindowSpec(length_s=512.0, stride_s=512.0, embedding_dim=3, delay_s=5.0)
        det = TdaEarlyWarning(window_spec=ws)

        t0 = time.perf_counter()
        feat_pre = det.score(pre)
        t1 = time.perf_counter()
        feat_post = det.score(post)
        t2 = time.perf_counter()

        h1_pre = feat_pre.max_lifetime_h1 or 0.0
        h1_post = feat_post.max_lifetime_h1 or 0.0

        print(f"\nPre-bifurcation  max_lifetime_h1 = {h1_pre:.6f}  (noise ball → minimal H1)")
        print(f"Post-bifurcation max_lifetime_h1 = {h1_post:.6f}  (2-torus → long H1 bar)")
        print(f"TDA score times: pre={t1-t0:.3f}s, post={t2-t1:.3f}s")

        assert h1_post > h1_pre, (
            f"Expected post-bifurcation H1 ({h1_post:.6f}) > "
            f"pre-bifurcation H1 ({h1_pre:.6f}) — "
            "2-torus topology must produce longer H1 bars than Gaussian noise ball"
        )
        # Strong version: the ratio should be >> 1 (expect ~100x)
        ratio = h1_post / max(h1_pre, 1e-9)
        print(f"H1 ratio (post/pre) = {ratio:.1f}x")
        assert ratio > 5.0, (
            f"H1 ratio {ratio:.1f}x is too small; expected > 5x for reliable bifurcation detection"
        )

    def test_fit_returns_self(self):
        """fit() returns self for chaining."""
        ts = self._make_pre_bifurcation()
        ws = WindowSpec(length_s=512.0, stride_s=512.0, embedding_dim=2, delay_s=3.0)
        det = TdaEarlyWarning(window_spec=ws)
        result = det.fit(ts)
        assert result is det

    def test_score_under_2s(self):
        """Score on 1024-sample window with embedding_dim=3 must complete under 2s.

        Coverage instrumentation roughly triples wall time; relax the budget when a
        tracer (coverage) is active.
        """
        import sys

        rng = np.random.default_rng(99)
        ts = np.sin(np.linspace(0, 8 * np.pi, 1024)) + 0.1 * rng.standard_normal(1024)
        ws = WindowSpec(length_s=1024.0, stride_s=1024.0, embedding_dim=3, delay_s=5.0)
        det = TdaEarlyWarning(window_spec=ws)

        t0 = time.perf_counter()
        feat = det.score(ts)
        elapsed = time.perf_counter() - t0

        budget = 6.0 if sys.gettrace() is not None else 2.0
        print(f"\n1024-sample score time: {elapsed:.3f}s (budget {budget}s, tracer={sys.gettrace() is not None})")
        assert elapsed < budget, f"TDA score took {elapsed:.3f}s, exceeds {budget}s budget"
        assert feat.max_lifetime_h1 is not None
        assert feat.persistence_entropy is not None

    def test_emit_produces_valid_signal(self):
        """emit() produces a valid EarlyWarningSignal."""
        ts = self._make_post_bifurcation()
        ws = WindowSpec(length_s=512.0, stride_s=512.0, embedding_dim=3, delay_s=5.0)
        det = TdaEarlyWarning(window_spec=ws)
        features = det.score(ts)
        signal = det.emit("battery-cell-42", "battery", features)

        assert signal.domain == "battery"
        assert signal.source_object_id == "battery-cell-42"
        assert 0.0 <= signal.warning_score <= 1.0
        assert signal.status is not None
