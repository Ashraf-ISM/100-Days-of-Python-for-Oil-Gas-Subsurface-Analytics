"""Unified well data loader (single file, auto-detect)."""
from __future__ import annotations

from pathlib import Path

from core.data_model import Well


def _read_las(path: str):
    try:
        import lasio  # type: ignore 
    except Exception:  # noqa: BLE001 
        return None
    las = lasio.read(path)
    df = las.df().reset_index()
    df.rename(columns={df.columns[0]: "DEPTH"}, inplace=True)

    header = {
        "WELL": {item.mnemonic: {"unit": item.unit, "value": item.value, "desc": item.descr} for item in las.well}, 
        "PARAM": {item.mnemonic: {"unit": item.unit, "value": item.value, "desc": item.descr} for item in las.params}, 
    }
    log_info = { 
        curve.mnemonic: {
            "unit": curve.unit,
            "type": getattr(curve, "curve_type", "") or "",
            "mnemonic": curve.mnemonic,
            "desc": curve.descr,
        }
        for curve in las.curves
    }
    return Well(name=Path(path).stem, header=header, log_info=log_info, data=df), f"Loaded LAS: {Path(path).name}"


def _read_csv_basic(path: str):
    try:
        import pandas as pd  # type: ignore
    except Exception:  # noqa: BLE001
        return None
    return pd.read_csv(path)


def load_well(path: str, *, replace_nulls: bool = True, depth_unit: str = "m", depth_type: str = "MD") -> tuple[Well, str]:
    _ = (replace_nulls, depth_unit, depth_type)
    ext = Path(path).suffix.lower()
    name = Path(path).stem

    if ext in {".las", ".laz", ".dlis", ".dl"}:
        las_result = _read_las(path)
        if las_result is not None:
            return las_result

    if ext in {".csv", ".txt", ".dat", ".asc"}:
        df = _read_csv_basic(path)
        return Well(name=name, data=df), f"Loaded CSV: {name}"

    return Well(name=name), f"Loaded (empty) well: {name}"
