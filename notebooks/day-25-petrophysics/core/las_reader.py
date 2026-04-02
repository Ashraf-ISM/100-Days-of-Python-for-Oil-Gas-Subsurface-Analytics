"""
core/las_reader.py
==================
Handles import of LAS 2.0 / 3.0, CSV, and Excel files into WellData objects.
"""

from __future__ import annotations
import os
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Tuple, Dict

from core.data_model import WellData, CurveData


NULL_VALUES = (-9999.25, -9999, -999.25, -999, 1e30, -1e30)


def _replace_nulls(arr: np.ndarray) -> np.ndarray:
    """Replace common null sentinel values with NaN."""
    result = arr.astype(float)
    for nv in NULL_VALUES:
        result[np.isclose(result, nv, rtol=1e-4)] = np.nan
    return result


def load_las(filepath: str,
             replace_nulls: bool = True,
             depth_unit: str = "m",
             depth_type: str = "MD") -> Tuple[WellData, str]:
    """
    Read a LAS 2.0 / 3.0 file.
    Returns (WellData, log_message).
    Requires:  pip install lasio
    """
    try:
        import lasio
    except ImportError:
        return _dummy_well(filepath), "ERROR: lasio not installed. Run: pip install lasio"

    log_lines = []
    try:
        las = lasio.read(filepath)
    except Exception as exc:
        return _dummy_well(filepath), f"ERROR reading LAS: {exc}"

    well_name = las.well.WELL.value or Path(filepath).stem
    w = WellData(name=well_name, source_file=filepath,
                 depth_unit=depth_unit, depth_type=depth_type)

    # ── header ────────────────────────────────────────────────────────────────
    for item in las.well:
        w.header[item.mnemonic] = str(item.value)
    for item in las.params:
        w.header[f"P:{item.mnemonic}"] = str(item.value)

    # ── depth index ───────────────────────────────────────────────────────────
    depth = las.index
    if replace_nulls:
        depth = _replace_nulls(depth)
    w.depth = depth

    # ── curves ────────────────────────────────────────────────────────────────
    for curve in las.curves:
        if curve.mnemonic.upper() in ("DEPT", "DEPTH", "MD", "TVD"):
            continue
        data = curve.data.astype(float)
        if replace_nulls:
            data = _replace_nulls(data)
        cd = CurveData(
            mnemonic=curve.mnemonic,
            alias=curve.mnemonic,
            unit=curve.unit or "",
            data=data,
            description=curve.descr or "",
        )
        w.curves[cd.alias] = cd
        log_lines.append(f"  Loaded: {curve.mnemonic} [{curve.unit}]  "
                         f"min={cd.min:.3g}  max={cd.max:.3g}")

    log_msg = (f"Loaded LAS: {well_name} | "
               f"Depth {w.depth_min:.1f}–{w.depth_max:.1f} {depth_unit} | "
               f"{len(w.curves)} curves\n" + "\n".join(log_lines))
    return w, log_msg


def load_csv(filepath: str,
             depth_col: str = "",
             replace_nulls: bool = True,
             depth_unit: str = "m",
             depth_type: str = "MD") -> Tuple[WellData, str]:
    """Read a CSV or Excel file into WellData."""
    ext = Path(filepath).suffix.lower()
    try:
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(filepath)
        else:
            df = pd.read_csv(filepath)
    except Exception as exc:
        return _dummy_well(filepath), f"ERROR reading CSV/Excel: {exc}"

    # Detect depth column
    if not depth_col:
        for candidate in ("DEPTH", "DEPT", "MD", "TVD", "Depth", "depth"):
            if candidate in df.columns:
                depth_col = candidate
                break
    if not depth_col:
        depth_col = df.columns[0]

    well_name = Path(filepath).stem
    w = WellData(name=well_name, source_file=filepath,
                 depth_unit=depth_unit, depth_type=depth_type)
    w.header["source"] = filepath

    depth = df[depth_col].values.astype(float)
    if replace_nulls:
        depth = _replace_nulls(depth)
    w.depth = depth

    for col in df.columns:
        if col == depth_col:
            continue
        data = df[col].values.astype(float, errors="ignore")
        if data.dtype != float:
            continue  # skip non-numeric columns
        if replace_nulls:
            data = _replace_nulls(data)
        cd = CurveData(mnemonic=col, alias=col, data=data)
        w.curves[col] = cd

    log_msg = (f"Loaded CSV: {well_name} | "
               f"{len(w.depth)} samples | {len(w.curves)} curves")
    return w, log_msg


def _dummy_well(filepath: str) -> WellData:
    """Return a minimal WellData with synthetic test data so the UI still works."""
    depth = np.arange(2800, 3100, 0.1)
    n = len(depth)
    rng = np.random.default_rng(42)

    w = WellData(name=Path(filepath).stem or "Demo_Well",
                 source_file=filepath)
    w.depth = depth

    curves = {
        "GR":   (rng.uniform(20, 120, n), "GAPI"),
        "RT":   (10 ** rng.uniform(0.5, 2.5, n), "ohm.m"),
        "RHOB": (rng.uniform(2.1, 2.65, n), "g/cc"),
        "NPHI": (rng.uniform(0.05, 0.35, n), "v/v"),
        "DT":   (rng.uniform(50, 110, n), "us/ft"),
    }
    for name, (data, unit) in curves.items():
        w.curves[name] = CurveData(mnemonic=name, alias=name, unit=unit, data=data)
    return w


def generate_demo_well(name: str = "Demo_Well") -> WellData:
    """Create a synthetic well for testing / demo purposes."""
    return _dummy_well(name)