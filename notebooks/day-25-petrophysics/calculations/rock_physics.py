"""
calculations/rock_physics.py
============================
Rock-physics calculations:
  • Elastic moduli from DT, DTS, RHOB
  • Acoustic Impedance (AI, SI)
  • Lambda-Mu-Rho (LMR)
  • Gassmann fluid substitution
  • Vp/Vs ratio
"""

from __future__ import annotations
import numpy as np


# ── Elastic moduli from sonic logs ────────────────────────────────────────────

def dt_to_vp(dt: np.ndarray, unit: str = "us/ft") -> np.ndarray:
    """Convert slowness to velocity (m/s or ft/s)."""
    if unit == "us/ft":
        return 304_800.0 / dt          # → m/s
    return 1_000_000.0 / dt            # us/m → m/s


def dt_to_vs(dts: np.ndarray, unit: str = "us/ft") -> np.ndarray:
    return dt_to_vp(dts, unit)


def calc_elastic_moduli(vp: np.ndarray,
                        vs: np.ndarray,
                        rho: np.ndarray) -> dict[str, np.ndarray]:
    """
    Compute bulk modulus K_sat, shear modulus G, P-wave modulus M,
    Young's modulus E, Poisson's ratio nu, lambda.
    All in GPa.
    rho in g/cc, vp/vs in m/s.
    """
    rho_kg = rho * 1000.0      # g/cc → kg/m³
    vp2 = vp ** 2
    vs2 = vs ** 2

    G = rho_kg * vs2 * 1e-9                    # GPa
    K = rho_kg * (vp2 - 4.0 / 3.0 * vs2) * 1e-9
    M = rho_kg * vp2 * 1e-9                     # P-wave modulus
    lam = K - 2.0 / 3.0 * G                    # Lambda

    with np.errstate(invalid="ignore", divide="ignore"):
        nu = (vp2 - 2 * vs2) / (2 * (vp2 - vs2))
        E  = 2 * G * (1 + nu)

    return {"K": K, "G": G, "M": M, "Lambda": lam, "nu": nu, "E": E}


# ── Acoustic Impedance ────────────────────────────────────────────────────────

def acoustic_impedance(vp: np.ndarray, rho: np.ndarray) -> np.ndarray:
    """AI = Vp * Rho   (m/s * g/cc → 10³ m/s·g/cc = kPa·s/m ~ kg/m²/s)"""
    return vp * rho


def shear_impedance(vs: np.ndarray, rho: np.ndarray) -> np.ndarray:
    return vs * rho


def reflection_coeff(ai: np.ndarray) -> np.ndarray:
    """Normal-incidence reflection coefficient series."""
    rc = np.zeros_like(ai)
    with np.errstate(invalid="ignore", divide="ignore"):
        rc[1:] = (ai[1:] - ai[:-1]) / (ai[1:] + ai[:-1])
    return rc


# ── Lambda-Mu-Rho (LMR) ──────────────────────────────────────────────────────

def lmr(vp: np.ndarray, vs: np.ndarray, rho: np.ndarray):
    """Returns lambda*rho (LR) and mu*rho (MR).  rho in g/cc."""
    rho_kg = rho * 1000.0
    MR = rho_kg * vs ** 2 * 1e-9          # GPa·g/cc (mu*rho)
    LR = rho_kg * (vp ** 2 - 2 * vs ** 2) * 1e-9
    return LR, MR


# ── Gassmann Fluid Substitution ──────────────────────────────────────────────

def gassmann(K_sat_initial: np.ndarray,
             G: np.ndarray,
             K_mineral: float,
             K_fluid_initial: float,
             K_fluid_final: float,
             phi: np.ndarray) -> dict[str, np.ndarray]:
    """
    Gassmann (1951) fluid substitution.

    Parameters
    ----------
    K_sat_initial : bulk modulus of rock saturated with initial fluid (GPa)
    G             : shear modulus (same for dry and saturated) (GPa)
    K_mineral     : mineral (grain) bulk modulus (GPa)
    K_fluid_initial / K_fluid_final : fluid bulk modulus before/after (GPa)
    phi           : total porosity (fraction)

    Returns dict with K_sat_final (GPa), Vp_ratio (Vp_new/Vp_old), etc.
    """
    Km = K_mineral

    # Dry-frame modulus via Gassmann rearrangement
    with np.errstate(invalid="ignore", divide="ignore"):
        delta_fluid_i = K_fluid_initial / (phi * (Km - K_fluid_initial))
        numer_dry = K_sat_initial / (Km - K_sat_initial) - delta_fluid_i
        denom_dry = 1.0 + numer_dry
        K_dry = Km * np.clip(numer_dry / denom_dry, 0.0, None)  # approx guard

    # Saturate with final fluid
    with np.errstate(invalid="ignore", divide="ignore"):
        delta_fluid_f = K_fluid_final / (phi * (Km - K_fluid_final))
        numer_f = K_dry / (Km - K_dry) + delta_fluid_f
        K_sat_final = Km * numer_f / (1.0 + numer_f)

    return {
        "K_dry":       K_dry,
        "G":           G,
        "K_sat_final": K_sat_final,
    }


def fluid_mix_modulus(k1: float, s1: float,
                      k2: float, s2: float) -> float:
    """Reuss (harmonic) average fluid mixing (Brie is common alternative)."""
    with np.errstate(invalid="ignore", divide="ignore"):
        km = 1.0 / (s1 / k1 + s2 / k2) if (k1 > 0 and k2 > 0) else 0.0
    return km


# ── Vp/Vs ─────────────────────────────────────────────────────────────────────

def vpvs_ratio(vp: np.ndarray, vs: np.ndarray) -> np.ndarray:
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(vs > 0, vp / vs, np.nan)


# ── Dispatcher ────────────────────────────────────────────────────────────────

def run_rock_physics(well, dt_name="DT", dts_name="DTS",
                     rhob_name="RHOB", phie_name="PHIE") -> dict:
    """
    Convenience function: fetch curves from a WellData, compute everything,
    return a dict of result arrays ready to store back.
    """
    from core.data_model import WellData
    assert isinstance(well, WellData)

    results = {}
    dt_c   = well.get_curve(dt_name)
    dts_c  = well.get_curve(dts_name)
    rhob_c = well.get_curve(rhob_name)
    phie_c = well.get_curve(phie_name)

    if dt_c is None or rhob_c is None:
        return {"error": "Missing DT or RHOB curve"}

    vp = dt_to_vp(dt_c.data)
    rho = rhob_c.data

    results["AI"]  = acoustic_impedance(vp, rho)
    results["VP"]  = vp

    if dts_c is not None:
        vs = dt_to_vs(dts_c.data)
        results["VS"] = vs
        moduli = calc_elastic_moduli(vp, vs, rho)
        results.update(moduli)
        lr, mr = lmr(vp, vs, rho)
        results["LR"] = lr
        results["MR"] = mr
        results["SI"] = shear_impedance(vs, rho)
        results["VPVS"] = vpvs_ratio(vp, vs)

    return results