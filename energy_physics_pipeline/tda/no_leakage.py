"""No-leakage guards for TDA-based models.

All methods raise ValueError with an explicit message on violation.
These guards must be applied before any TDA-derived score is used to
evaluate model performance, following the PRD requirement that
disruption / runaway warnings preserve no-leakage checks.

References
----------
Raschka, S. (2018). Model Evaluation, Model Selection, and Algorithm Selection
  in Machine Learning. arXiv:1811.12808.  (train/test split discipline)
Politis, D.N., Romano, J.P. & Wolf, M. (1999). Subsampling. Springer.
  (block-based splitting for time series — motivation for pulse-level split)
"""
from __future__ import annotations

from typing import Sequence


class NoLeakageGuard:
    """Collection of static guards for temporal and pulse-level no-leakage.

    Each method is a class method so the guard can be used without
    instantiation: ``NoLeakageGuard.assert_no_future_leakage(...)``.
    """

    @classmethod
    def assert_no_future_leakage(
        cls,
        train_idx: Sequence[int],
        test_idx: Sequence[int],
        n: int,
    ) -> None:
        """Assert that the latest training index is strictly before the earliest test index.

        Parameters
        ----------
        train_idx : sequence of integer sample indices used for training
        test_idx  : sequence of integer sample indices used for testing
        n         : total number of samples (used for bounds checking)

        Raises
        ------
        ValueError
            If max(train_idx) >= min(test_idx), indicating future leakage.
        ValueError
            If any index is out of [0, n).
        """
        train_list = list(train_idx)
        test_list = list(test_idx)
        if not train_list:
            raise ValueError("assert_no_future_leakage: train_idx is empty")
        if not test_list:
            raise ValueError("assert_no_future_leakage: test_idx is empty")

        for idx in train_list:
            if idx < 0 or idx >= n:
                raise ValueError(
                    f"assert_no_future_leakage: train index {idx} out of bounds [0, {n})"
                )
        for idx in test_list:
            if idx < 0 or idx >= n:
                raise ValueError(
                    f"assert_no_future_leakage: test index {idx} out of bounds [0, {n})"
                )

        max_train = max(train_list)
        min_test = min(test_list)
        if max_train >= min_test:
            raise ValueError(
                f"Future leakage detected: max train index ({max_train}) >= "
                f"min test index ({min_test}). "
                "Training data must end strictly before test data begins."
            )

    @classmethod
    def assert_pulse_level_split(
        cls,
        train_pulses: Sequence[str],
        test_pulses: Sequence[str],
    ) -> None:
        """Assert that training and test pulse sets are fully disjoint.

        In tokamak / pulsed-device contexts, each pulse is an independent
        experimental run.  Leakage occurs when the same pulse appears in
        both train and test sets (e.g. using early time of a pulse for
        training and late time for testing).

        Parameters
        ----------
        train_pulses : sequence of pulse identifiers (str or hashable)
        test_pulses  : sequence of pulse identifiers

        Raises
        ------
        ValueError
            If any pulse identifier appears in both sets.
        """
        train_set = set(train_pulses)
        test_set = set(test_pulses)
        overlap = train_set & test_set
        if overlap:
            raise ValueError(
                f"Pulse-level leakage detected: pulses {sorted(overlap)} appear in "
                "both train and test sets. Each pulse must belong to exactly one split."
            )

    @classmethod
    def assert_normalisation_fitted_on_train_only(
        cls,
        train_stats: dict,
        fit_call_log: Sequence[dict],
    ) -> None:
        """Assert that normalisation statistics were computed only on training data.

        Parameters
        ----------
        train_stats  : dict with at least keys 'mean', 'std' or 'min', 'max'
                       (not validated here — presence signals that a fit was done)
        fit_call_log : sequence of dicts with at least a 'data_split' key.
                       Each entry records one call to a fit/transform method.
                       Allowed data_split values: 'train'.
                       Forbidden values: 'test', 'all', 'full', 'val', 'validation'.

        Raises
        ------
        ValueError
            If any log entry has data_split != 'train', indicating that
            normalisation was computed on test or full data.
        """
        forbidden = {"test", "all", "full", "val", "validation", "eval"}
        for i, entry in enumerate(fit_call_log):
            split = str(entry.get("data_split", "")).lower().strip()
            if split in forbidden:
                raise ValueError(
                    f"Normalisation leakage detected at fit_call_log[{i}]: "
                    f"data_split='{split}' — normalisation must be fitted on "
                    "'train' data only, not on test/val/full data."
                )
            if split not in {"train", ""}:
                # Unrecognised split — warn conservatively
                raise ValueError(
                    f"Normalisation leakage guard: unrecognised data_split='{split}' "
                    f"at fit_call_log[{i}]. Only 'train' is permitted for fit calls."
                )
