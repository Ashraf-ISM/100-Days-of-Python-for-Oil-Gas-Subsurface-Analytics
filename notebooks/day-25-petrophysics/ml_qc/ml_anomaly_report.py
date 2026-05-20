"""
ml_anomaly_report.py
====================
Dataclass for ML QC results and helper to build issue-table rows.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MLQCResult:
    """Container for a single ML-QC run result."""

    # Core outputs
    curve_name: str = ""
    model_name: str = ""
    n_samples: int = 0
    n_anomalies: int = 0

    # Per-sample boolean anomaly mask (aligned to the *valid* depth index)
    anomaly_mask: Optional[pd.Series] = None

    # Per-sample anomaly score (higher → more anomalous; aligned to valid index)
    anomaly_scores: Optional[pd.Series] = None

    # Feature names used for detection
    feature_names: List[str] = field(default_factory=list)

    # Feature importance / contribution scores (same order as feature_names)
    feature_importance: Optional[np.ndarray] = None

    # Summary metrics
    anomaly_pct: float = 0.0          # % of samples flagged
    mean_score: float = 0.0           # mean anomaly score
    max_score: float = 0.0            # worst-case score
    qc_score: float = 100.0           # 100 - anomaly_pct (clamped 0–100)
    reliability_pct: float = 100.0    # data-quality reliability estimate

    # Raw depth + curve series (visible window only) for plotting
    depth_series: Optional[pd.Series] = None
    curve_series: Optional[pd.Series] = None

    # ── convenience properties ────────────────────────────────────────────────

    @property
    def n_good(self) -> int:
        return self.n_samples - self.n_anomalies

    @property
    def good_pct(self) -> float:
        return 100.0 - self.anomaly_pct

    @property
    def severity_label(self) -> str:
        if self.anomaly_pct < 5:
            return "Good"
        if self.anomaly_pct < 15:
            return "Warning"
        return "Critical"


# ─────────────────────────────────────────────────────────────────────────────
# Row builder for the issues table
# ─────────────────────────────────────────────────────────────────────────────

def build_anomaly_rows(
    result: MLQCResult,
    max_rows: int = 250,
) -> List[Tuple[str, str, str, str, str]]:
    """Build table rows from an :class:`MLQCResult`.

    Returns
    -------
    List of (depth_str, curve, value_str, score_str, severity) tuples.
    """
    if result.anomaly_mask is None or result.depth_series is None:
        return []

    mask   = result.anomaly_mask
    depth  = result.depth_series
    curve  = result.curve_series
    scores = result.anomaly_scores

    rows: List[Tuple[str, str, str, str, str]] = []
    for idx in depth.index[mask][:max_rows]:
        d_str = _fmt(depth.loc[idx], ".2f")
        v_str = _fmt(curve.loc[idx] if curve is not None else np.nan, ".4f")
        s_val = float(scores.loc[idx]) if (scores is not None and idx in scores.index) else np.nan
        s_str = _fmt(s_val, ".3f")
        sev   = _severity_from_score(s_val, result.max_score)
        rows.append((d_str, result.curve_name, v_str, s_str, sev))

    rows.sort(key=lambda r: _safe_float(r[0]))
    return rows


def _fmt(value, spec: str) -> str:
    try:
        return format(float(value), spec)
    except Exception:
        return "—"


def _safe_float(s: str) -> float:
    try:
        return float(s)
    except Exception:
        return float("inf")


def _severity_from_score(score: float, max_score: float) -> str:
    if np.isnan(score) or max_score == 0:
        return "Unknown"
    ratio = score / max(max_score, 1e-9)
    if ratio > 0.75:
        return "Critical"
    if ratio > 0.40:
        return "Warning"
    return "Info"
