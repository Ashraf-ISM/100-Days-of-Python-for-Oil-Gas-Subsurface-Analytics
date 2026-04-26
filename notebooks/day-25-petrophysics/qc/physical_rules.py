"""
physical_rules.py
=================
Tool physics registry for professional spike detection.

Maps petrophysical curve mnemonics to their known physical operating ranges.
Resistivity curves use a log10 transform because of their multi-decade dynamic
range — comparing raw Ohm-m values would make short-circuit statistics useless.

Usage
-----
    from qc.physical_rules import get_limits, PhysicalLimit

    limit = get_limits("GR")          # returns PhysicalLimit or None
    if limit:
        violated = limit.is_violated(value)
        transformed = limit.transform(value)   # log10 for RT etc.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PhysicalLimit:
    """Physical operating range for a petrophysical measurement tool.

    Attributes
    ----------
    curve_type : str
        Human-readable curve category (e.g. "Gamma Ray", "Bulk Density").
    min_val : float
        Minimum physically plausible value (in native or transformed units).
    max_val : float
        Maximum physically plausible value (in native or transformed units).
    unit : str
        Unit string for display purposes.
    transform : str
        ``"none"`` for linear scales; ``"log10"`` for resistivity logs.
    soft_min : float | None
        Softer inner bound (values outside this range are suspicious but not
        impossible).  Used for confidence scoring rather than hard rejection.
    soft_max : float | None
        Soft upper bound (same semantics as soft_min).
    """
    curve_type: str
    min_val: float
    max_val: float
    unit: str
    transform: str = "none"
    soft_min: Optional[float] = None
    soft_max: Optional[float] = None

    # ── value transform helpers ───────────────────────────────────────────────
    def transform_value(self, value: float) -> Optional[float]:
        """Apply the curve's transform (log10 for resistivity, else identity)."""
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return None
        if self.transform == "log10":
            if value <= 0:
                return None        # unphysical — will be flagged as violated
            return math.log10(value)
        return float(value)

    # ── range checks ─────────────────────────────────────────────────────────
    def is_hard_violated(self, value: float) -> bool:
        """Return True if *value* lies outside the absolute physical range."""
        tv = self.transform_value(value)
        if tv is None:
            return True
        return tv < self.min_val or tv > self.max_val

    def is_soft_violated(self, value: float) -> bool:
        """Return True if *value* lies in the suspicious (soft) band."""
        if self.soft_min is None and self.soft_max is None:
            return False
        tv = self.transform_value(value)
        if tv is None:
            return True
        lo = self.soft_min if self.soft_min is not None else self.min_val
        hi = self.soft_max if self.soft_max is not None else self.max_val
        return tv < lo or tv > hi

    def violation_score(self, value: float) -> float:
        """Return a [0, 1] severity score for physics violation.

        0.0 → within soft range (no violation)
        0.5 → outside soft but inside hard range
        1.0 → outside hard limit (impossible value)
        """
        if self.is_hard_violated(value):
            return 1.0
        if self.is_soft_violated(value):
            return 0.5
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Physical limits registry
# Keys are canonical mnemonics (uppercase, no subscript).
# Matching is done via the fuzzy lookup below.
# ─────────────────────────────────────────────────────────────────────────────

_REGISTRY: dict[str, PhysicalLimit] = {

    # ── Gamma Ray ─────────────────────────────────────────────────────────────
    "GR": PhysicalLimit(
        curve_type="Gamma Ray",
        min_val=0.0,
        max_val=300.0,
        unit="API",
        soft_min=0.0,
        soft_max=200.0,
    ),
    "SGR": PhysicalLimit(
        curve_type="Spectral Gamma Ray (Total)",
        min_val=0.0,
        max_val=300.0,
        unit="API",
        soft_min=0.0,
        soft_max=200.0,
    ),
    "CGR": PhysicalLimit(
        curve_type="Computed Gamma Ray",
        min_val=0.0,
        max_val=300.0,
        unit="API",
        soft_min=0.0,
        soft_max=200.0,
    ),

    # ── Bulk Density ──────────────────────────────────────────────────────────
    "RHOB": PhysicalLimit(
        curve_type="Bulk Density",
        min_val=1.0,
        max_val=3.5,
        unit="g/cc",
        soft_min=1.7,
        soft_max=3.05,
    ),
    "DPHI": PhysicalLimit(
        curve_type="Density Porosity",
        min_val=-0.20,
        max_val=0.70,
        unit="v/v",
        soft_min=-0.05,
        soft_max=0.60,
    ),

    # ── Neutron Porosity ──────────────────────────────────────────────────────
    "NPHI": PhysicalLimit(
        curve_type="Neutron Porosity",
        min_val=-0.15,
        max_val=0.75,
        unit="v/v",
        soft_min=0.00,
        soft_max=0.60,
    ),
    "TNPH": PhysicalLimit(
        curve_type="Thermal Neutron Porosity",
        min_val=-0.15,
        max_val=0.75,
        unit="v/v",
        soft_min=0.00,
        soft_max=0.60,
    ),

    # ── Sonic / Acoustic ──────────────────────────────────────────────────────
    "DT": PhysicalLimit(
        curve_type="Compressional Slowness",
        min_val=38.0,
        max_val=240.0,
        unit="us/ft",
        soft_min=42.0,
        soft_max=200.0,
    ),
    "DTC": PhysicalLimit(
        curve_type="Compressional Slowness",
        min_val=38.0,
        max_val=240.0,
        unit="us/ft",
        soft_min=42.0,
        soft_max=200.0,
    ),
    "DTS": PhysicalLimit(
        curve_type="Shear Slowness",
        min_val=55.0,
        max_val=600.0,
        unit="us/ft",
        soft_min=60.0,
        soft_max=500.0,
    ),
    "DTCO": PhysicalLimit(
        curve_type="Compressional Slowness (DSI)",
        min_val=38.0,
        max_val=240.0,
        unit="us/ft",
        soft_min=42.0,
        soft_max=200.0,
    ),

    # ── Resistivity (log10 transform) ─────────────────────────────────────────
    # min_val / max_val are in log10-Ohm-m space:
    #   0.1 Ohm-m → log10 = -1.0   (absolute minimum)
    #   20,000 Ohm-m → log10 = 4.3 (absolute maximum for any tool)
    "RT": PhysicalLimit(
        curve_type="True Resistivity",
        min_val=-1.0,   # log10(0.1)
        max_val=4.3,    # log10(20000)
        unit="Ohm-m (log10)",
        transform="log10",
        soft_min=-0.7,  # log10(0.2)
        soft_max=4.0,   # log10(10000)
    ),
    "ILD": PhysicalLimit(
        curve_type="Deep Induction Resistivity",
        min_val=-1.0,
        max_val=4.3,
        unit="Ohm-m (log10)",
        transform="log10",
        soft_min=-0.7,
        soft_max=4.0,
    ),
    "ILM": PhysicalLimit(
        curve_type="Medium Induction Resistivity",
        min_val=-1.0,
        max_val=4.3,
        unit="Ohm-m (log10)",
        transform="log10",
        soft_min=-0.7,
        soft_max=4.0,
    ),
    "LLD": PhysicalLimit(
        curve_type="Deep Laterolog Resistivity",
        min_val=-1.0,
        max_val=4.3,
        unit="Ohm-m (log10)",
        transform="log10",
        soft_min=-0.7,
        soft_max=4.0,
    ),
    "LLS": PhysicalLimit(
        curve_type="Shallow Laterolog Resistivity",
        min_val=-1.0,
        max_val=4.3,
        unit="Ohm-m (log10)",
        transform="log10",
        soft_min=-0.7,
        soft_max=4.0,
    ),
    "MSFL": PhysicalLimit(
        curve_type="Microspherically Focused Resistivity",
        min_val=-1.0,
        max_val=4.3,
        unit="Ohm-m (log10)",
        transform="log10",
        soft_min=-0.7,
        soft_max=4.0,
    ),
    "RDEEP": PhysicalLimit(
        curve_type="Deep Resistivity",
        min_val=-1.0,
        max_val=4.3,
        unit="Ohm-m (log10)",
        transform="log10",
        soft_min=-0.7,
        soft_max=4.0,
    ),
    "RMED": PhysicalLimit(
        curve_type="Medium Resistivity",
        min_val=-1.0,
        max_val=4.3,
        unit="Ohm-m (log10)",
        transform="log10",
        soft_min=-0.7,
        soft_max=4.0,
    ),

    # ── Caliper ───────────────────────────────────────────────────────────────
    "CALI": PhysicalLimit(
        curve_type="Caliper",
        min_val=4.0,
        max_val=30.0,
        unit="inches",
        soft_min=5.0,
        soft_max=20.0,
    ),
    "CAL": PhysicalLimit(
        curve_type="Caliper",
        min_val=4.0,
        max_val=30.0,
        unit="inches",
        soft_min=5.0,
        soft_max=20.0,
    ),

    # ── SP ────────────────────────────────────────────────────────────────────
    "SP": PhysicalLimit(
        curve_type="Spontaneous Potential",
        min_val=-200.0,
        max_val=100.0,
        unit="mV",
        soft_min=-160.0,
        soft_max=80.0,
    ),

    # ── Photoelectric Factor ──────────────────────────────────────────────────
    "PE": PhysicalLimit(
        curve_type="Photoelectric Factor",
        min_val=0.0,
        max_val=12.0,
        unit="barns/electron",
        soft_min=1.0,
        soft_max=9.0,
    ),
    "PEF": PhysicalLimit(
        curve_type="Photoelectric Factor",
        min_val=0.0,
        max_val=12.0,
        unit="barns/electron",
        soft_min=1.0,
        soft_max=9.0,
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# Fuzzy lookup helpers
# ─────────────────────────────────────────────────────────────────────────────

def _normalise(name: str) -> str:
    """Strip trailing digits / underscores and uppercase."""
    return name.upper().strip().rstrip("0123456789_")


def get_limits(curve_name: str) -> Optional[PhysicalLimit]:
    """Return the :class:`PhysicalLimit` for *curve_name*, or ``None``.

    Lookup order:
    1. Exact match (uppercase).
    2. Normalised (suffix-stripped) exact match.
    3. Partial / contained-in match against registry keys.
    4. None — no known physics for this curve.
    """
    if not curve_name:
        return None

    upper = curve_name.upper().strip()

    # 1. Exact
    if upper in _REGISTRY:
        return _REGISTRY[upper]

    # 2. Normalised exact
    norm = _normalise(upper)
    if norm in _REGISTRY:
        return _REGISTRY[norm]

    # 3. Partial match — registry key contained in curve name or vice-versa
    for key, limit in _REGISTRY.items():
        if key in upper or upper.startswith(key):
            return limit

    return None


def list_supported_curves() -> list[str]:
    """Return all canonical mnemonic keys in the registry."""
    return sorted(_REGISTRY.keys())
