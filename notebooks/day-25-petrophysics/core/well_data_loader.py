"""Unified well data loader (single file, auto-detect)."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable

# pyrefly: ignore [missing-import]
from core.data_model import Well


FutureFormatHandler = Callable[[str], tuple[Well, str] | None]


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


def _read_tabular(path: str):
    try:
        import pandas as pd  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("pandas is required to read tabular files") from exc

    ext = Path(path).suffix.lower()

    if ext == ".csv":
        return pd.read_csv(path)

    if ext in {".xlsx", ".xls"}:
        return pd.read_excel(path)

    if ext in {".txt", ".asc", ".ascii", ".dat"}:
        # Try delimiter sniffing first, then whitespace-delimited fallback.
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                sample = f.read(4096)
            dialect = csv.Sniffer().sniff(sample)
            return pd.read_csv(path, sep=dialect.delimiter)
        except Exception:
            return pd.read_csv(path, delim_whitespace=True)

    return None


def _load_with_custom_handler(path: str, custom_handler: FutureFormatHandler | None):
    """Extension hook for unsupported formats.

    Return `(Well, message)` when handled, or `None` to fallback to default behavior.
    """
    if custom_handler is None:
        return None
    return custom_handler(path)


def load_well(
    path: str,
    *,
    replace_nulls: bool = True,
    depth_unit: str = "m",
    depth_type: str = "MD",
    custom_handler: FutureFormatHandler | None = None,
) -> tuple[Well, str]:
    _ = (replace_nulls, depth_unit, depth_type)
    ext = Path(path).suffix.lower()
    name = Path(path).stem

    if ext in {".las", ".laz", ".dlis", ".dl"}:
        las_result = _read_las(path)
        if las_result is not None:
            return las_result

    if ext in {".csv", ".xlsx", ".xls", ".txt", ".dat", ".asc", ".ascii"}:
        df = _read_tabular(path)
        if df is not None:
            return Well(name=name, data=df), f"Loaded tabular file: {Path(path).name}"

    custom_result = _load_with_custom_handler(path, custom_handler)
    if custom_result is not None:
        return custom_result

    return Well(name=name), f"Loaded (empty) well: {name}"
