"""
qc_rules.py
===========
QC rule defaults and curve-specific detection profiles.

Commercial QC systems (Techlog, IP, Geolog) use per-curve tuning rather than
a single global MAD multiplier + window.  This module provides that registry.

Usage
-----
    from qc.qc_rules import get_curve_profile, DEFAULT_RULES

    profile = get_curve_profile("TNPH")
    # {'window': 15, 'mad_multiplier': 4.5, 'max_spike_width': 2, ...}
"""
from __future__ import annotations

from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Per-curve QC profiles
# Keys are canonical uppercase mnemonics.  Fuzzy lookup handles variants like
# "GR_EDITED", "NPHI_1", etc.
# ─────────────────────────────────────────────────────────────────────────────

CURVE_PROFILES: dict[str, dict] = {

    # ── Gamma Ray family ──────────────────────────────────────────────────────
    "GR": {
        "window":          13,
        "mad_multiplier":  4.0,
        "max_spike_width": 2,
        "gradient_limit":  15.0,    # API/sample — large jumps still plausible
        "correction":      "local_median",
    },
    "SGR": {
        "window":          13,
        "mad_multiplier":  4.0,
        "max_spike_width": 2,
        "gradient_limit":  15.0,
        "correction":      "local_median",
    },
    "CGR": {
        "window":          13,
        "mad_multiplier":  4.0,
        "max_spike_width": 2,
        "gradient_limit":  15.0,
        "correction":      "local_median",
    },

    # ── Bulk Density ──────────────────────────────────────────────────────────
    "RHOB": {
        "window":          9,
        "mad_multiplier":  3.5,
        "max_spike_width": 2,
        "gradient_limit":  0.15,    # g/cc per sample
        "correction":      "local_median",
    },
    "DPHI": {
        "window":          9,
        "mad_multiplier":  3.5,
        "max_spike_width": 2,
        "gradient_limit":  0.10,
        "correction":      "local_median",
    },

    # ── Neutron Porosity (most prone to false spikes) ─────────────────────────
    "NPHI": {
        "window":          15,
        "mad_multiplier":  4.5,
        "max_spike_width": 2,
        "gradient_limit":  0.08,    # v/v per sample
        "correction":      "local_median",
    },
    "TNPH": {
        "window":          15,
        "mad_multiplier":  4.5,
        "max_spike_width": 2,
        "gradient_limit":  0.08,
        "correction":      "local_median",
    },

    # ── Sonic / Acoustic ──────────────────────────────────────────────────────
    "DT": {
        "window":          11,
        "mad_multiplier":  4.0,
        "max_spike_width": 2,
        "gradient_limit":  8.0,     # us/ft per sample
        "correction":      "local_median",
    },
    "DTC": {
        "window":          11,
        "mad_multiplier":  4.0,
        "max_spike_width": 2,
        "gradient_limit":  8.0,
        "correction":      "local_median",
    },
    "DTCO": {
        "window":          11,
        "mad_multiplier":  4.0,
        "max_spike_width": 2,
        "gradient_limit":  8.0,
        "correction":      "local_median",
    },
    "DTS": {
        "window":          13,
        "mad_multiplier":  4.0,
        "max_spike_width": 3,
        "gradient_limit":  12.0,
        "correction":      "local_median",
    },

    # ── Resistivity (log-scale dynamic range) ─────────────────────────────────
    "RT": {
        "window":          11,
        "mad_multiplier":  3.0,
        "max_spike_width": 2,
        "gradient_limit":  None,    # handled by log10 transform in physics
        "correction":      "local_median",
    },
    "ILD": {
        "window":          11,
        "mad_multiplier":  3.0,
        "max_spike_width": 2,
        "gradient_limit":  None,
        "correction":      "local_median",
    },
    "ILM": {
        "window":          11,
        "mad_multiplier":  3.0,
        "max_spike_width": 2,
        "gradient_limit":  None,
        "correction":      "local_median",
    },
    "LLD": {
        "window":          11,
        "mad_multiplier":  3.0,
        "max_spike_width": 2,
        "gradient_limit":  None,
        "correction":      "local_median",
    },
    "LLS": {
        "window":          11,
        "mad_multiplier":  3.0,
        "max_spike_width": 2,
        "gradient_limit":  None,
        "correction":      "local_median",
    },
    "MSFL": {
        "window":          11,
        "mad_multiplier":  3.0,
        "max_spike_width": 2,
        "gradient_limit":  None,
        "correction":      "local_median",
    },
    "RDEEP": {
        "window":          11,
        "mad_multiplier":  3.0,
        "max_spike_width": 2,
        "gradient_limit":  None,
        "correction":      "local_median",
    },
    "RMED": {
        "window":          11,
        "mad_multiplier":  3.0,
        "max_spike_width": 2,
        "gradient_limit":  None,
        "correction":      "local_median",
    },

    # ── Caliper ───────────────────────────────────────────────────────────────
    "CALI": {
        "window":          9,
        "mad_multiplier":  3.5,
        "max_spike_width": 3,
        "gradient_limit":  1.5,     # inches/sample
        "correction":      "local_median",
    },
    "CAL": {
        "window":          9,
        "mad_multiplier":  3.5,
        "max_spike_width": 3,
        "gradient_limit":  1.5,
        "correction":      "local_median",
    },

    # ── Spontaneous Potential ─────────────────────────────────────────────────
    "SP": {
        "window":          11,
        "mad_multiplier":  4.0,
        "max_spike_width": 2,
        "gradient_limit":  10.0,    # mV/sample
        "correction":      "local_median",
    },

    # ── Photoelectric Factor ──────────────────────────────────────────────────
    "PE": {
        "window":          11,
        "mad_multiplier":  3.5,
        "max_spike_width": 2,
        "gradient_limit":  1.0,
        "correction":      "local_median",
    },
    "PEF": {
        "window":          11,
        "mad_multiplier":  3.5,
        "max_spike_width": 2,
        "gradient_limit":  1.0,
        "correction":      "local_median",
    },
}

# Sensible fall-back for curves not in the registry
_GENERIC_PROFILE: dict = {
    "window":          11,
    "mad_multiplier":  4.0,
    "max_spike_width": 3,
    "gradient_limit":  None,
    "correction":      "local_median",
}

# ─────────────────────────────────────────────────────────────────────────────
# Fuzzy lookup
# ─────────────────────────────────────────────────────────────────────────────

def _normalise(name: str) -> str:
    """Uppercase and strip trailing digits/underscores (e.g. GR_1 → GR)."""
    return name.upper().strip().rstrip("0123456789_")


def get_curve_profile(curve_name: str) -> dict:
    """Return the QC profile for *curve_name* with fuzzy mnemonic matching.

    Lookup order:
    1. Exact uppercase match.
    2. Suffix-stripped match (``GR_EDITED`` → ``GR``).
    3. Prefix match (``TNPH_CORR`` → ``TNPH``).
    4. Generic fallback profile.

    Returns
    -------
    dict — always a dict (never None).  Caller overrides via **kwargs.
    """
    if not curve_name:
        return _GENERIC_PROFILE.copy()

    upper = curve_name.upper().strip()

    # 1. Exact
    if upper in CURVE_PROFILES:
        return CURVE_PROFILES[upper].copy()

    # 2. Normalised exact (strip trailing digits/underscores)
    norm = _normalise(upper)
    if norm in CURVE_PROFILES:
        return CURVE_PROFILES[norm].copy()

    # 3. Key-contained-in or starts-with
    for key, profile in CURVE_PROFILES.items():
        if upper.startswith(key) or key in upper:
            return profile.copy()

    return _GENERIC_PROFILE.copy()


# ─────────────────────────────────────────────────────────────────────────────
# Legacy flat rules dict — kept for backward-compat with old engine references
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_RULES: dict = {
    "missing_values": {"max_pct": 5.0},
    "spike_detection": {
        # These are the generic fallback values.
        # Prefer get_curve_profile() for per-curve accuracy.
        "mode":                 "Standard",
        "mad_multiplier":       _GENERIC_PROFILE["mad_multiplier"],
        "window":               _GENERIC_PROFILE["window"],
        "max_spike_width":      _GENERIC_PROFILE["max_spike_width"],
        "confidence_threshold": 0.5,
        "cross_log_validation": True,
        "correction":           "local_median",
        # Legacy key kept for any code that still reads it
        "zscore":               4.0,
    },
    "depth_gaps": {"max_gap": 1.0},
}