"""
calculations/porosity.py
========================
Porosity calculations: PHID, PHIS, PHIN, and shale-corrected PHIE.
"""

from __future__ import annotations
import numpy as np


# ── Density Porosity ─────────────────────────────────────────────────────────

def phid(rhob: np.ndarray,
         rho_matrix: float = 2.65,
         rho_fluid: float = 1.0) -> np.ndarray:
    """Density porosity.
    PHID = (rho_matrix − RHOB) / (rho_matrix − rho_fluid)
    """
    denom = rho_matrix - rho_fluid
    if abs(denom) < 1e-9:
        return np.full_like(rhob, np.nan, dtype=float)
    return np.clip((rho_matrix - rhob) / denom, 0.0, 1.0)


# ── Sonic Porosity ────────────────────────────────────────────────────────────

def phis_wyllie(dt: np.ndarray,
                dt_matrix: float = 55.5,
                dt_fluid: float = 189.0,
                cp: float = 1.0) -> np.ndarray:
    """Wyllie time-average equation.
    PHIS = (DT − DT_matrix) / (DT_fluid − DT_matrix) / cp
    """
    denom = dt_fluid - dt_matrix
    if abs(denom) < 1e-9:
        return np.full_like(dt, np.nan, dtype=float)
    return np.clip(((dt - dt_matrix) / denom) / cp, 0.0, 1.0)


def phis_raymer(dt: np.ndarray,
                dt_matrix: float = 55.5) -> np.ndarray:
    """Raymer-Hunt-Gardner equation.
    PHIS = 1 − dt_matrix / DT
    """
    with np.errstate(invalid="ignore", divide="ignore"):
        phi = 1.0 - dt_matrix / dt
    return np.clip(phi, 0.0, 1.0)


# ── Neutron-Density Combination ──────────────────────────────────────────────

def phit_nd(nphi: np.ndarray, phid_arr: np.ndarray) -> np.ndarray:
    """Total porosity from neutron-density combination."""
    return np.clip((nphi + phid_arr) / 2.0, 0.0, 1.0)


# ── Shale correction → PHIE ──────────────────────────────────────────────────

def phie_from_phit(phit: np.ndarray, vshale: np.ndarray,
                   phish: float = 0.10) -> np.ndarray:
    """Effective porosity:
    PHIE = PHIT − Vsh * PHISH   (where PHISH = shale neutron porosity)
    """
    return np.clip(phit - vshale * phish, 0.0, 1.0)


def phie_density(rhob: np.ndarray,
                 vshale: np.ndarray,
                 rho_matrix: float = 2.65,
                 rho_fluid: float = 1.0,
                 rho_shale: float = 2.45) -> np.ndarray:
    """Density-derived PHIE with shale correction."""
    denom = rho_matrix - rho_fluid
    if abs(denom) < 1e-9:
        return np.full_like(rhob, np.nan, dtype=float)
    phi = (rho_matrix - rhob - vshale * (rho_matrix - rho_shale)) / denom
    return np.clip(phi, 0.0, 1.0)


# ── Main dispatcher ───────────────────────────────────────────────────────────

def calc_porosity(method: str = "Density",
                  rhob: np.ndarray | None = None,
                  nphi: np.ndarray | None = None,
                  dt: np.ndarray | None = None,
                  vshale: np.ndarray | None = None,
                  rho_matrix: float = 2.65,
                  rho_fluid: float = 1.0,
                  rho_shale: float = 2.45,
                  phish: float = 0.10,
                  dt_matrix: float = 55.5,
                  dt_fluid: float = 189.0,
                  sonic_method: str = "Wyllie",
                  correct_shale: bool = True) -> dict[str, np.ndarray]:
    """
    Returns a dict with keys: "PHIT", "PHIE", and optionally "PHID"/"PHIS".
    """
    results: dict[str, np.ndarray] = {}

    if method == "Density" and rhob is not None:
        phi = phid(rhob, rho_matrix, rho_fluid)
        results["PHID"] = phi
        results["PHIT"] = phi.copy()

    elif method == "Sonic" and dt is not None:
        if sonic_method == "Raymer":
            phi = phis_raymer(dt, dt_matrix)
        else:
            phi = phis_wyllie(dt, dt_matrix, dt_fluid)
        results["PHIS"] = phi
        results["PHIT"] = phi.copy()

    elif method == "N-D Combination" and nphi is not None and rhob is not None:
        phi_d = phid(rhob, rho_matrix, rho_fluid)
        phi_t = phit_nd(nphi, phi_d)
        results["PHID"] = phi_d
        results["PHIT"] = phi_t

    elif method == "Neutron Only" and nphi is not None:
        results["PHIT"] = np.clip(nphi, 0.0, 1.0)

    else:
        # Fallback: zeros
        size = (len(rhob) if rhob is not None else
                len(nphi) if nphi is not None else 100)
        results["PHIT"] = np.zeros(size)

    # Shale correction
    if correct_shale and vshale is not None and "PHIT" in results:
        results["PHIE"] = phie_from_phit(results["PHIT"], vshale, phish)
    else:
        results["PHIE"] = results.get("PHIT", np.zeros(1)).copy()

    return results