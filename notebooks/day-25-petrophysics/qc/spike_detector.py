"""
spike_detector.py
=================
Enterprise-grade 7-stage spike detection engine — v2 (signal-processing upgrade).

Changes vs v1
-------------
* Curve-specific profiles loaded from qc_rules.get_curve_profile()
* Adaptive MAD: threshold scales with local volatility (stable → strict, noisy → relaxed)
* Stage 2: peak-width constraint added alongside gradient symmetry
* Stage 4: hard tiered persistence rejection (1-2 spike | 3-5 suspicious | >5 geology)
* Stage 1 ML: richer feature set (gradient, curvature, rolling_std, local_median_diff)
* Stage 6: logical gating before weighted confidence sum
* Stage 7: context-aware correction (isolated/burst/interpolation/keep)
* SpikeResult: new spike_type array for UI visualization

Stage Pipeline
--------------
  1. Candidate Detection  – Adaptive Rolling Median + MAD (or enriched IF)
  2. Gradient + Width     – Sign reversal AND peak_width <= max_spike_width
  3. Physical Range       – Hard + soft limits per curve type
  4. Persistence Check    – Tiered run-length hard rejection
  5. Cross-Log Correlation– Isolation score with depth tolerance
  6. Logical Gate + Score – Hard reject first, then weighted confidence
  7. Correction           – Method chosen by spike_type
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
    ML        = "ML"         # Stages 1–4 + enriched Isolation Forest


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
    spike_type : np.ndarray[str]
        Classification per spike: "isolated" | "burst" | "physics" |
        "geology_change" | "none".  Enables distinct UI markers.
    n_spikes : int
        Number of points classified as spikes.
    """
    is_spike:          np.ndarray
    confidence:        np.ndarray
    correction_values: np.ndarray
    original_index:    pd.Index
    stage_flags:       dict = field(default_factory=dict)
    spike_type:        np.ndarray = field(default_factory=lambda: np.array([], dtype=object))
    n_spikes:          int  = 0


# ─────────────────────────────────────────────────────────────────────────────
# Main engine
# ─────────────────────────────────────────────────────────────────────────────

class SpikeDetector:
    """Multi-stage professional spike detector (v2).

    The same instance can be reused across wells / curves (stateless).
    """

    # Stage weights for confidence scoring (must sum to 1.0)
    _W_LOCAL     = 0.40
    _W_GRADIENT  = 0.20
    _W_PHYSICS   = 0.20
    _W_ISOLATION = 0.20

    # Adaptive MAD volatility scaling factor
    _ADAPTIVE_ALPHA = 0.5

    # ── public API ────────────────────────────────────────────────────────────

    def detect(
        self,
        curve_series:         pd.Series,
        depth_series:         pd.Series,
        curve_name:           str = "",
        all_curves_df:        Optional[pd.DataFrame] = None,
        *,
        mode:                 str   = "Standard",
        window:               Optional[int]   = None,
        mad_multiplier:       Optional[float] = None,
        confidence_threshold: float = 0.5,
        cross_log_validation: bool  = True,
        correction:           Optional[str]   = None,
        max_spike_width:      Optional[int]   = None,
    ) -> SpikeResult:
        """Run the spike detection pipeline.

        Parameters
        ----------
        curve_series : pd.Series
            The log curve to analyse (numeric, may contain NaN).
        depth_series : pd.Series
            Depth values aligned to *curve_series*.
        curve_name : str
            Mnemonic for physics lookup and profile selection.
        all_curves_df : pd.DataFrame, optional
            All available curves from the same well (Stage 5).
        mode : str
            "Standard", "Advanced", or "ML".
        window : int, optional
            Override profile window (half-window for rolling stats).
        mad_multiplier : float, optional
            Override profile MAD multiplier.
        confidence_threshold : float
            Minimum confidence to classify a point as a spike.
        cross_log_validation : bool
            Whether to run Stage 5 (cross-log correlation).
        correction : str, optional
            Override correction method: local_median | linear | cubic | keep.
        max_spike_width : int, optional
            Override profile max spike width in samples.
        """
        # ── load curve-specific profile; caller kwargs override ───────────────
        try:
            from qc.qc_rules import get_curve_profile
            profile = get_curve_profile(curve_name)
        except ImportError:
            profile = {
                "window": 11, "mad_multiplier": 4.0,
                "max_spike_width": 3, "correction": "local_median",
            }

        _window   = int(window        or profile["window"])
        _mult     = float(mad_multiplier or profile["mad_multiplier"])
        _msw      = int(max_spike_width  or profile.get("max_spike_width", 3))
        _corr     = correction           or profile.get("correction", "local_median")

        # ── guard: need at least 5 valid points ──────────────────────────────
        valid_mask  = curve_series.notna() & depth_series.notna()
        valid_index = curve_series.index[valid_mask]
        values      = curve_series.loc[valid_index].to_numpy(dtype=float)
        depths      = depth_series.loc[valid_index].to_numpy(dtype=float)
        n           = len(values)

        _empty = SpikeResult(
            is_spike=np.zeros(n, dtype=bool),
            confidence=np.zeros(n, dtype=float),
            correction_values=np.full(n, np.nan),
            original_index=valid_index,
            stage_flags={},
            spike_type=np.full(n, "none", dtype=object),
            n_spikes=0,
        )
        if n < 5:
            return _empty

        win    = max(int(_window) | 1, 3)   # ensure odd and ≥ 3
        mode_e = DetectionMode(mode) if isinstance(mode, str) else mode

        # ── Stage 1: Adaptive Candidate Detection ────────────────────────────
        if mode_e == DetectionMode.ML:
            s1 = self._stage1_ml(values, depths, _mult)
        else:
            s1 = self._stage1_candidate(values, win, _mult)

        # ── Stage 2: Gradient Symmetry + Peak-Width Constraint ───────────────
        s2, peak_widths = self._stage2_gradient_width(values, _msw)

        # ── Stage 3: Physical Range Validation ───────────────────────────────
        s3 = self._stage3_physics(values, curve_name)

        # ── Stage 4: Tiered Persistence (hard rejection) ─────────────────────
        s4, run_lengths = self._stage4_persistence_tiered(s1)

        # ── Stage 5: Cross-Log Correlation ───────────────────────────────────
        s5 = np.zeros(n, dtype=float)   # isolation scores
        if (mode_e == DetectionMode.ADVANCED and cross_log_validation and
                all_curves_df is not None):
            try:
                from qc.cross_log_validator import CrossLogValidator
                s5 = CrossLogValidator().validate(
                    candidate_indices=np.where(s1)[0],
                    all_curves_df=all_curves_df,
                    valid_index=valid_index,
                    depth_series=depth_series,
                    window=win,
                    mad_multiplier=_mult,
                )
            except Exception:
                pass

        # ── Stage 6: Logical Gate → then Confidence Scoring ──────────────────
        confidence, hard_rejected = self._stage6_gated_confidence(
            s1, s2, s3, s4, s5, values, win, curve_name, run_lengths,
        )

        is_spike = (confidence >= confidence_threshold) & (~hard_rejected)

        # ── Stage 7: Classify spike_type & Context-Aware Correction ──────────
        spike_type = self._classify_spike_type(is_spike, run_lengths, s3)
        correction_values = self._stage7_correction(
            values, is_spike, spike_type, win, _corr
        )

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
            spike_type=spike_type,
            n_spikes=int(is_spike.sum()),
        )

    # ── Stage 1: Adaptive MAD ─────────────────────────────────────────────────

    @staticmethod
    def _stage1_candidate(
        values: np.ndarray, win: int, base_multiplier: float
    ) -> np.ndarray:
        """Adaptive rolling-median + MAD candidate detection.

        The effective threshold scales with local volatility:
            threshold = base_mult * (1 + alpha * normalised_volatility)

        Stable zones → strict QC; geologically noisy zones → relaxed.
        """
        n        = len(values)
        flags    = np.zeros(n, dtype=bool)
        half_w   = win // 2
        alpha    = SpikeDetector._ADAPTIVE_ALPHA

        # Global std used for volatility normalisation
        global_std = float(np.nanstd(values)) or 1.0

        for i in range(1, n - 1):
            lo = max(0, i - half_w)
            hi = min(n, i + half_w + 1)
            neighbours = np.concatenate([values[lo:i], values[i + 1:hi]])
            if neighbours.size < 2:
                continue

            local_med = float(np.median(neighbours))
            local_mad = float(np.median(np.abs(neighbours - local_med)))
            local_std = max(local_mad * 1.4826, 1e-9)

            # Local volatility relative to global
            local_vol      = float(np.std(neighbours)) if neighbours.size > 1 else local_std
            norm_vol       = local_vol / global_std
            adaptive_mult  = base_multiplier * (1.0 + alpha * norm_vol)

            if abs(values[i] - local_med) > adaptive_mult * local_std:
                flags[i] = True

        return flags

    @staticmethod
    def _stage1_ml(
        values: np.ndarray, depths: np.ndarray, base_multiplier: float
    ) -> np.ndarray:
        """Enriched Isolation Forest on multi-feature residuals (ML mode).

        Features: value, gradient, curvature, rolling_std,
                  local_median_diff, depth_normalized.
        IF is a secondary scorer here, not primary gate.
        """
        try:
            from sklearn.ensemble import IsolationForest
        except ImportError:
            warnings.warn("scikit-learn not available; falling back to adaptive MAD.")
            return SpikeDetector._stage1_candidate(values, 5, base_multiplier)

        s   = pd.Series(values)
        med = s.rolling(window=5, center=True, min_periods=2).median().to_numpy()
        std = s.rolling(window=5, center=True, min_periods=2).std().to_numpy()

        # Rich feature set
        gradient     = np.gradient(values)
        curvature    = np.gradient(gradient)
        rolling_std  = np.where(np.isnan(std), np.nanstd(values), std)
        median_diff  = values - np.where(np.isnan(med), values, med)
        depth_norm   = (depths - depths.min()) / (depths.ptp() + 1e-9)

        features = np.column_stack([
            values, gradient, curvature, rolling_std, median_diff, depth_norm
        ])

        # Normalise features
        feat_mean = np.nanmean(features, axis=0)
        feat_std  = np.nanstd(features, axis=0)
        feat_std[feat_std == 0] = 1.0
        features  = (features - feat_mean) / feat_std

        contamination = float(np.clip(0.15 / max(float(base_multiplier), 0.5), 0.01, 0.10))
        model = IsolationForest(
            contamination=contamination,
            n_estimators=200,
            random_state=42,
        )
        return model.fit_predict(features) == -1

    # ── Stage 2: Gradient + Peak-Width ────────────────────────────────────────

    @staticmethod
    def _stage2_gradient_width(
        values: np.ndarray, max_spike_width: int
    ) -> tuple[np.ndarray, np.ndarray]:
        """Gradient symmetry (sign reversal) AND peak-width constraint.

        A point is flagged only if:
        1. Both neighbouring gradients reverse sign (up-then-down or vice versa).
        2. The width of the impulse ≤ max_spike_width samples.

        Returns
        -------
        flags       : bool array (True = passes gradient test)
        peak_widths : int array (impulse width at each point, 0 = not gradient)
        """
        n           = len(values)
        flags       = np.zeros(n, dtype=bool)
        peak_widths = np.zeros(n, dtype=int)

        if n < 3:
            return flags, peak_widths

        diff = np.diff(values)   # length n-1

        for i in range(1, n - 1):
            d_before = diff[i - 1]
            d_after  = diff[i]

            if d_before * d_after < 0:  # sign reversal
                # Measure how many consecutive samples share this sign pattern
                # (width = run of anomalous gradient before sign flips back)
                lo = i
                while lo > 0 and diff[lo - 1] * diff[i - 1] > 0:
                    lo -= 1
                hi = i
                while hi < n - 2 and diff[hi + 1] * diff[i] > 0:
                    hi += 1
                width = hi - lo + 1

                peak_widths[i] = width
                if width <= max_spike_width:
                    flags[i] = True

        return flags, peak_widths

    # ── Stage 3 ───────────────────────────────────────────────────────────────

    @staticmethod
    def _stage3_physics(values: np.ndarray, curve_name: str) -> np.ndarray:
        """Hard/soft physical limit violation flags."""
        n     = len(values)
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

    # ── Stage 4: Tiered Persistence ───────────────────────────────────────────

    @staticmethod
    def _stage4_persistence_tiered(
        candidates: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Tiered run-length persistence gate.

        Run length  Interpretation     Action
        ─────────── ──────────────── ─────────────────────────────
        1 – 2       Likely spike       Keep (allowed through)
        3 – 5       Suspicious         Keep but penalise confidence
        > 5         Likely geology     Hard-reject (remove label)

        Returns
        -------
        result      : bool array (False = hard-rejected as geology)
        run_lengths : int array (run length at each candidate position)
        """
        n           = len(candidates)
        result      = candidates.copy()
        run_lengths = np.zeros(n, dtype=int)

        i = 0
        while i < n:
            if candidates[i]:
                j = i
                while j < n and candidates[j]:
                    j += 1
                run_len = j - i
                for k in range(i, j):
                    run_lengths[k] = run_len
                if run_len > 5:       # geology — hard reject
                    result[i:j] = False
                i = j
            else:
                i += 1

        return result, run_lengths

    # ── Stage 6: Logical Gate + Weighted Confidence ───────────────────────────

    def _stage6_gated_confidence(
        self,
        s1: np.ndarray,
        s2: np.ndarray,
        s3: np.ndarray,
        s4: np.ndarray,
        s5_isolation: np.ndarray,
        values: np.ndarray,
        win: int,
        curve_name: str,
        run_lengths: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Logical gate → then compute weighted confidence only for survivors.

        Gate order (hard rejects):
          1. Not a candidate (Stage 1 negative) → reject
          2. Persistence hard-rejected (run > 5) → reject
          3. Physically valid AND cross-log correlated → reject

        Remaining candidates get confidence from weighted sum.
        Run-length 3–5 gets a 0.6× confidence penalty.

        Returns
        -------
        confidence    : float array [0, 1]
        hard_rejected : bool array (True = rejected by gate, skip threshold)
        """
        n = len(values)
        confidence    = np.zeros(n, dtype=float)
        hard_rejected = np.zeros(n, dtype=bool)

        # Build isolation score array aligned to full n
        iso_score = np.zeros(n, dtype=float)
        if len(s5_isolation) == n:
            iso_score = s5_isolation.astype(float)
        elif len(s5_isolation) > 0:
            candidate_idx = np.where(s1)[0]
            for k, idx in enumerate(candidate_idx):
                if k < len(s5_isolation) and idx < n:
                    iso_score[idx] = float(s5_isolation[k])

        local_score    = self._local_deviation_score(values, win, curve_name)
        gradient_score = s2.astype(float)
        physics_score  = self._physics_score(values, curve_name)

        # Determine if cross-log data is meaningful (non-trivial scores present)
        has_cross_log = bool(np.any(s5_isolation != 0.5) and len(s5_isolation) > 0)

        for i in range(n):
            # Gate 1: must be a Stage-1 candidate
            if not s1[i]:
                hard_rejected[i] = True
                continue

            # Gate 2: hard persistence rejection (run > 5 already cleared in s4)
            if not s4[i]:
                hard_rejected[i] = True
                continue

            # Gate 3: physically fine AND companion logs actively corroborate
            # the point → likely real geology, not noise.
            # Only applied when cross-log data is actually available.
            if has_cross_log and not s3[i] and iso_score[i] < 0.25:
                hard_rejected[i] = True
                continue

            # Weighted confidence
            conf = (
                self._W_LOCAL     * local_score[i] +
                self._W_GRADIENT  * gradient_score[i] +
                self._W_PHYSICS   * physics_score[i] +
                self._W_ISOLATION * iso_score[i]
            )

            # Penalise suspicious (run 3–5) but don't hard-reject
            if 3 <= run_lengths[i] <= 5:
                conf *= 0.6

            confidence[i] = float(np.clip(conf, 0.0, 1.0))

        return confidence, hard_rejected

    # ── Confidence helpers ────────────────────────────────────────────────────

    @staticmethod
    def _local_deviation_score(
        values: np.ndarray, win: int, curve_name: str
    ) -> np.ndarray:
        """Continuous adaptive MAD-normalised deviation [0, 1]."""
        n       = len(values)
        scores  = np.zeros(n, dtype=float)
        half_w  = win // 2
        alpha   = SpikeDetector._ADAPTIVE_ALPHA
        g_std   = float(np.nanstd(values)) or 1.0

        for i in range(1, n - 1):
            lo = max(0, i - half_w)
            hi = min(n, i + half_w + 1)
            neighbours = np.concatenate([values[lo:i], values[i + 1:hi]])
            if neighbours.size < 2:
                continue
            local_med = float(np.median(neighbours))
            local_mad = float(np.median(np.abs(neighbours - local_med)))
            local_std = max(local_mad * 1.4826, 1e-9)
            local_vol = float(np.std(neighbours)) if neighbours.size > 1 else local_std
            norm_vol  = local_vol / g_std
            eff_std   = local_std * (1.0 + alpha * norm_vol)
            raw_z     = abs(values[i] - local_med) / eff_std
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

    # ── Stage 7: Context-Aware Correction ────────────────────────────────────

    @staticmethod
    def _classify_spike_type(
        is_spike: np.ndarray,
        run_lengths: np.ndarray,
        s3_physics: np.ndarray,
    ) -> np.ndarray:
        """Assign a spike_type label to each flagged point.

        Labels
        ------
        "isolated"       – run length 1 (classic single-sample noise spike)
        "burst"          – run length 2–3 (short electronic burst)
        "physics"        – outside physical hard limits
        "geology_change" – longer run, kept as suspicious
        "none"           – not a spike
        """
        n          = len(is_spike)
        spike_type = np.full(n, "none", dtype=object)

        for i in np.where(is_spike)[0]:
            rl = int(run_lengths[i])
            if s3_physics[i]:
                spike_type[i] = "physics"
            elif rl == 1:
                spike_type[i] = "isolated"
            elif rl <= 3:
                spike_type[i] = "burst"
            else:
                spike_type[i] = "geology_change"

        return spike_type

    @staticmethod
    def _stage7_correction(
        values: np.ndarray,
        is_spike: np.ndarray,
        spike_type: np.ndarray,
        win: int,
        default_method: str,
    ) -> np.ndarray:
        """Context-aware correction method per spike_type.

        Type              Method
        ─────────────── ─────────────────────────────────────────
        isolated        local_median
        burst           Savitzky-Golay (fallback: local_median)
        physics         linear interpolation
        geology_change  keep original (NaN → no correction)
        fallback        uses *default_method*
        """
        n          = len(values)
        correction = np.full(n, np.nan)
        half_w     = win // 2

        if not is_spike.any():
            return correction

        spike_pos = np.where(is_spike)[0]
        clean_pos = np.where(~is_spike)[0]

        # ── isolated: local median ────────────────────────────────────────────
        isolated_idx = [i for i in spike_pos if spike_type[i] == "isolated"]
        for i in isolated_idx:
            lo = max(0, i - half_w)
            hi = min(n, i + half_w + 1)
            nb = np.concatenate([values[lo:i], values[i + 1:hi]])
            nb = nb[~np.isnan(nb)]
            correction[i] = float(np.median(nb)) if nb.size > 0 else np.nan

        # ── burst: Savitzky-Golay or local_median fallback ────────────────────
        burst_idx = [i for i in spike_pos if spike_type[i] == "burst"]
        if burst_idx:
            try:
                from scipy.signal import savgol_filter
                sg_win   = max(win | 1, 5)  # must be odd and ≥ 5
                smoothed = savgol_filter(values, window_length=sg_win, polyorder=2)
                for i in burst_idx:
                    correction[i] = float(smoothed[i])
            except (ImportError, Exception):
                for i in burst_idx:
                    lo = max(0, i - half_w)
                    hi = min(n, i + half_w + 1)
                    nb = np.concatenate([values[lo:i], values[i + 1:hi]])
                    nb = nb[~np.isnan(nb)]
                    correction[i] = float(np.median(nb)) if nb.size > 0 else np.nan

        # ── physics: linear interpolation ─────────────────────────────────────
        physics_idx = [i for i in spike_pos if spike_type[i] == "physics"]
        if physics_idx and clean_pos.size >= 2:
            for i in physics_idx:
                correction[i] = float(np.interp(i, clean_pos, values[clean_pos]))

        # ── geology_change: keep (no correction = NaN stays) ─────────────────
        # (already NaN by default)

        # ── fallback for any remaining un-classified spikes ───────────────────
        for i in spike_pos:
            if not np.isnan(correction[i]):
                continue
            if default_method == "local_median":
                lo = max(0, i - half_w)
                hi = min(n, i + half_w + 1)
                nb = np.concatenate([values[lo:i], values[i + 1:hi]])
                nb = nb[~np.isnan(nb)]
                correction[i] = float(np.median(nb)) if nb.size > 0 else np.nan
            elif default_method in ("linear", "cubic") and clean_pos.size >= 2:
                if default_method == "cubic" and clean_pos.size >= 4:
                    try:
                        from scipy.interpolate import CubicSpline
                        cs = CubicSpline(clean_pos, values[clean_pos], extrapolate=True)
                        correction[i] = float(cs(i))
                        continue
                    except (ImportError, Exception):
                        pass
                correction[i] = float(np.interp(i, clean_pos, values[clean_pos]))

        return correction
