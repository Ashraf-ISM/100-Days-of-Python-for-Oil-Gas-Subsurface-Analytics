"""
calculations/saturation.py
==========================
Water-saturation models: Archie, Simandoux, Indonesia (Poupon-Leveaux),
Dual Water (Clavier), Waxman-Smits.

Returns Sw (fraction 0-1).
"""

from __future__ import annotations
import numpy as np


def _safe_div(a, b, fill=np.nan):
    with np.errstate(invalid="ignore", divide="ignore"):
        result = np.where(np.abs(b) > 1e-30, a / b, fill)
    return result


# ── Archie ────────────────────────────────────────────────────────────────────

def sw_archie(rt: np.ndarray,
              phie: np.ndarray,
              rw: float,
              a: float = 1.0,
              m: float = 2.0,
              n: float = 2.0) -> np.ndarray:
    """Classic Archie equation:
    Sw^n = (a * Rw) / (phie^m * Rt)
    """
    with np.errstate(invalid="ignore", divide="ignore"):
        sw_n = _safe_div(a * rw, (phie ** m) * rt)
        sw = sw_n ** (1.0 / n)
    return np.clip(sw, 0.0, 1.0)


# ── Simandoux ─────────────────────────────────────────────────────────────────

def sw_simandoux(rt: np.ndarray,
                 phie: np.ndarray,
                 vshale: np.ndarray,
                 rw: float,
                 rshale: float = 4.0,
                 a: float = 1.0,
                 m: float = 2.0,
                 n: float = 2.0) -> np.ndarray:
    """Simandoux (1963) for shaly sands."""
    c = (phie ** m) / (a * rw)
    vsh_rt = _safe_div(vshale, rshale)
    discriminant = (c / 2.0) ** 2 + _safe_div(c, rt) - c * vsh_rt
    with np.errstate(invalid="ignore"):
        sw = _safe_div(c, 2.0) + np.sqrt(np.clip(discriminant, 0.0, None))
    return np.clip(sw ** (1.0 / n), 0.0, 1.0)


# ── Modified Simandoux ────────────────────────────────────────────────────────

def sw_modified_simandoux(rt: np.ndarray,
                          phie: np.ndarray,
                          vshale: np.ndarray,
                          rw: float,
                          rshale: float = 4.0,
                          m: float = 2.0,
                          n: float = 2.0) -> np.ndarray:
    """Modified Simandoux — accounts for effective porosity with Vsh."""
    c = (phie ** m) * (1.0 - vshale) / rw
    vsh_rt = _safe_div(vshale, rshale)
    discriminant = (c / 2.0) ** 2 + _safe_div(c, rt) - c * vsh_rt
    with np.errstate(invalid="ignore"):
        sw = _safe_div(c, 2.0) + np.sqrt(np.clip(discriminant, 0.0, None))
    return np.clip(sw ** (1.0 / n), 0.0, 1.0)


# ── Indonesia (Poupon-Leveaux) ────────────────────────────────────────────────

def sw_indonesia(rt: np.ndarray,
                 phie: np.ndarray,
                 vshale: np.ndarray,
                 rw: float,
                 rshale: float = 4.0,
                 a: float = 1.0,
                 m: float = 2.0,
                 n: float = 2.0) -> np.ndarray:
    """Indonesia (Poupon-Leveaux, 1970)."""
    with np.errstate(invalid="ignore", divide="ignore"):
        term1 = _safe_div(phie ** (m / 2.0), np.sqrt(a * rw))
        term2 = _safe_div(vshale ** (1.0 - 0.5 * vshale), np.sqrt(rshale))
        c = (term1 + term2) ** 2
        sw_n = _safe_div(c, _safe_div(1.0, rt))
    return np.clip(sw_n ** (1.0 / n), 0.0, 1.0)


# ── Dual Water (Clavier) ──────────────────────────────────────────────────────

def sw_dual_water(rt: np.ndarray,
                  phit: np.ndarray,
                  phie: np.ndarray,
                  vshale: np.ndarray,
                  rw: float,
                  rwb: float = 0.025,
                  a: float = 1.0,
                  m: float = 2.0,
                  n: float = 2.0) -> np.ndarray:
    """Dual Water model (Clavier et al., 1984)."""
    swb = np.clip(_safe_div(phit - phie, phit), 0.0, 1.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        rw_eff = _safe_div(1.0, _safe_div(1.0 - swb, rw) + _safe_div(swb, rwb))
        sw_n = _safe_div(a * rw_eff, (phit ** m) * rt)
    return np.clip(sw_n ** (1.0 / n), 0.0, 1.0)


# ── BVW & Hydrocarbon Saturation ─────────────────────────────────────────────

def calc_bvw(phie: np.ndarray, sw: np.ndarray) -> np.ndarray:
    """Bulk Volume Water = PHIE × Sw"""
    return phie * sw


def calc_sh(sw: np.ndarray) -> np.ndarray:
    """Hydrocarbon saturation = 1 − Sw"""
    return np.clip(1.0 - sw, 0.0, 1.0)


def calc_moveable_hc(sxo: np.ndarray, sw: np.ndarray) -> np.ndarray:
    """Moveable HC = Sxo − Sw  (flush zone vs. un-invaded)"""
    return np.clip(sxo - sw, 0.0, 1.0)


# ── Rw estimation ─────────────────────────────────────────────────────────────

def rw_from_temperature(salinity_ppm: float, temp_c: float) -> float:
    """Estimate formation water resistivity from NaCl salinity.
    Uses Bateman & Konen simplified Arps equation.
    """
    rw_75 = 400_000.0 / salinity_ppm          # Rw at 75°F (24°C)
    rw_t = rw_75 * (24.0 + 21.5) / (temp_c + 21.5)
    return rw_t


# ── Dispatcher ───────────────────────────────────────────────────────────────

def calc_saturation(model: str,
                    rt: np.ndarray,
                    phie: np.ndarray,
                    rw: float,
                    vshale: np.ndarray | None = None,
                    phit: np.ndarray | None = None,
                    rshale: float = 4.0,
                    rwb: float = 0.025,
                    a: float = 1.0,
                    m: float = 2.0,
                    n: float = 2.0) -> dict[str, np.ndarray]:
    """
    Dispatcher.  model options:
      "Archie" | "Simandoux" | "Modified Simandoux"
      | "Indonesia Equation (Poupon-Leveaux)"
      | "Dual Water (Clavier et al.)"
    Returns dict with keys: SW, BVW, SH
    """
    if vshale is None:
        vshale = np.zeros_like(phie)
    if phit is None:
        phit = phie.copy()

    sw_funcs = {
        "Archie":                               lambda: sw_archie(rt, phie, rw, a, m, n),
        "Simandoux":                            lambda: sw_simandoux(rt, phie, vshale, rw, rshale, a, m, n),
        "Modified Simandoux":                   lambda: sw_modified_simandoux(rt, phie, vshale, rw, rshale, m, n),
        "Indonesia Equation (Poupon-Leveaux)":  lambda: sw_indonesia(rt, phie, vshale, rw, rshale, a, m, n),
        "Dual Water (Clavier et al.)":          lambda: sw_dual_water(rt, phit, phie, vshale, rw, rwb, a, m, n),
    }
    fn = sw_funcs.get(model, sw_funcs["Archie"])
    sw = fn()

    return {
        "SW":  sw,
        "BVW": calc_bvw(phie, sw),
        "SH":  calc_sh(sw),
    }