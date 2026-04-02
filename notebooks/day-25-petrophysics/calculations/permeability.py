"""
calculations/permeability.py
============================
Log-derived permeability models.
"""

from __future__ import annotations
import numpy as np


def perm_timur(phie: np.ndarray, swirr: float = 0.10) -> np.ndarray:
    """Timur (1968):
    K = 0.136 * (PHIE^4.4) / Swirr^2    [mD]
    """
    with np.errstate(invalid="ignore", divide="ignore"):
        k = 0.136 * (phie ** 4.4) / (swirr ** 2)
    return np.clip(k, 0.0, None)


def perm_morris_biggs(phie: np.ndarray, swirr: float = 0.10,
                      c: float = 65.0) -> np.ndarray:
    """Morris & Biggs (1967):
    K = C * (PHIE^3 / Swirr)^2         [mD]
    """
    with np.errstate(invalid="ignore", divide="ignore"):
        k = c * ((phie ** 3) / swirr) ** 2
    return np.clip(k, 0.0, None)


def perm_kozeny_carman(phie: np.ndarray,
                       tau: float = 2.0,
                       Sv: float = 0.02) -> np.ndarray:
    """Kozeny-Carman:
    K = phie^3 / (tau^2 * Sv^2 * (1-phie)^2)    [mD-like, depends on units]
    """
    with np.errstate(invalid="ignore", divide="ignore"):
        num = phie ** 3
        denom = (tau ** 2) * (Sv ** 2) * ((1.0 - phie) ** 2)
        k = np.where(denom > 0, num / denom, np.nan)
    return np.clip(k * 1e3, 0.0, None)   # scale to mD approx


def perm_coates(phie: np.ndarray, bvi: np.ndarray,
                ffv: np.ndarray | None = None,
                c: float = 10.0) -> np.ndarray:
    """Coates (SDR / NMR-analog):
    K = (PHIE^2 * (FFV/BVI))^2 * C^2   [mD]
    BVI = bound-volume irreducible, FFV = free-fluid volume
    If FFV is None, FFV = PHIE − BVI
    """
    if ffv is None:
        ffv = np.clip(phie - bvi, 0.0, None)
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = np.where(bvi > 1e-6, ffv / bvi, 0.0)
        k = (phie ** 2 * ratio) ** 2 * c ** 2
    return np.clip(k, 0.0, None)


def calc_permeability(model: str,
                      phie: np.ndarray,
                      swirr: float = 0.10,
                      c: float = 65.0) -> np.ndarray:
    """
    Dispatcher.  model: "Timur-Coates" | "Morris-Biggs" | "Kozeny-Carman"
    Returns K array [mD].
    """
    dispatch = {
        "Timur-Coates":    lambda: perm_timur(phie, swirr),
        "Morris-Biggs":    lambda: perm_morris_biggs(phie, swirr, c),
        "Kozeny-Carman":   lambda: perm_kozeny_carman(phie),
    }
    fn = dispatch.get(model, dispatch["Timur-Coates"])
    return fn()