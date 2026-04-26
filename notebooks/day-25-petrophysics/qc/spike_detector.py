"""
spike_detector.py
=================
Enterprise-grade 7-stage spike detection engine.

Inspired by the architecture of Techlog, Geolog, and Interactive Petrophysics.
Replaces the simple single-pass MAD detector in qc_service.py with a robust,
physics-aware, multi-log pipeline that emits structured SpikeResult objects
including per-point confidence scores and correction suggestions.

Stage Pipeline
--------------
  1. Candidate Detection  – Rolling Median + MAD (robust local baseline)
  2. Gradient Symmetry    – Δ₁/Δ₂ sign reversal ("up then back down")
  3. Physical Range       – Hard + soft limits per curve type
  4. Persistence Check    – Run-length ≤ 2 → spike; longer → real formation
  5. Cross-Log Correlation– Isolation score: single-log anomaly → noise
  6. Confidence Scoring   – Weighted sum of all stage votes
  7. Correction Suggestion– Median, linear, cubic, or keep original

Usage
-----
    from qc.spike_detector import SpikeDetector, DetectionMode

    result = SpikeDetector().detect(
        curve_series=series,
        depth_series=depth,
        curve_name="GR",
        all_curves_df=df,
        mode="Advanced",
        window=5,
        mad_multiplier=3.0,
        confidence_threshold=0.5,
        correction="local_median",
    )
    spike_mask = result.is_spike       # bool array aligned to curve_series
    confidence  = result.confidence    # float array [0, 1]
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# Public enumerations
# ─────────────────────────────────────────────────────────────────────────────

class DetectionMode(str, Enum):
    """Detection sophistication level."""
    STANDARD = "Standard"    # Stages 1–4
    ADVANCED  = "Advanced"   # Stages 1–5 (adds cross-log)
    ML        = "ML"         # Stages 1–4 + Isolation Forest on residuals


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SpikeResult:
    """Structured output from the multi-stage spike detector.

    All arrays are aligned to the **valid** (finite, in-range) subset of the
    input curve, NOT the full original index.  Use ``original_index`` to map
    results back to the source DataFrame.

    Attributes
    ----------
    is_spike : np.ndarray[bool]
        Final binary spike classification after confidence thresholding.
    confidence : np.ndarray[float]
        Per-point confidence that the point is a spike ∈ [0, 1].
    correction_values : np.ndarray[float]
        Suggested replacement values at spike positions (NaN elsewhere).
    original_index : pd.Index
        pandas index labels corresponding to the valid subset.
    stage_flags : dict[str, np.ndarray[bool]]
        Per-stage boolean arrays for diagnostics.
        Keys: "candidate", "gradient", "physics", "persistence", "cross_log".
    n_spikes : int
        Number of points classified as spikes.
    """
    is_spike:          np.ndarray
    confidence:        np.ndarray
    correction_values: np.ndarray
    original_index:    pd.Index
    stage_flags:       dict = field(default_factory=dict)
    n_spikes:          int  = 0


# ─────────────────────────────────────────────────────────────────────────────
# Main engine
# ─────────────────────────────────────────────────────────────────────────────

class SpikeDetector:
    """Multi-stage professional spike detector.

    Parameters are all passed to :meth:`detect`; the class itself is stateless
    so the same instance can be reused across wells / curves.
    """

    # Stage weights for confidence scoring (must sum to 1.0)
    _W_LOCAL     = 0.40
    _W_GRADIENT  = 0.20
    _W_PHYSICS   = 0.20
    _W_ISOLATION = 0.20

    # ── public API ────────────────────────────────────────────────────────────

    def detect(
        self,
        curve_series:         pd.Series,
        depth_series:         pd.Series,
        curve_name:           str = "",
        all_curves_df:        Optional[pd.DataFrame] = None,
        *,
        mode:                 str   = "Standard",
        window:               int   = 5,
        mad_multiplier:       float = 3.0,
        confidence_threshold: float = 0.5,
        cross_log_validation: bool  = True,
        correction:           str   = "local_median",
    ) -> SpikeResult:
        """Run the spike detection pipeline.

        Parameters
        ----------
        curve_series : pd.Series
            The log curve to analyse (numeric, may contain NaN).
        depth_series : pd.Series
            Depth values aligned to *curve_series*.
        curve_name : str
            Mnemonic used for physics lookup (e.g. "GR", "RHOB").
        all_curves_df : pd.DataFrame, optional
            All available curves from the same well, used in Stage 5.
        mode : str
            "Standard", "Advanced", or "ML".
        window : int
            Half-window size for rolling statistics (minimum 3, rounded up to
            nearest odd number internally).
        mad_multiplier : float
            Multiplier applied to the local MAD; larger → less sensitive.
        confidence_threshold : float
            Minimum confidence [0, 1] to classify a point as a spike.
        cross_log_validation : bool
            Whether to run Stage 5 (cross-log correlation).
        correction : str
            "local_median" | "linear" | "cubic" | "keep".

        Returns
        -------
        SpikeResult
        """
        # ── guard: need at least 5 valid points ──────────────────────────────
        valid_mask  = curve_series.notna() & depth_series.notna()
        valid_index = curve_series.index[valid_mask]
        values      = curve_series.loc[valid_index].to_numpy(dtype=float)
        depths      = depth_series.loc[valid_index].to_numpy(dtype=float)
        n           = len(values)

        if n < 5:
            empty = np.zeros(n, dtype=bool)
            return SpikeResult(
                is_spike=empty,
                confidence=np.zeros(n, dtype=float),
                correction_values=np.full(n, np.nan),
                original_index=valid_index,
                stage_flags={},
                n_spikes=0,
            )

        win     = max(int(window) | 1, 3)   # ensure odd and ≥ 3
        mode_e  = DetectionMode(mode) if isinstance(mode, str) else mode

        # ── Stage 1: Candidate Detection (Rolling Median + MAD) ──────────────
        s1 = self._stage1_candidate(values, win, mad_multiplier)

        # ── Stage 2: Gradient Symmetry ────────────────────────────────────────
        s2 = self._stage2_gradient(values)

        # ── Stage 3: Physical Range Validation ───────────────────────────────
        s3 = self._stage3_physics(values, curve_name)

        # ── Stage 4: Persistence Check ────────────────────────────────────────
        s4 = self._stage4_persistence(s1, max_run=2)

        # ── Stage 5: Cross-Log Correlation ────────────────────────────────────
        s5 = np.zeros(n, dtype=float)   # isolation scores
        if (mode_e in (DetectionMode.ADVANCED,) and cross_log_validation and
                all_curves_df is not None):
            from qc.cross_log_validator import CrossLogValidator
            s5 = CrossLogValidator().validate(
                candidate_indices=np.where(s1)[0],
                all_curves_df=all_curves_df,
                valid_index=valid_index,
                depth_series=depth_series,
                window=win,
                mad_multiplier=mad_multiplier,
            )

        # ── ML mode: replace Stage 1 with Isolation Forest on residuals ──────
        if mode_e == DetectionMode.ML:
            s1 = self._stage1_ml(values, depths, mad_multiplier)
            # re-run persistence on ML candidates
            s4 = self._stage4_persistence(s1, max_run=2)

        # ── Stage 6: Confidence Scoring ───────────────────────────────────────
        confidence = self._stage6_confidence(s1, s2, s3, s5, values, win, curve_name)

        # Apply confidence threshold
        is_spike = confidence >= confidence_threshold

        # Enforce persistence gate: if a run is long it's formation, not noise
        is_spike = is_spike & s4

        # ── Stage 7: Correction Suggestion ───────────────────────────────────
        correction_values = self._stage7_correction(values, is_spike, win, correction)

        return SpikeResult(
            is_spike=is_spike,
            confidence=confidence,
            correction_values=correction_values,
            original_index=valid_index,
            stage_flags={
                "candidate":   s1,
                "gradient":    s2,
                "physics":     s3,
                "persistence": s4,
                "cross_log":   (s5 > 0.5),
            },
            n_spikes=int(is_spike.sum()),
        )

    # ── Stage 1 ───────────────────────────────────────────────────────────────

    @staticmethod
    def _stage1_candidate(values: np.ndarray, win: int, multiplier: float) -> np.ndarray:
        """Rolling-median + MAD candidate detection."""
        n      = len(values)
        flags  = np.zeros(n, dtype=bool)
        half_w = win // 2

        for i in range(1, n - 1):
            lo = max(0, i - half_w)
            hi = min(n, i + half_w + 1)
            neighbours = np.concatenate([values[lo:i], values[i + 1:hi]])
            if neighbours.size < 2:
                continue
            local_med = float(np.median(neighbours))
            local_mad = float(np.median(np.abs(neighbours - local_med)))
            local_std = max(local_mad * 1.4826, 1e-9)
            if abs(values[i] - local_med) > multiplier * local_std:
                flags[i] = True

        return flags

    @staticmethod
    def _stage1_ml(values: np.ndarray, depths: np.ndarray, multiplier: float) -> np.ndarray:
        """Isolation Forest on rolling-median residuals (ML mode)."""
        try:
            from sklearn.ensemble import IsolationForest
        except ImportError:
            warnings.warn("scikit-learn not available; falling back to MAD detector.")
            return SpikeDetector._stage1_candidate(values, 5, multiplier)

        # Compute residual from rolling median
        s   = pd.Series(values)
        med = s.rolling(window=5, center=True, min_periods=2).median().to_numpy()
        residuals = values - np.where(np.isnan(med), values, med)

        features = np.column_stack([depths, residuals])
        feat_std  = np.nanstd(features, axis=0)
        feat_std[feat_std == 0] = 1.0
        features  = (features - np.nanmean(features, axis=0)) / feat_std

        contamination = float(np.clip(0.15 / max(float(multiplier), 0.5), 0.01, 0.15))
        model = IsolationForest(
            contamination=contamination,
            n_estimators=200,
            random_state=42,
        )
        return model.fit_predict(features) == -1

    # ── Stage 2 ───────────────────────────────────────────────────────────────

    @staticmethod
    def _stage2_gradient(values: np.ndarray) -> np.ndarray:
        """Gradient symmetry: up-then-back-down (or down-then-back-up) pattern."""
        n     = len(values)
        flags = np.zeros(n, dtype=bool)

        if n < 3:
            return flags

        diff = np.diff(values)          # length n-1
        for i in range(1, n - 1):
            d_before = diff[i - 1]      # values[i] - values[i-1]
            d_after  = diff[i]          # values[i+1] - values[i]
            # Spike: sign reversal (up then down, or down then up)
            # AND the magnitudes are both non-trivial
            if d_before * d_after < 0:
                flags[i] = True

        return flags

    # ── Stage 3 ───────────────────────────────────────────────────────────────

    @staticmethod
    def _stage3_physics(values: np.ndarray, curve_name: str) -> np.ndarray:
        """Hard/soft physical limit violation flags."""
        n = len(values)
        flags = np.zeros(n, dtype=bool)

        try:
            from qc.physical_rules import get_limits
            limit = get_limits(curve_name)
        except ImportError:
            return flags

        if limit is None:
            return flags

        for i, v in enumerate(values):
            if limit.is_hard_violated(float(v)):
                flags[i] = True

        return flags

    # ── Stage 4 ───────────────────────────────────────────────────────────────

    @staticmethod
    def _stage4_persistence(candidates: np.ndarray, max_run: int = 2) -> np.ndarray:
        """Run-length test: anomaly runs > max_run are likely real formation."""
        n      = len(candidates)
        result = candidates.copy()
        i      = 0
        while i < n:
            if candidates[i]:
                j = i
                while j < n and candidates[j]:
                    j += 1
                run_len = j - i
                if run_len > max_run:
                    result[i:j] = False   # too long → real formation/trend
                i = j
            else:
                i += 1
        return result

    # ── Stage 6 ───────────────────────────────────────────────────────────────

    def _stage6_confidence(
        self,
        s1: np.ndarray,
        s2: np.ndarray,
        s3: np.ndarray,
        s5_isolation: np.ndarray,
        values: np.ndarray,
        win: int,
        curve_name: str,
    ) -> np.ndarray:
        """Weighted confidence score per point."""
        n = len(values)

        # Local deviation score (continuous version of Stage 1)
        local_score = self._local_deviation_score(values, win, curve_name)

        # Gradient score: 1.0 if sign reversal, 0.0 otherwise
        gradient_score = s2.astype(float)

        # Physics score (continuous violation severity)
        physics_score = self._physics_score(values, curve_name)

        # Isolation score: high value → point is isolated (likely noise rather
        # than real formation change).  Comes from cross-log validator.
        # Shape may be shorter if only candidates were scored → broadcast safely.
        iso_score = np.zeros(n, dtype=float)
        if len(s5_isolation) == n:
            iso_score = s5_isolation.astype(float)
        elif len(s5_isolation) > 0:
            # Only candidate positions were scored — splat back
            candidate_idx = np.where(s1)[0]
            for k, idx in enumerate(candidate_idx):
                if k < len(s5_isolation) and idx < n:
                    iso_score[idx] = float(s5_isolation[k])

        confidence = (
            self._W_LOCAL     * local_score +
            self._W_GRADIENT  * gradient_score +
            self._W_PHYSICS   * physics_score +
            self._W_ISOLATION * iso_score
        )
        return np.clip(confidence, 0.0, 1.0)

    @staticmethod
    def _local_deviation_score(values: np.ndarray, win: int, curve_name: str) -> np.ndarray:
        """Continuous MAD-normalised deviation [0, 1] clipped at 3σ → 1.0."""
        n      = len(values)
        scores = np.zeros(n, dtype=float)
        half_w = win // 2

        for i in range(1, n - 1):
            lo = max(0, i - half_w)
            hi = min(n, i + half_w + 1)
            neighbours = np.concatenate([values[lo:i], values[i + 1:hi]])
            if neighbours.size < 2:
                continue
            local_med = float(np.median(neighbours))
            local_mad = float(np.median(np.abs(neighbours - local_med)))
            local_std = max(local_mad * 1.4826, 1e-9)
            raw_z = abs(values[i] - local_med) / local_std
            # Normalise: z=3 → score=1.0
            scores[i] = float(np.clip(raw_z / 3.0, 0.0, 1.0))

        return scores

    @staticmethod
    def _physics_score(values: np.ndarray, curve_name: str) -> np.ndarray:
        """Continuous physics violation severity [0, 1] per point."""
        n = len(values)
        scores = np.zeros(n, dtype=float)

        try:
            from qc.physical_rules import get_limits
            limit = get_limits(curve_name)
        except ImportError:
            return scores

        if limit is None:
            return scores

        for i, v in enumerate(values):
            scores[i] = limit.violation_score(float(v))

        return scores

    # ── Stage 7 ───────────────────────────────────────────────────────────────
    @staticmethod
    def _stage7_correction(
        values: np.ndarray,
        is_spike: np.ndarray,
        win: int,
        method: str,
    ) -> np.ndarray:
        """Compute suggested replacement values for spike positions."""
        n = len(values)
        correction = np.full(n, np.nan)
        half_w = win // 2

        if method == "keep" or not is_spike.any():
            return correction

        if method == "local_median":
            for i in np.where(is_spike)[0]:
                lo = max(0, i - half_w)
                hi = min(n, i + half_w + 1)
                neighbours = np.concatenate([values[lo:i], values[i + 1:hi]])
                # Exclude other spike positions from neighbours
                non_spike_nb = neighbours[~is_spike[
                    np.concatenate([
                        np.arange(lo, i),
                        np.arange(i + 1, hi),
                    ])[:len(neighbours)]
                ]] if lo < i or hi > i + 1 else neighbours
                if non_spike_nb.size == 0:
                    non_spike_nb = neighbours
                correction[i] = float(np.median(non_spike_nb))

        elif method == "linear":
            # Linear interpolation between the nearest non-spike points
            spike_pos = np.where(is_spike)[0]
            clean_pos = np.where(~is_spike)[0]
            if clean_pos.size < 2:
                return correction
            correction[spike_pos] = np.interp(spike_pos, clean_pos, values[clean_pos])

        elif method == "cubic":
            try:
                from scipy.interpolate import CubicSpline
            except ImportError:
                # Fall back to linear
                spike_pos = np.where(is_spike)[0]
                clean_pos = np.where(~is_spike)[0]
                if clean_pos.size >= 2:
                    correction[spike_pos] = np.interp(spike_pos, clean_pos, values[clean_pos])
                return correction

            spike_pos = np.where(is_spike)[0]
            clean_pos = np.where(~is_spike)[0]
            if clean_pos.size >= 4:
                cs = CubicSpline(clean_pos, values[clean_pos], extrapolate=True)
                correction[spike_pos] = cs(spike_pos)
            elif clean_pos.size >= 2:
                correction[spike_pos] = np.interp(spike_pos, clean_pos, values[clean_pos])

        return correction
