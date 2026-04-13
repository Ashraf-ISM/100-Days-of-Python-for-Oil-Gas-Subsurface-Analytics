"""
facies_classifications/data_loader.py
======================================
Responsible for:
  - Loading a LAS file into a pandas DataFrame
  - Filtering to a depth interval
  - Basic null handling / despiking
  - Building the raw input-curve inventory

All public functions are pure (no Qt imports) so they can be unit-tested or
called from a CLI without a running GUI.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
LoadResult = Tuple[Optional[pd.DataFrame], Dict[str, Any], str]
"""(dataframe | None, metadata_dict, status_message)"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_las_file(
    las_path: str | Path,
    top_depth: float = -1.0,
    base_depth: float = -1.0,
    null_strategy: str = "interpolate",
    sampling_m: float = 0.10,
    despike: bool = True,
    normalize_by_zone: bool = False,
    zone_column: str | None = None,
) -> LoadResult:
    """Load a LAS file and return a tidy DataFrame ready for feature engineering.

    Parameters
    ----------
    las_path:
        Absolute path to the ``.las`` file.
    top_depth, base_depth:
        Depth interval to clip the data to (both in metres).
        Pass ``-1`` to use the full extent of the log.
    null_strategy:
        One of ``"interpolate"``, ``"median_fill"``, or ``"drop"``.
    sampling_m:
        Re-sample the log to this step size (metres). ``0`` = keep original.
    despike:
        Apply a rolling-median despike filter to numeric curves.
    normalize_by_zone:
        If ``True`` and *zone_column* is available, normalize each curve
        per zone.
    zone_column:
        Column name that carries formation / zone labels.

    Returns
    -------
    (df, metadata, message)
        *df* is ``None`` on failure; *metadata* carries summary statistics;
        *message* is a human-readable status string.
    """
    las_path = Path(las_path)
    if not las_path.exists():
        return None, {}, f"File not found: {las_path}"

    # --- Try lasio first, fall back to a raw CSV-like parser ---------------
    df, meta = _read_las(las_path)
    if df is None:
        return None, {}, f"Could not parse LAS file: {las_path.name}"

    # --- Identify the depth column -----------------------------------------
    depth_col = _find_depth_column(df)
    if depth_col is None:
        return None, meta, "No depth column (DEPTH / DEPT / MD) found in LAS."

    df[depth_col] = pd.to_numeric(df[depth_col], errors="coerce")
    df = df.dropna(subset=[depth_col]).sort_values(depth_col).reset_index(drop=True)

    # --- Depth clipping -------------------------------------------------------
    if top_depth >= 0:
        df = df[df[depth_col] >= top_depth]
    if base_depth > top_depth >= 0:
        df = df[df[depth_col] <= base_depth]
    df = df.reset_index(drop=True)

    if df.empty:
        return None, meta, "No data rows remain after depth clipping."

    # --- Optional re-sampling -------------------------------------------------
    if sampling_m > 0:
        df = _resample_log(df, depth_col, sampling_m)

    # --- Null handling --------------------------------------------------------
    df = _handle_nulls(df, strategy=null_strategy, depth_col=depth_col)

    # --- Despiking ------------------------------------------------------------
    if despike:
        df = _despike(df, depth_col)

    # --- Zone-based normalisation --------------------------------------------
    if normalize_by_zone and zone_column and zone_column in df.columns:
        df = _normalize_by_zone(df, zone_column, depth_col)

    # --- Build metadata -------------------------------------------------------
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c != depth_col]
    total_rows = len(df)
    completeness = {
        col: round(100.0 * df[col].notna().mean(), 1) for col in numeric_cols
    }
    null_clusters = _count_null_clusters(df, numeric_cols)
    spike_count  = _count_spikes(df, numeric_cols) if not despike else 0

    meta.update(
        {
            "las_file": las_path.name,
            "depth_col": depth_col,
            "depth_range": (float(df[depth_col].min()), float(df[depth_col].max())),
            "total_rows": total_rows,
            "numeric_curves": numeric_cols,
            "completeness": completeness,
            "null_clusters": null_clusters,
            "spike_count": spike_count,
        }
    )

    zone_summary = _build_zone_summary(df, depth_col, zone_column)
    meta["zone_summary"] = zone_summary

    status = (
        f"Loaded {total_rows:,} samples × {len(numeric_cols)} curves "
        f"from {las_path.name}  "
        f"[{float(df[depth_col].min()):.1f} – {float(df[depth_col].max()):.1f} m]"
    )
    return df, meta, status


def build_qc_report(df: pd.DataFrame, metadata: Dict[str, Any]) -> str:
    """Return a plain-text QC summary suitable for displaying in txtQcNotes."""
    lines = ["QC Report — " + metadata.get("las_file", "unknown")]
    lines.append("=" * 56)
    lines.append(f"Depth range : {metadata.get('depth_range', ('?', '?'))}")
    lines.append(f"Total rows  : {metadata.get('total_rows', '?'):,}")
    lines.append(f"Null clusters: {metadata.get('null_clusters', '?')}")
    lines.append(f"Spikes flagged: {metadata.get('spike_count', '?')}")
    lines.append("")
    lines.append("Curve completeness:")
    for curve, pct in metadata.get("completeness", {}).items():
        bar = "█" * int(pct / 5)
        lines.append(f"  {curve:<10} {pct:5.1f}%  {bar}")
    return "\n".join(lines)


def get_inventory_rows(metadata: Dict[str, Any]) -> list[tuple[str, str, str]]:
    """Return [(log_name, unit, status), …] for populating tblInputLogs."""
    standard_units = {
        "GR": "API", "RHOB": "g/cc", "NPHI": "v/v", "DT": "us/ft",
        "ILD": "ohm.m", "PEF": "barn/e", "CALI": "in", "SP": "mV",
        "RT": "ohm.m", "LLD": "ohm.m", "LLS": "ohm.m",
    }
    optional_curves = {"PEF", "CALI", "SP"}
    rows = []
    for curve in metadata.get("numeric_curves", []):
        unit   = standard_units.get(curve.upper(), "")
        status = "Optional" if curve.upper() in optional_curves else "Loaded"
        rows.append((curve, unit, status))
    return rows


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _read_las(path: Path) -> tuple[Optional[pd.DataFrame], dict]:
    """Try lasio, then fall back to raw text parse."""
    try:
        import lasio
        las = lasio.read(str(path))
        df  = las.df().reset_index()
        # column 'DEPT' or 'DEPTH' may be the index
        meta = {"well_name": las.well.WELL.value if hasattr(las.well, "WELL") else ""}
        return df, meta
    except Exception:
        pass

    # Fallback: read as CSV skipping comment lines
    try:
        lines = path.read_text(errors="replace").splitlines()
        data_lines = [l for l in lines if not l.strip().startswith("~") and l.strip()]
        # First non-comment line after ~A is the header
        header_idx = next(
            (i for i, l in enumerate(lines) if l.strip().startswith("~A")), None
        )
        if header_idx is None:
            return None, {}
        col_line = lines[header_idx + 1] if header_idx + 1 < len(lines) else ""
        cols = col_line.split() or ["DEPTH"]
        raw  = [l for l in lines[header_idx + 2:] if l.strip() and not l.strip().startswith("#")]
        rows = [r.split() for r in raw if r.strip()]
        df   = pd.DataFrame(rows, columns=cols[:max(len(r) for r in rows)] if rows else cols)
        for c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df, {}
    except Exception:
        return None, {}


def _find_depth_column(df: pd.DataFrame) -> Optional[str]:
    candidates = ["DEPTH", "DEPT", "MD", "MEASUREDDEPTH", "DEPTH_M"]
    for c in df.columns:
        if str(c).upper().replace(" ", "") in candidates:
            return c
    # Any column whose name contains DEPTH / DEPT
    for c in df.columns:
        norm = str(c).upper().replace(" ", "")
        if "DEPTH" in norm or "DEPT" in norm:
            return c
    return None


def _resample_log(df: pd.DataFrame, depth_col: str, step: float) -> pd.DataFrame:
    """Linear re-sample the log DataFrame to a regular *step* spacing."""
    d_min = float(df[depth_col].min())
    d_max = float(df[depth_col].max())
    new_depths = np.arange(d_min, d_max + step, step)
    df_out = pd.DataFrame({depth_col: new_depths})
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c != depth_col]
    df = df.sort_values(depth_col)
    for col in numeric_cols:
        df_out[col] = np.interp(
            new_depths,
            df[depth_col].to_numpy(dtype=float),
            df[col].fillna(method="ffill").fillna(method="bfill").to_numpy(dtype=float),
        )
    # Carry any string columns as NaN
    str_cols = [c for c in df.columns if c not in numeric_cols and c != depth_col]
    for col in str_cols:
        df_out[col] = np.nan
    return df_out


def _handle_nulls(df: pd.DataFrame, strategy: str, depth_col: str) -> pd.DataFrame:
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c != depth_col]
    if strategy == "interpolate":
        df[numeric_cols] = df[numeric_cols].interpolate(limit_direction="both")
    elif strategy == "median_fill":
        for col in numeric_cols:
            df[col] = df[col].fillna(df[col].median())
    elif strategy == "drop":
        df = df.dropna(subset=numeric_cols).reset_index(drop=True)
    return df


def _despike(df: pd.DataFrame, depth_col: str, window: int = 5, threshold: float = 3.0) -> pd.DataFrame:
    """Median-based despike: replace values deviating > *threshold* IQR."""
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c != depth_col]
    for col in numeric_cols:
        s = df[col].copy()
        rolling_med = s.rolling(window, center=True, min_periods=1).median()
        diff = (s - rolling_med).abs()
        mad = diff.rolling(window, center=True, min_periods=1).median()
        mask = diff > threshold * (mad + 1e-9)
        df[col] = s.where(~mask, rolling_med)
    return df


def _normalize_by_zone(df: pd.DataFrame, zone_col: str, depth_col: str) -> pd.DataFrame:
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c != depth_col and c != zone_col]
    for zone, grp in df.groupby(zone_col):
        idx = grp.index
        for col in numeric_cols:
            mn = df.loc[idx, col].min()
            mx = df.loc[idx, col].max()
            if mx - mn > 1e-9:
                df.loc[idx, col] = (df.loc[idx, col] - mn) / (mx - mn)
    return df


def _count_null_clusters(df: pd.DataFrame, numeric_cols: list[str]) -> int:
    """Count null runs across all numeric columns."""
    total = 0
    for col in numeric_cols:
        null_mask = df[col].isna()
        in_run = False
        for v in null_mask:
            if v and not in_run:
                total += 1
                in_run = True
            elif not v:
                in_run = False
    return total


def _count_spikes(df: pd.DataFrame, numeric_cols: list[str], window: int = 5, threshold: float = 3.0) -> int:
    total = 0
    for col in numeric_cols:
        s = df[col].copy()
        rolling_med = s.rolling(window, center=True, min_periods=1).median()
        diff = (s - rolling_med).abs()
        mad  = diff.rolling(window, center=True, min_periods=1).median()
        total += int((diff > threshold * (mad + 1e-9)).sum())
    return total


def _build_zone_summary(
    df: pd.DataFrame,
    depth_col: str,
    zone_col: Optional[str],
) -> list[dict]:
    """Return a list of {zone, top, base, rows} dicts for tblZoneSummary."""
    if zone_col and zone_col in df.columns:
        rows = []
        for zone, grp in df.groupby(zone_col):
            rows.append(
                {
                    "zone": str(zone),
                    "top": float(grp[depth_col].min()),
                    "base": float(grp[depth_col].max()),
                    "rows": len(grp),
                }
            )
        return rows
    else:
        # Synthetic single zone
        return [
            {
                "zone": "Full Log",
                "top": float(df[depth_col].min()),
                "base": float(df[depth_col].max()),
                "rows": len(df),
            }
        ]
