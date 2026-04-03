"""Unified well data loader.

One entry point for LAS/CSV/Excel/ASCII/etc. This keeps the UI clean and
avoids having separate loader files per format.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from core import las_reader


class WellDataLoader:
    """Smart loader that auto-detects by extension and falls back gracefully."""

    def load(self, path: str, *, replace_nulls: bool = True, depth_unit: str = "m", depth_type: str = "MD"):
        ext = Path(path).suffix.lower()

        # Keep all formats in a single entry point.
        if ext in {".las", ".laz", ".dlis", ".dl"}:
            return las_reader.load_las(
                path,
                replace_nulls=replace_nulls,
                depth_unit=depth_unit,
                depth_type=depth_type,
            )
        if ext in {".csv", ".txt", ".dat", ".asc"}:
            return las_reader.load_csv(
                path,
                replace_nulls=replace_nulls,
                depth_unit=depth_unit,
                depth_type=depth_type,
            )

        # Generic fallback: try CSV-style parsing first.
        return las_reader.load_csv(
            path,
            replace_nulls=replace_nulls,
            depth_unit=depth_unit,
            depth_type=depth_type,
        )


_loader = WellDataLoader()


def load_well(path: str, *, replace_nulls: bool = True, depth_unit: str = "m", depth_type: str = "MD") -> Any:
    return _loader.load(
        path,
        replace_nulls=replace_nulls,
        depth_unit=depth_unit,
        depth_type=depth_type,
    )
