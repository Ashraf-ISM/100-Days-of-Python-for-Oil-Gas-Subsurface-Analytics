"""
calculations/vshale.py
======================
Shale-volume (Vshale / Vclay) algorithms.

All functions operate on numpy arrays and return arrays of the same shape.
NaN propagates naturally through numpy maths.
"""

from __future__ import annotations
import numpy as np


# ── Linear / GR-based ────────────────────────────────────────────────────────

def vshale_linear(gr: np.ndarray, gr_sand: float, gr_shale: float) -> np.ndarray:
    """Linear GR index (IGR).
    Vsh = (GR - GR_sand) / (GR_shale - GR_sand)
    """
    denom = gr_shale - gr_sand
    if abs(denom) < 1e-9:
        return np.full_like(gr, np.nan, dtype=float)
    igr = (gr - gr_sand) / denom
    return np.clip(igr, 0.0, 1.0)


def vshale_larionov_old(igr: np.ndarray) -> np.ndarray:
    """Larionov (1969) correction for Tertiary rocks.
    Vsh = 0.083 * (2^(3.7 * IGR) − 1)
    """
    return np.clip(0.083 * (2 ** (3.7 * igr) - 1.0), 0.0, 1.0)


def vshale_larionov_tertiary(igr: np.ndarray) -> np.ndarray:
    """Larionov (1969) for older consolidated rocks."""
    return np.clip(0.33 * (2 ** (2.0 * igr) - 1.0), 0.0, 1.0)


def vshale_steiber(igr: np.ndarray) -> np.ndarray:
    """Steiber (1970): Vsh = IGR / (3 − 2*IGR)"""
    denom = 3.0 - 2.0 * igr
    with np.errstate(invalid="ignore", divide="ignore"):
        v = igr / denom
    return np.clip(v, 0.0, 1.0)


def vshale_clavier(igr: np.ndarray) -> np.ndarray:
    """Clavier (1971): Vsh = 1.7 − sqrt(3.38 − (IGR + 0.7)^2)"""
    inner = 3.38 - (igr + 0.7) ** 2
    with np.errstate(invalid="ignore"):
        v = 1.7 - np.sqrt(np.clip(inner, 0.0, None))
    return np.clip(v, 0.0, 1.0)


# ── SP-based ─────────────────────────────────────────────────────────────────

def vshale_sp(sp: np.ndarray, sp_sand: float, sp_shale: float) -> np.ndarray:
    """SP-based Vshale."""
    denom = sp_shale - sp_sand
    if abs(denom) < 1e-9:
        return np.full_like(sp, np.nan, dtype=float)
    igr = (sp - sp_sand) / denom
    return np.clip(igr, 0.0, 1.0)


# ── Dispatcher ───────────────────────────────────────────────────────────────

def calc_vshale(gr: np.ndarray,
                gr_sand: float = 20.0,
                gr_shale: float = 120.0,
                method: str = "Linear") -> np.ndarray:
    """
    Main entry point.
    method: "Linear" | "Larionov Old" | "Larionov Tertiary" | "Steiber" | "Clavier"
    """
    igr = vshale_linear(gr, gr_sand, gr_shale)
    dispatch = {
        "Linear":              igr,
        "Larionov Old":        vshale_larionov_old(igr),
        "Larionov Tertiary":   vshale_larionov_tertiary(igr),
        "Steiber":             vshale_steiber(igr),
        "Clavier":             vshale_clavier(igr),
    }
    return dispatch.get(method, igr)