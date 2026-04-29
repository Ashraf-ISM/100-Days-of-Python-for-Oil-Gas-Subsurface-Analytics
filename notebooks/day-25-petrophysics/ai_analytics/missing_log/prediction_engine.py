"""
prediction_engine.py
Core analytical utilities for the Missing Log Prediction module.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# Common petrophysical log → unit mapping
_UNIT_MAP = {
    "GR":    "API",
    "NPHI":  "V/V",
    "RHOB":  "g/cc",
    "DT":    "µs/ft",
    "DTC":   "µs/ft",
    "DTS":   "µs/ft",
    "RT":    "ohm.m",
    "RD":    "ohm.m",
    "ILD":   "ohm.m",
    "ILM":   "ohm.m",
    "RILD":  "ohm.m",
    "RILM":  "ohm.m",
    "RS":    "ohm.m",
    "RM":    "ohm.m",
    "CALI":  "in",
    "PE":    "b/e",
    "SP":    "mV",
    "MD":    "m",
    "DEPT":  "m",
    "DEPTH": "m",
    "PORO":  "V/V",
    "PHI":   "V/V",
    "SW":    "V/V",
    "VCL":   "V/V",
    "VSH":   "V/V",
    "TEMP":  "°C",
}


class MissingLogEngine:
    """
    Core analytics engine for the Missing Log Prediction module.

    Provides data statistics, feature suggestion, interval detection
    and unit guessing — all from a pandas DataFrame.
    """

    def __init__(self, data: pd.DataFrame):
        self.df = data

    # ── statistics ────────────────────────────────────────────────────────────

    def get_log_statistics(self, target_log: str) -> dict | None:
        """Return a statistics dict for a single log column."""
        if target_log not in self.df.columns:
            return None

        series  = self.df[target_log]
        total   = len(series) 
        missing = int(series.isna().sum())
        pct     = (missing / total * 100) if total > 0 else 0.0

        result: dict = {
            "total":       total,
            "missing":     missing,
            "missing_pct": pct,
            "valid":       total - missing,
        }

        numeric = pd.to_numeric(series, errors="coerce").dropna()
        if not numeric.empty:
            result.update({
                "min":  float(numeric.min()),
                "max":  float(numeric.max()),
                "mean": float(numeric.mean()),
                "std":  float(numeric.std()),
            })

        return result

    # ── missing intervals ─────────────────────────────────────────────────────

    def count_missing_intervals(self, target_log: str) -> int:
        """Return the number of contiguous NaN runs in the target log."""
        if target_log not in self.df.columns:
            return 0
        is_nan = self.df[target_log].isna()
        count  = 0
        in_gap = False
        for flag in is_nan:
            if flag and not in_gap:
                count += 1
                in_gap = True
            elif not flag:
                in_gap = False
        return count

    def get_missing_intervals(self, target_log: str) -> list[tuple[int, int]]:
        """Return list of (start_idx, end_idx) for each NaN run."""
        if target_log not in self.df.columns:
            return []
        is_nan = self.df[target_log].isna()
        intervals: list[tuple[int, int]] = []
        in_gap = False
        start  = 0
        for i, flag in enumerate(is_nan):
            if flag and not in_gap:
                start  = i
                in_gap = True
            elif not flag and in_gap:
                intervals.append((start, i))
                in_gap = False
        if in_gap:
            intervals.append((start, len(is_nan)))
        return intervals

    # ── feature suggestion ────────────────────────────────────────────────────

    def suggest_features(self, target_log: str, top_n: int = 5) -> list[str]:
        """
        Return top_n log names most correlated with target_log
        (by absolute Pearson correlation).
        """
        if target_log not in self.df.columns:
            return []

        numeric_df = self.df.select_dtypes(include=[np.number])
        if target_log not in numeric_df.columns:
            return []

        corr = numeric_df.corr()[target_log].abs()
        corr = corr.drop(target_log, errors="ignore")
        return corr.sort_values(ascending=False).head(top_n).index.tolist()


    # ── unit guessing ─────────────────────────────────────────────────────────

    def guess_unit(self, log_name: str) -> str:
        """
        Best-effort unit mapping based on the log name prefix.
        Falls back to '—' if unknown.
        """
        key = log_name.upper().split("_")[0].split("-")[0].strip()
        # Try exact match first
        if key in _UNIT_MAP:
            return _UNIT_MAP[key]
        # Try partial match
        for k, v in _UNIT_MAP.items():
            if key.startswith(k) or k in key:
                return v
        return "—"
