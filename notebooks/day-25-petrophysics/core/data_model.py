"""
core/data_model.py
==================
Central data structures for PetroSight Pro.
All well data and curve data live here; the rest of the app
imports these objects instead of raw dicts/arrays.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np


@dataclass
class CurveData:
    """A single log curve (one column in a LAS/DLIS file)."""
    mnemonic: str                        # Original mnemonic (e.g. "GR")
    alias: str = ""                      # User-assigned standard name (e.g. "GAMMA_RAY")
    unit: str = ""                       # Physical unit string
    data: np.ndarray = field(default_factory=lambda: np.array([]))
    curve_type: str = "raw"              # "raw" | "calculated" | "core"
    description: str = ""

    def __post_init__(self):
        if not self.alias:
            self.alias = self.mnemonic

    # ── convenience ──────────────────────────────────────────────────────────
    @property
    def min(self) -> float:
        valid = self.data[np.isfinite(self.data)]
        return float(valid.min()) if len(valid) else float("nan")

    @property
    def max(self) -> float:
        valid = self.data[np.isfinite(self.data)]
        return float(valid.max()) if len(valid) else float("nan")

    @property
    def mean(self) -> float:
        valid = self.data[np.isfinite(self.data)]
        return float(valid.mean()) if len(valid) else float("nan")

    @property
    def std(self) -> float:
        valid = self.data[np.isfinite(self.data)]
        return float(valid.std()) if len(valid) else float("nan")

    @property
    def null_pct(self) -> float:
        if len(self.data) == 0:
            return 0.0
        return 100.0 * np.sum(~np.isfinite(self.data)) / len(self.data)

    def to_dict(self) -> dict:
        return {
            "mnemonic": self.mnemonic,
            "alias": self.alias,
            "unit": self.unit,
            "curve_type": self.curve_type,
            "description": self.description,
            "data": self.data.tolist(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CurveData":
        c = cls(
            mnemonic=d["mnemonic"],
            alias=d.get("alias", d["mnemonic"]),
            unit=d.get("unit", ""),
            curve_type=d.get("curve_type", "raw"),
            description=d.get("description", ""),
        )
        c.data = np.array(d.get("data", []), dtype=float)
        return c


@dataclass
class FormationTop:
    """A depth pick / formation boundary."""
    name: str
    depth: float          # Measured depth (m or ft)
    color: str = "#FF5722"
    comment: str = ""


@dataclass
class WellData:
    """Container for one well (all curves + metadata)."""
    name: str
    depth: np.ndarray = field(default_factory=lambda: np.array([]))
    curves: Dict[str, CurveData] = field(default_factory=dict)
    header: Dict[str, str] = field(default_factory=dict)
    formation_tops: List[FormationTop] = field(default_factory=list)
    depth_unit: str = "m"               # "m" | "ft"
    depth_type: str = "MD"              # "MD" | "TVD" | "TVDSS"
    source_file: str = ""

    # ── curve access helpers ─────────────────────────────────────────────────
    def add_curve(self, curve: CurveData):
        """Add or overwrite a curve keyed by its alias."""
        self.curves[curve.alias] = curve

    def get_curve(self, name: str) -> Optional[CurveData]:
        """Retrieve by alias or original mnemonic."""
        if name in self.curves:
            return self.curves[name]
        for c in self.curves.values():
            if c.mnemonic == name:
                return c
        return None

    def curve_names(self) -> List[str]:
        return list(self.curves.keys())

    def add_calculated_curve(self, mnemonic: str, unit: str,
                              data: np.ndarray, description: str = ""):
        curve = CurveData(
            mnemonic=mnemonic,
            alias=mnemonic,
            unit=unit,
            data=data.copy(),
            curve_type="calculated",
            description=description,
        )
        self.curves[mnemonic] = curve

    # ── depth helpers ────────────────────────────────────────────────────────
    @property
    def depth_min(self) -> float:
        return float(self.depth.min()) if len(self.depth) else 0.0

    @property
    def depth_max(self) -> float:
        return float(self.depth.max()) if len(self.depth) else 0.0

    @property
    def step(self) -> float:
        if len(self.depth) < 2:
            return 0.1
        diffs = np.diff(self.depth)
        return float(np.median(diffs))

    # ── serialisation ────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "depth": self.depth.tolist(),
            "curves": {k: v.to_dict() for k, v in self.curves.items()},
            "header": self.header,
            "formation_tops": [
                {"name": t.name, "depth": t.depth,
                 "color": t.color, "comment": t.comment}
                for t in self.formation_tops
            ],
            "depth_unit": self.depth_unit,
            "depth_type": self.depth_type,
            "source_file": self.source_file,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WellData":
        w = cls(name=d["name"])
        w.depth = np.array(d.get("depth", []), dtype=float)
        w.curves = {k: CurveData.from_dict(v) for k, v in d.get("curves", {}).items()}
        w.header = d.get("header", {})
        w.depth_unit = d.get("depth_unit", "m")
        w.depth_type = d.get("depth_type", "MD")
        w.source_file = d.get("source_file", "")
        for t in d.get("formation_tops", []):
            w.formation_tops.append(
                FormationTop(t["name"], t["depth"], t.get("color", "#FF5722"), t.get("comment", ""))
            )
        return w


@dataclass
class Project:
    """Top-level project container (holds all wells)."""
    name: str = "Untitled Project"
    wells: Dict[str, WellData] = field(default_factory=dict)
    notes: str = ""

    def add_well(self, well: WellData):
        self.wells[well.name] = well

    def remove_well(self, name: str):
        self.wells.pop(name, None)

    def well_names(self) -> List[str]:
        return list(self.wells.keys())

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "wells": {k: v.to_dict() for k, v in self.wells.items()},
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Project":
        p = cls(name=d.get("name", "Untitled Project"), notes=d.get("notes", ""))
        for k, v in d.get("wells", {}).items():
            p.wells[k] = WellData.from_dict(v)
        return p