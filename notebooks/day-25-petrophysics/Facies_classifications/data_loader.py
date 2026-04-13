"""
facies_classifications/data_loader.py
======================================
Responsible for:
  - Loading a LAS file  **or**  a CSV file into a pandas DataFrame
  - Filtering to a depth interval / well name
  - Basic null handling / despiking
  - Building the raw input-curve inventory

CSV format supported
--------------------
The loader handles the canonical facies-classification CSV layout::

    Facies, Formation, Well Name, Depth, GR, ILD_log10, DeltaPHI, PHIND,
    PE, NM_M, RELPOS, PHID, NPHI, VSH, Bulk Density, PE_filled

Key rules applied automatically
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* The **depth column** is found by name heuristic (DEPTH / DEPT / Depth / MD …).
* **Label columns** (Facies / Lithology / Class / Label …) are kept as integers
  and excluded from the numeric-curve list used for feature engineering.
* **Well / Formation / string flag columns** are preserved as-is and never
  normalised or despiked.
* When a multi-well CSV is loaded, the user can optionally filter to a single
  well via *well_filter*.

All public functions are pure (no Qt imports) so they can be unit-tested or
called from a CLI without a running GUI.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
LoadResult = Tuple[Optional[pd.DataFrame], Dict[str, Any], str]
"""(dataframe | None, metadata_dict, status_message)"""


# ---------------------------------------------------------------------------
# Known column roles  (all comparisons are done in UPPER-CASE)
# ---------------------------------------------------------------------------
_LABEL_CANDIDATES: tuple[str, ...] = (
    "FACIES", "LITHOLOGY", "LITH", "CLASS", "LABEL", "FACIE",
    "LITHO", "ROCK_TYPE", "ROCKTYPE",
)

_WELL_CANDIDATES: tuple[str, ...] = (
    "WELL NAME", "WELL_NAME", "WELLNAME", "WELL", "API", "UWI",
)

_FORMATION_CANDIDATES: tuple[str, ...] = (
    "FORMATION", "FORM", "ZONE", "INTERVAL", "MEMBER",
)

# Columns whose values are categorical flags/strings (e.g. "Original" / "Filled")
_FLAG_CANDIDATES: tuple[str, ...] = (
    "PE_FILLED", "FLAG", "SOURCE", "DATA_FLAG", "STATUS",
)


# ---------------------------------------------------------------------------
# Public API  – CSV
# ---------------------------------------------------------------------------

def load_csv_file(
    csv_path: str | Path,
    top_depth: float = -1.0,
    base_depth: float = -1.0,
    well_filter: str | None = None,
    null_strategy: str = "interpolate",
    sampling_m: float = 0.0,
    despike: bool = True,
    normalize_by_zone: bool = False,
    zone_column: str | None = None,
    label_column: str | None = None,
    separator: str = ",",
) -> LoadResult:
    """Load a facies-classification CSV and return a tidy DataFrame.

    Parameters
    ----------
    csv_path:
        Absolute path to the ``.csv`` (or ``.txt``) file.
    top_depth, base_depth:
        Depth interval to clip to (metres). ``-1`` = use full extent.
    well_filter:
        If provided, keep only rows where the well-name column equals this
        value.  Case-insensitive.  Pass ``None`` to load all wells.
    null_strategy:
        One of ``"interpolate"``, ``"median_fill"``, or ``"drop"``.
    sampling_m:
        Re-sample the log to this depth-step (metres). ``0`` = keep original.
        .. note::
            For multi-well CSVs, re-sampling is applied **per well** so that
            depth resets between wells are honoured.
    despike:
        Apply a rolling-median despike filter to numeric curves.
    normalize_by_zone:
        If ``True`` and *zone_column* is available, normalise each curve
        per zone.
    zone_column:
        Column name that carries formation / zone labels.
    label_column:
        Override auto-detection of the facies/label column.  Rows with NaN
        in this column are dropped before any other processing.
    separator:
        CSV delimiter (default ``","``).

    Returns
    -------
    (df, metadata, message)
        *df* is ``None`` on failure; *metadata* carries summary statistics;
        *message* is a human-readable status string.
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        return None, {}, f"File not found: {csv_path}"

    # ------------------------------------------------------------------
    # 1. Read raw CSV
    # ------------------------------------------------------------------
    df, meta = _read_csv(csv_path, separator)
    if df is None or df.empty:
        return None, {}, f"Could not parse CSV file: {csv_path.name}"

    # ------------------------------------------------------------------
    # 2. Identify special columns
    # ------------------------------------------------------------------
    depth_col = _find_depth_column(df)
    if depth_col is None:
        return None, meta, "No depth column (Depth / DEPTH / DEPT / MD) found in CSV."

    lbl_col   = label_column or _detect_label_column(df)
    well_col  = _detect_well_column(df)
    form_col  = zone_column or _detect_formation_column(df)
    flag_cols = _detect_flag_columns(df)

    # Columns we will NEVER treat as numeric feature curves
    reserved = {depth_col}
    for c in [lbl_col, well_col, form_col] + flag_cols:
        if c:
            reserved.add(c)

    # ------------------------------------------------------------------
    # 3. Coerce depth to float; drop undetermined rows
    # ------------------------------------------------------------------
    df[depth_col] = pd.to_numeric(df[depth_col], errors="coerce")
    df = df.dropna(subset=[depth_col]).sort_values(
        [well_col, depth_col] if well_col else [depth_col]
    ).reset_index(drop=True)

    # ------------------------------------------------------------------
    # 4. Coerce numeric feature columns
    # ------------------------------------------------------------------
    for col in df.columns:
        if col not in reserved:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ------------------------------------------------------------------
    # 5. Drop rows with NaN label (unlabelled samples cannot be used for
    #    supervised training or evaluation)
    # ------------------------------------------------------------------
    if lbl_col and lbl_col in df.columns:
        before = len(df)
        df = df.dropna(subset=[lbl_col]).reset_index(drop=True)
        dropped_unlabelled = before - len(df)
    else:
        dropped_unlabelled = 0

    # Ensure label is stored as integer
    if lbl_col and lbl_col in df.columns:
        df[lbl_col] = pd.to_numeric(df[lbl_col], errors="coerce").astype("Int64")

    # ------------------------------------------------------------------
    # 6. Well-name filter
    # ------------------------------------------------------------------
    all_wells: list[str] = []
    if well_col and well_col in df.columns:
        all_wells = sorted(df[well_col].dropna().unique().tolist())
        if well_filter:
            mask = df[well_col].str.strip().str.upper() == well_filter.strip().upper()
            df = df[mask].reset_index(drop=True)
            if df.empty:
                available = ", ".join(all_wells)
                return (
                    None, meta,
                    f"No data for well '{well_filter}'. "
                    f"Available wells: {available}"
                )

    # ------------------------------------------------------------------
    # 7. Depth clipping
    # ------------------------------------------------------------------
    if top_depth >= 0:
        df = df[df[depth_col] >= top_depth]
    if base_depth > top_depth >= 0:
        df = df[df[depth_col] <= base_depth]
    df = df.reset_index(drop=True)

    if df.empty:
        return None, meta, "No data rows remain after depth clipping / well filter."

    # ------------------------------------------------------------------
    # 8. Per-well re-sampling (so depth resets between wells are safe)
    # ------------------------------------------------------------------
    if sampling_m > 0:
        if well_col and well_col in df.columns:
            parts = []
            for _, grp in df.groupby(well_col, sort=False):
                parts.append(_resample_log(grp.reset_index(drop=True), depth_col, sampling_m))
            df = pd.concat(parts, ignore_index=True)
        else:
            df = _resample_log(df, depth_col, sampling_m)

    # ------------------------------------------------------------------
    # 9. Null handling  (numeric feature columns only)
    # ------------------------------------------------------------------
    df = _handle_nulls(df, strategy=null_strategy, depth_col=depth_col,
                       exclude_cols=reserved)

    # ------------------------------------------------------------------
    # 10. Despiking  (numeric feature columns only)
    # ------------------------------------------------------------------
    if despike:
        df = _despike(df, depth_col, exclude_cols=reserved)

    # ------------------------------------------------------------------
    # 11. Zone-based normalisation
    # ------------------------------------------------------------------
    if normalize_by_zone and form_col and form_col in df.columns:
        df = _normalize_by_zone(df, form_col, depth_col, exclude_cols=reserved)

    # ------------------------------------------------------------------
    # 12. Build metadata
    # ------------------------------------------------------------------
    numeric_cols = [
        c for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c])
        and c not in reserved
        and c != lbl_col
    ]
    total_rows = len(df)
    completeness = {
        col: round(100.0 * df[col].notna().mean(), 1)
        for col in numeric_cols
    }
    null_clusters = _count_null_clusters(df, numeric_cols)
    spike_count   = _count_spikes(df, numeric_cols) if not despike else 0

    # Facies / class distribution
    facies_dist: dict = {}
    if lbl_col and lbl_col in df.columns:
        facies_dist = (
            df[lbl_col]
            .value_counts()
            .sort_index()
            .to_dict()
        )

    meta.update(
        {
            "source_file"       : csv_path.name,
            "file_type"         : "csv",
            "depth_col"         : depth_col,
            "depth_range"       : (float(df[depth_col].min()), float(df[depth_col].max())),
            "total_rows"        : total_rows,
            "numeric_curves"    : numeric_cols,
            "completeness"      : completeness,
            "null_clusters"     : null_clusters,
            "spike_count"       : spike_count,
            "label_column"      : lbl_col,
            "well_column"       : well_col,
            "formation_column"  : form_col,
            "flag_columns"      : flag_cols,
            "all_wells"         : all_wells,
            "active_well_filter": well_filter,
            "facies_distribution": facies_dist,
            "dropped_unlabelled": dropped_unlabelled,
        }
    )

    zone_summary = _build_zone_summary(df, depth_col, form_col)
    meta["zone_summary"] = zone_summary

    # Build a concise status message
    well_part = (
        f"  well='{well_filter}'" if well_filter
        else f"  {len(all_wells)} well(s)" if all_wells
        else ""
    )
    status = (
        f"Loaded {total_rows:,} samples × {len(numeric_cols)} curves "
        f"from {csv_path.name}{well_part}  "
        f"[{float(df[depth_col].min()):.1f} – {float(df[depth_col].max()):.1f} m]"
    )
    if dropped_unlabelled:
        status += f"  ({dropped_unlabelled} unlabelled rows dropped)"
    return df, meta, status


# ---------------------------------------------------------------------------
# Public API  – LAS   (unchanged except exclude_cols threaded through helpers)
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

    df, meta = _read_las(las_path)
    if df is None:
        return None, {}, f"Could not parse LAS file: {las_path.name}"

    depth_col = _find_depth_column(df)
    if depth_col is None:
        return None, meta, "No depth column (DEPTH / DEPT / MD) found in LAS."

    df[depth_col] = pd.to_numeric(df[depth_col], errors="coerce")
    df = df.dropna(subset=[depth_col]).sort_values(depth_col).reset_index(drop=True)

    if top_depth >= 0:
        df = df[df[depth_col] >= top_depth]
    if base_depth > top_depth >= 0:
        df = df[df[depth_col] <= base_depth]
    df = df.reset_index(drop=True)

    if df.empty:
        return None, meta, "No data rows remain after depth clipping."

    if sampling_m > 0:
        df = _resample_log(df, depth_col, sampling_m)

    reserved = {depth_col}
    df = _handle_nulls(df, strategy=null_strategy, depth_col=depth_col,
                       exclude_cols=reserved)

    if despike:
        df = _despike(df, depth_col, exclude_cols=reserved)

    if normalize_by_zone and zone_column and zone_column in df.columns:
        df = _normalize_by_zone(df, zone_column, depth_col, exclude_cols=reserved)

    numeric_cols = [
        c for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c]) and c != depth_col
    ]
    total_rows = len(df)
    completeness = {
        col: round(100.0 * df[col].notna().mean(), 1) for col in numeric_cols
    }
    null_clusters = _count_null_clusters(df, numeric_cols)
    spike_count   = _count_spikes(df, numeric_cols) if not despike else 0

    meta.update(
        {
            "source_file"   : las_path.name,
            "file_type"     : "las",
            "depth_col"     : depth_col,
            "depth_range"   : (float(df[depth_col].min()), float(df[depth_col].max())),
            "total_rows"    : total_rows,
            "numeric_curves": numeric_cols,
            "completeness"  : completeness,
            "null_clusters" : null_clusters,
            "spike_count"   : spike_count,
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


# ---------------------------------------------------------------------------
# Shared public helpers
# ---------------------------------------------------------------------------

def build_qc_report(df: pd.DataFrame, metadata: Dict[str, Any]) -> str:
    """Return a plain-text QC summary suitable for displaying in txtQcNotes."""
    fname = metadata.get("source_file", metadata.get("las_file", "unknown"))
    ftype = metadata.get("file_type", "las").upper()

    lines = [f"QC Report ({ftype}) — {fname}"]
    lines.append("=" * 60)
    lines.append(f"Depth range   : {metadata.get('depth_range', ('?', '?'))}")
    lines.append(f"Total rows    : {metadata.get('total_rows', '?'):,}")
    lines.append(f"Null clusters : {metadata.get('null_clusters', '?')}")
    lines.append(f"Spikes flagged: {metadata.get('spike_count', '?')}")

    # CSV-specific sections
    if ftype == "CSV":
        lbl  = metadata.get("label_column")
        well = metadata.get("well_column")
        form = metadata.get("formation_column")
        wells = metadata.get("all_wells", [])

        if lbl:
            lines.append(f"Label column  : {lbl}")
        if well:
            lines.append(f"Well column   : {well}  ({len(wells)} wells)")
            if wells:
                lines.append("  " + ", ".join(str(w) for w in wells))
        if form:
            lines.append(f"Zone column   : {form}")

        facies_dist = metadata.get("facies_distribution", {})
        if facies_dist:
            lines.append("")
            lines.append("Facies distribution:")
            for cls, cnt in sorted(facies_dist.items()):
                bar = "█" * int(40 * cnt / max(facies_dist.values()))
                lines.append(f"  Facies {str(cls):<4}  {cnt:>5}  {bar}")

        dropped = metadata.get("dropped_unlabelled", 0)
        if dropped:
            lines.append(f"\n  [{dropped} unlabelled rows dropped]")

    lines.append("")
    lines.append("Curve completeness:")
    for curve, pct in metadata.get("completeness", {}).items():
        bar = "█" * int(pct / 5)
        lines.append(f"  {curve:<14} {pct:5.1f}%  {bar}")

    return "\n".join(lines)


def get_inventory_rows(metadata: Dict[str, Any]) -> list[tuple[str, str, str]]:
    """Return [(log_name, unit, status), …] for populating tblInputLogs."""
    standard_units = {
        "GR"         : "API",     "RHOB"      : "g/cc",
        "NPHI"       : "v/v",     "DT"        : "us/ft",
        "ILD"        : "ohm.m",   "ILD_LOG10" : "log(ohm.m)",
        "PEF"        : "barn/e",  "PE"        : "barn/e",
        "CALI"       : "in",      "SP"        : "mV",
        "RT"         : "ohm.m",   "LLD"       : "ohm.m",
        "LLS"        : "ohm.m",   "DELTAPHI"  : "v/v",
        "PHIND"      : "v/v",     "PHID"      : "v/v",
        "VSH"        : "v/v",     "NM_M"      : "flag",
        "RELPOS"     : "frac",    "BULK DENSITY": "g/cc",
    }
    optional_curves = {"PEF", "PE", "CALI", "SP"}

    # For CSV loads, mark derived / filled columns as "Derived"
    flag_cols = set(c.upper() for c in metadata.get("flag_columns", []))

    rows = []
    for curve in metadata.get("numeric_curves", []):
        unit   = standard_units.get(curve.upper().replace(" ", "_"), "")
        if not unit:
            unit = standard_units.get(curve.upper(), "")
        if curve.upper() in flag_cols:
            status = "Derived"
        elif curve.upper() in optional_curves:
            status = "Optional"
        else:
            status = "Loaded"
        rows.append((curve, unit, status))

    # Append label column entry so the UI can display it
    lbl_col = metadata.get("label_column")
    if lbl_col:
        rows.append((lbl_col, "class", "Label"))

    return rows


def get_well_list(metadata: Dict[str, Any]) -> list[str]:
    """Return the list of well names found in a multi-well CSV.

    Returns an empty list for LAS files or single-well CSVs.
    """
    return list(metadata.get("all_wells", []))


# ---------------------------------------------------------------------------
# Internal helpers  – CSV reader
# ---------------------------------------------------------------------------

def _read_csv(path: Path, separator: str = ",") -> tuple[Optional[pd.DataFrame], dict]:
    """Read a delimited file into a raw DataFrame, preserving all columns."""
    try:
        # Try common separators if the given one yields only 1 column
        for sep in (separator, ",", "\t", ";"):
            df = pd.read_csv(path, sep=sep, dtype=str, encoding="utf-8",
                             on_bad_lines="skip")
            if len(df.columns) > 2:
                break
        meta: dict = {"well_name": ""}
        return df, meta
    except Exception as exc:
        return None, {"parse_error": str(exc)}


def _detect_label_column(df: pd.DataFrame) -> Optional[str]:
    """Return the first column whose upper-cased name matches a label candidate."""
    for col in df.columns:
        if col.upper().replace(" ", "_") in _LABEL_CANDIDATES or col.upper() in _LABEL_CANDIDATES:
            return col
    return None


def _detect_well_column(df: pd.DataFrame) -> Optional[str]:
    for col in df.columns:
        if col.upper().replace(" ", "_") in _WELL_CANDIDATES or col.upper() in _WELL_CANDIDATES:
            return col
    return None


def _detect_formation_column(df: pd.DataFrame) -> Optional[str]:
    for col in df.columns:
        if col.upper().replace(" ", "_") in _FORMATION_CANDIDATES or col.upper() in _FORMATION_CANDIDATES:
            return col
    return None


def _detect_flag_columns(df: pd.DataFrame) -> list[str]:
    """Return columns that are categorical flags / fill-status indicators."""
    found = []
    for col in df.columns:
        norm = col.upper().replace(" ", "_")
        if norm in _FLAG_CANDIDATES:
            found.append(col)
            continue
        # Also catch columns that contain only string values (non-numeric)
        sample = df[col].dropna().head(50)
        if len(sample) == 0:
            continue
        numeric_rate = pd.to_numeric(sample, errors="coerce").notna().mean()
        if numeric_rate < 0.05:  # >95 % non-numeric → likely a string flag column
            found.append(col)
    return found


# ---------------------------------------------------------------------------
# Internal helpers  – LAS reader
# ---------------------------------------------------------------------------

def _read_las(path: Path) -> tuple[Optional[pd.DataFrame], dict]:
    """Try lasio, then fall back to a raw text parse."""
    try:
        import lasio
        las  = lasio.read(str(path))
        df   = las.df().reset_index()
        meta = {"well_name": las.well.WELL.value if hasattr(las.well, "WELL") else ""}
        return df, meta
    except Exception:
        pass

    try:
        lines = path.read_text(errors="replace").splitlines()
        header_idx = next(
            (i for i, l in enumerate(lines) if l.strip().startswith("~A")), None
        )
        if header_idx is None:
            return None, {}
        col_line = lines[header_idx + 1] if header_idx + 1 < len(lines) else ""
        cols = col_line.split() or ["DEPTH"]
        raw  = [l for l in lines[header_idx + 2:]
                if l.strip() and not l.strip().startswith("#")]
        rows = [r.split() for r in raw if r.strip()]
        df   = pd.DataFrame(
            rows,
            columns=cols[:max(len(r) for r in rows)] if rows else cols,
        )
        for c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df, {}
    except Exception:
        return None, {}


# ---------------------------------------------------------------------------
# Internal helpers  – shared processing
# ---------------------------------------------------------------------------

def _find_depth_column(df: pd.DataFrame) -> Optional[str]:
    candidates = {"DEPTH", "DEPT", "MD", "MEASUREDDEPTH", "DEPTH_M"}
    for c in df.columns:
        if str(c).upper().replace(" ", "") in candidates:
            return c
    for c in df.columns:
        norm = str(c).upper().replace(" ", "")
        if "DEPTH" in norm or "DEPT" in norm:
            return c
    return None


def _resample_log(df: pd.DataFrame, depth_col: str, step: float) -> pd.DataFrame:
    """Linear re-sample to a regular *step* depth spacing."""
    d_min = float(df[depth_col].min())
    d_max = float(df[depth_col].max())
    new_depths = np.arange(d_min, d_max + step, step)
    df_out = pd.DataFrame({depth_col: new_depths})
    numeric_cols = [
        c for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c]) and c != depth_col
    ]
    df = df.sort_values(depth_col)
    for col in numeric_cols:
        df_out[col] = np.interp(
            new_depths,
            df[depth_col].to_numpy(dtype=float),
            df[col].ffill().bfill().to_numpy(dtype=float),
        )
    for col in [c for c in df.columns if c not in numeric_cols and c != depth_col]:
        df_out[col] = np.nan
    return df_out


def _handle_nulls(
    df: pd.DataFrame,
    strategy: str,
    depth_col: str,
    exclude_cols: set[str] | None = None,
) -> pd.DataFrame:
    exclude_cols = exclude_cols or {depth_col}
    numeric_cols = [
        c for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c])
        and c not in exclude_cols
    ]
    if strategy == "interpolate":
        df[numeric_cols] = df[numeric_cols].interpolate(limit_direction="both")
    elif strategy == "median_fill":
        for col in numeric_cols:
            df[col] = df[col].fillna(df[col].median())
    elif strategy == "drop":
        df = df.dropna(subset=numeric_cols).reset_index(drop=True)
    return df


def _despike(
    df: pd.DataFrame,
    depth_col: str,
    window: int = 5,
    threshold: float = 3.0,
    exclude_cols: set[str] | None = None,
) -> pd.DataFrame:
    """Median-based despike: replace values deviating > *threshold* × MAD."""
    exclude_cols = exclude_cols or {depth_col}
    numeric_cols = [
        c for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c]) and c not in exclude_cols
    ]
    for col in numeric_cols:
        s = df[col].copy()
        rolling_med = s.rolling(window, center=True, min_periods=1).median()
        diff = (s - rolling_med).abs()
        mad  = diff.rolling(window, center=True, min_periods=1).median()
        mask = diff > threshold * (mad + 1e-9)
        df[col] = s.where(~mask, rolling_med)
    return df


def _normalize_by_zone(
    df: pd.DataFrame,
    zone_col: str,
    depth_col: str,
    exclude_cols: set[str] | None = None,
) -> pd.DataFrame:
    exclude_cols = (exclude_cols or {depth_col}) | {depth_col, zone_col}
    numeric_cols = [
        c for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c]) and c not in exclude_cols
    ]
    for zone, grp in df.groupby(zone_col):
        idx = grp.index
        for col in numeric_cols:
            mn = df.loc[idx, col].min()
            mx = df.loc[idx, col].max()
            if mx - mn > 1e-9:
                df.loc[idx, col] = (df.loc[idx, col] - mn) / (mx - mn)
    return df


def _count_null_clusters(df: pd.DataFrame, numeric_cols: list[str]) -> int:
    total = 0
    for col in numeric_cols:
        in_run = False
        for v in df[col].isna():
            if v and not in_run:
                total += 1
                in_run = True
            elif not v:
                in_run = False
    return total


def _count_spikes(
    df: pd.DataFrame,
    numeric_cols: list[str],
    window: int = 5,
    threshold: float = 3.0,
) -> int:
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
    """Return [{zone, top, base, rows}, …] for tblZoneSummary."""
    if zone_col and zone_col in df.columns:
        rows = []
        for zone, grp in df.groupby(zone_col):
            rows.append(
                {
                    "zone" : str(zone),
                    "top"  : float(grp[depth_col].min()),
                    "base" : float(grp[depth_col].max()),
                    "rows" : len(grp),
                }
            )
        return rows
    return [
        {
            "zone" : "Full Log",
            "top"  : float(df[depth_col].min()),
            "base" : float(df[depth_col].max()),
            "rows" : len(df),
        }
    ]