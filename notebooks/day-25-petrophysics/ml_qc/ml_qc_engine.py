"""
ml_qc_engine.py
===============
Orchestrates the ML-based QC pipeline for well log anomaly detection.

Pipeline stages
---------------
1. Depth / curve extraction and depth-range filtering
2. Feature engineering (depth gradient, rolling stats, inter-curve ratios)
3. StandardScaler normalisation
4. Model fit + predict (via ml_qc_models.get_detector)
5. Result packaging into MLQCResult

Usage
-----
    from ml_qc.ml_qc_engine import run_ml_qc

    result = run_ml_qc(
        curve_series   = df["GR"],
        depth_series   = df["DEPTH"],
        curve_name     = "GR",
        all_curves_df  = df,
        model_name     = "Isolation Forest",
        contamination  = 0.05,
    )
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Optional

from ml_qc.ml_anomaly_report import MLQCResult
from ml_qc.ml_qc_models import get_detector


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_ml_qc(
    curve_series: pd.Series,
    depth_series: pd.Series,
    curve_name: str = "",
    all_curves_df: Optional[pd.DataFrame] = None,
    *,
    model_name: str = "Isolation Forest",
    contamination: float = 0.05,
    start_depth: Optional[float] = None,
    end_depth: Optional[float] = None,
    use_multi_curve: bool = True,
) -> MLQCResult:
    """Run the full ML QC pipeline and return an :class:`MLQCResult`.

    Parameters
    ----------
    curve_series    : primary log curve to analyse (pd.Series)
    depth_series    : depth values aligned to curve_series (pd.Series)
    curve_name      : mnemonic label (for reporting)
    all_curves_df   : full curve DataFrame for multi-curve feature engineering
    model_name      : one of ``ml_qc_models.MODEL_NAMES``
    contamination   : expected anomaly fraction [0.01, 0.49]
    start_depth     : optional top of analysis window
    end_depth       : optional base of analysis window
    use_multi_curve : if True, include companion curves as additional features
    """
    contamination = float(np.clip(contamination, 0.01, 0.49))

    # ── 1. Numeric conversion + depth-range filter ────────────────────────────
    depth_num = pd.to_numeric(depth_series, errors="coerce")
    curve_num = pd.to_numeric(curve_series,  errors="coerce")

    valid_mask = depth_num.notna() & curve_num.notna()
    if start_depth is not None:
        valid_mask &= depth_num >= float(start_depth)
    if end_depth is not None:
        valid_mask &= depth_num <= float(end_depth)

    if valid_mask.sum() < 10:
        return MLQCResult(
            curve_name=curve_name,
            model_name=model_name,
        )

    valid_idx   = depth_num.index[valid_mask]
    depth_valid = depth_num.loc[valid_idx]
    curve_valid = curve_num.loc[valid_idx]

    # ── 2. Feature engineering ────────────────────────────────────────────────
    feature_matrix, feature_names = _build_features(
        curve_valid, depth_valid,
        all_curves_df=all_curves_df,
        curve_name=curve_name,
        use_multi_curve=use_multi_curve,
    )

    # ── 3. Normalise ──────────────────────────────────────────────────────────
    X = _normalize(feature_matrix)

    if X.shape[0] < 5 or X.shape[1] < 1:
        return MLQCResult(curve_name=curve_name, model_name=model_name)

    # ── 4. Detect anomalies ───────────────────────────────────────────────────
    detector = get_detector(model_name, contamination=contamination)
    anomaly_mask_arr, score_arr = detector.fit_predict(X)
    importance_arr = detector.feature_importance()

    # ── 5. Package result ─────────────────────────────────────────────────────
    anomaly_mask   = pd.Series(anomaly_mask_arr, index=valid_idx, dtype=bool)
    anomaly_scores = pd.Series(score_arr,        index=valid_idx, dtype=float)

    n_samples   = int(valid_mask.sum())
    n_anomalies = int(anomaly_mask.sum())
    anom_pct    = 100.0 * n_anomalies / max(n_samples, 1)
    qc_score    = float(np.clip(100.0 - anom_pct, 0, 100))
    mean_score  = float(score_arr.mean()) if len(score_arr) else 0.0
    max_score   = float(score_arr.max())  if len(score_arr) else 0.0

    # Reliability: penalise missing values and anomaly rate
    missing_pct     = 100.0 * (depth_num.notna() & curve_num.isna()).sum() / max(len(depth_num), 1)
    reliability_pct = float(np.clip(100.0 - anom_pct * 0.5 - missing_pct * 0.3, 0, 100))

    return MLQCResult(
        curve_name       = curve_name,
        model_name       = model_name,
        n_samples        = n_samples,
        n_anomalies      = n_anomalies,
        anomaly_mask     = anomaly_mask,
        anomaly_scores   = anomaly_scores,
        feature_names    = feature_names,
        feature_importance = importance_arr,
        anomaly_pct      = anom_pct,
        mean_score       = mean_score,
        max_score        = max_score,
        qc_score         = qc_score,
        reliability_pct  = reliability_pct,
        depth_series     = depth_valid,
        curve_series     = curve_valid,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Feature engineering helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_features(
    curve: pd.Series,
    depth: pd.Series,
    *,
    all_curves_df: Optional[pd.DataFrame],
    curve_name: str,
    use_multi_curve: bool,
) -> tuple[np.ndarray, list[str]]:
    """Build a (n, d) feature matrix from the curve and optional companions."""

    cols: list[np.ndarray] = []
    names: list[str] = []

    # Primary value
    v = curve.to_numpy(dtype=float)
    cols.append(v)
    names.append(curve_name or "value")

    # Depth-gradient
    dz = depth.diff().fillna(1.0).to_numpy(dtype=float)
    dv = curve.diff().fillna(0.0).to_numpy(dtype=float)
    grad = np.where(np.abs(dz) > 1e-9, dv / dz, 0.0)
    cols.append(grad)
    names.append("gradient")

    # Rolling statistics (window=11)
    w = 11
    roll_mean = _rolling(curve, w, "mean")
    roll_std  = _rolling(curve, w, "std")
    residual  = v - roll_mean
    cols.append(residual)
    names.append("residual")
    cols.append(roll_std)
    names.append("rolling_std")

    # MAD-normalised deviation
    global_median = float(np.nanmedian(v))
    global_mad    = float(np.nanmedian(np.abs(v - global_median))) or 1.0
    mad_score = np.abs(v - global_median) / (global_mad * 1.4826 + 1e-9)
    cols.append(mad_score)
    names.append("mad_score")

    # Multi-curve companion features (skip primary curve)
    if use_multi_curve and all_curves_df is not None:
        companions = _select_companions(all_curves_df, curve_name, max_curves=3)
        for comp_name in companions:
            try:
                comp = pd.to_numeric(all_curves_df[comp_name], errors="coerce")
                comp_aligned = comp.loc[curve.index].fillna(comp.median())
                comp_arr = comp_aligned.to_numpy(dtype=float)
                cols.append(comp_arr)
                names.append(comp_name)
            except Exception:  # noqa: BLE001
                pass

    # Stack and replace NaN with column median
    X = np.column_stack(cols).astype(float)
    for j in range(X.shape[1]):
        col_j = X[:, j]
        nan_mask = ~np.isfinite(col_j)
        if nan_mask.any():
            col_j[nan_mask] = float(np.nanmedian(col_j[~nan_mask]) if (~nan_mask).any() else 0.0)

    return X, names


def _rolling(series: pd.Series, window: int, stat: str) -> np.ndarray:
    if stat == "mean":
        result = series.rolling(window, center=True, min_periods=3).mean()
    else:
        result = series.rolling(window, center=True, min_periods=3).std(ddof=1)
    return result.fillna(result.median()).to_numpy(dtype=float)


def _select_companions(df: pd.DataFrame, primary: str, max_curves: int = 3) -> list[str]:
    """Pick up to max_curves numeric columns that correlate with depth."""
    PREFERRED = ["GR", "RHOB", "NPHI", "DT", "RT", "CALI", "SP", "PE",
                 "ILD", "LLD", "PHIT", "SW", "VSH"]
    candidates = [c for c in df.columns
                  if c != primary and pd.api.types.is_numeric_dtype(df[c])]
    priority   = [c for c in PREFERRED if c in candidates]
    remainder  = [c for c in candidates if c not in priority]
    return (priority + remainder)[:max_curves]


def _normalize(X: np.ndarray) -> np.ndarray:
    """Robust z-score normalisation using median and IQR."""
    try:
        from sklearn.preprocessing import RobustScaler
        return RobustScaler().fit_transform(X)
    except ImportError:
        pass
    # Fallback: manual z-score
    mu  = np.nanmean(X, axis=0)
    std = np.nanstd(X,  axis=0)
    std[std == 0] = 1.0
    return (X - mu) / std
