"""Unified well data loader (single file, auto-detect)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from core.data_model import Well

try:
    from core import las_reader  # type: ignore
except Exception:  # noqa: BLE001
    las_reader = None


def _read_csv_basic(path: str):
    try:
        import pandas as pd  # type: ignore
    except Exception:  # noqa: BLE001
        return None
    return pd.read_csv(path)


def load_well(path: str, *, replace_nulls: bool = True, depth_unit: str = "m", depth_type: str = "MD") -> tuple[Well, str]:
    ext = Path(path).suffix.lower()
    name = Path(path).stem

    if las_reader and ext in {".las", ".laz", ".dlis", ".dl"}:
        return las_reader.load_las(path, replace_nulls=replace_nulls, depth_unit=depth_unit, depth_type=depth_type)

    if ext in {".csv", ".txt", ".dat", ".asc"}:
        if las_reader:
            return las_reader.load_csv(path, replace_nulls=replace_nulls, depth_unit=depth_unit, depth_type=depth_type)
        df = _read_csv_basic(path)
        return Well(name=name, data=df), f"Loaded CSV: {name}"

    # Fallback empty well
    return Well(name=name), f"Loaded (empty) well: {name}"
