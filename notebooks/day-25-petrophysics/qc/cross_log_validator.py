"""
cross_log_validator.py
======================
Stage 5 of the enterprise spike detector: cross-log correlation.

A point that appears anomalous in ONLY ONE curve is more likely to be
electronic noise or tool skip than a real geological feature. Real
formation changes (e.g., lithology boundaries, fractures) tend to be
visible in multiple logs simultaneously.

The validator computes an **isolation score** ∈ [0, 1] for each
candidate spike position:

  * 0.0   → several companion logs also show an anomaly at this depth
             (concordant multi-log response → probably real geology)
  * 1.0   → no other log shows an anomaly at this depth
             (single-log artefact → high confidence it's a noise spike)

v2 change: depth_tolerance_samples (default 3) expands the search
neighbourhood to ± N samples around the candidate.  This accounts for
real-world tool offsets, depth mismatch, and different vertical
resolution between logging runs.

The isolation score feeds into Stage 6 confidence weighting with
coefficient 0.20 (see spike_detector.py).

Usage
-----
    from qc.cross_log_validator import CrossLogValidator

    isolation_scores = CrossLogValidator().validate(
        candidate_indices=np.where(stage1_flags)[0],
        all_curves_df=df,
        valid_index=valid_index,
        depth_series=depth_series,
        window=15,
        mad_multiplier=4.5,
        depth_tolerance_samples=3,
    )
    # Returns float array, shape (len(candidate_indices),)
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


# Curves checked as companion logs.
# If the curve under test is one of these we do not include itself.
_COMPANION_MNEMONICS = [
    "GR", "SGR", "CGR",
    "RHOB", "DPHI",
    "NPHI", "TNPH",
    "DT", "DTC", "DTCO", "DTS",
    "RT", "ILD", "ILM", "LLD", "LLS", "MSFL", "RDEEP", "RMED",
    "CALI", "CAL",
    "SP",
    "PE", "PEF",
]


class CrossLogValidator:
    """Compute per-candidate isolation scores using companion log anomalies."""

    def validate(
        self,
        candidate_indices: np.ndarray,
        all_curves_df: pd.DataFrame,
        valid_index: pd.Index,
        depth_series: pd.Series,
        window: int = 11,
        mad_multiplier: float = 4.0,
        depth_tolerance_samples: int = 3,
    ) -> np.ndarray:
        """Return isolation scores for each candidate spike index.

        Parameters
        ----------
        candidate_indices : np.ndarray[int]
            Positions (within the valid subset) that Stage 1 flagged.
        all_curves_df : pd.DataFrame
            Full curve table for the current well.
        valid_index : pd.Index
            Index labels of the valid (finite) subset used in Stage 1.
        depth_series : pd.Series
            Depth values aligned to *all_curves_df*.
        window : int
            Analysis window for local MAD computation.
        mad_multiplier : float
            Multiplier for local MAD threshold (same as Stage 1).
        depth_tolerance_samples : int
            ± sample tolerance when checking companion log anomalies.
            Handles tool offsets, depth mismatch, and differing vertical
            resolution.  Default 3 samples (≈ 0.45 ft at 0.15 m sampling).

        Returns
        -------
        np.ndarray[float]  –  shape ``(len(candidate_indices),)``
        """
        n_candidates = len(candidate_indices)
        if n_candidates == 0:
            return np.zeros(0, dtype=float)

        # Identify companion columns in the DataFrame
        companion_cols = self._find_companion_cols(all_curves_df)
        if not companion_cols:
            # No companion logs → neutral score (don't penalise or boost)
            return np.full(n_candidates, 0.5, dtype=float)

        # Pre-compute anomaly flags for each companion log over the valid index
        companion_flags: dict[str, np.ndarray] = {}
        for col in companion_cols:
            col_series = pd.to_numeric(all_curves_df[col], errors="coerce")
            col_valid  = col_series.loc[valid_index].to_numpy(dtype=float)
            if np.count_nonzero(~np.isnan(col_valid)) < 5:
                continue
            companion_flags[col] = self._local_mad_flags(
                col_valid, window, mad_multiplier
            )

        if not companion_flags:
            return np.full(n_candidates, 0.5, dtype=float)

        flag_matrix = np.column_stack(list(companion_flags.values()))  # (n_valid, n_comp)
        n_valid     = flag_matrix.shape[0]
        n_comp      = flag_matrix.shape[1]

        # Effective search half-window: combines the MAD analysis window
        # with the extra depth-tolerance samples
        search_half = max(window // 2, 1) + depth_tolerance_samples

        isolation_scores = np.zeros(n_candidates, dtype=float)

        for k, ci in enumerate(candidate_indices):
            lo = max(0, ci - search_half)
            hi = min(n_valid, ci + search_half + 1)
            window_flags = flag_matrix[lo:hi, :]   # (neighbourhood, n_comp)

            # Companion responds if ANY sample in the tolerance window is flagged
            companion_responds = window_flags.any(axis=0)   # bool (n_comp,)
            n_responding       = int(companion_responds.sum())

            isolation_scores[k] = 1.0 - n_responding / n_comp

        return np.clip(isolation_scores, 0.0, 1.0)

    # ── internals ─────────────────────────────────────────────────────────────

    @staticmethod
    def _find_companion_cols(df: pd.DataFrame) -> list[str]:
        """Return columns in *df* that match known petrophysical mnemonics. """
        cols       = []
        upper_cols = {c.upper().strip(): c for c in df.columns}
        for mnem in _COMPANION_MNEMONICS:
            if mnem in upper_cols:
                cols.append(upper_cols[mnem])
            else:
                for ucol, original in upper_cols.items():
                    if mnem in ucol and original not in cols:
                        cols.append(original)
                        break
        return cols

    @staticmethod
    def _local_mad_flags(
        values: np.ndarray, window: int, multiplier: float
    ) -> np.ndarray:
        """Rolling MAD anomaly detection aligned with Stage 1 logic."""
        n      = len(values)
        flags  = np.zeros(n, dtype=bool)
        half_w = window // 2

        for i in range(1, n - 1):
            if np.isnan(values[i]):
                continue
            lo = max(0, i - half_w)
            hi = min(n, i + half_w + 1)
            neighbours = np.concatenate([values[lo:i], values[i + 1:hi]])
            neighbours = neighbours[~np.isnan(neighbours)]
            if neighbours.size < 2:
                continue
            local_med = float(np.median(neighbours))
            local_mad = float(np.median(np.abs(neighbours - local_med)))
            local_std = max(local_mad * 1.4826, 1e-9)
            if abs(values[i] - local_med) > multiplier * local_std:
                flags[i] = True

        return flags
