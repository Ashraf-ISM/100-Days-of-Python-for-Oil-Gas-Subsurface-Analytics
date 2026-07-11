"""Permeability estimation models for petrophysical evaluation.

Supported models:
    - Timur (Coates)  : K = C * (PHI^a) * ((1 - Swi) / Swi)^b
    - Kozeny-Carman   : K = C * (PHI^3) / (1 - PHI)^2
    - Wyllie-Rose     : K = C * (PHI^a) / (Swi^b)
    - Core Regression : K = 10^(a * PHI + b)   (empirical log-linear fit)
"""
from __future__ import annotations

import numpy as np


def compute_perm_timur(
    phi,
    sw,
    swi: float = 0.2,
    coeff_c: float = 0.0316,
) -> np.ndarray:
    """Timur / Coates permeability model.

    K = coeff_c * (phi^4) * ((1 - Swi) / Swi)^2   [Coates form]
    Falls back to the classic Timur form when Swi is near 0.

    Args:
        phi: Effective porosity (fraction, 0-1).
        sw: Water saturation (fraction, 0-1) — used only if swi is not set.
        swi: Irreducible water saturation (fraction, 0-1).
        coeff_c: Calibration coefficient (default 0.0316 typical for mD).

    Returns:
        Permeability in mD.
    """
    phi = np.asarray(phi, dtype=float)
    swi_val = np.clip(swi, 1e-6, 0.9999)
    bvw_ratio = ((1.0 - swi_val) / swi_val) ** 2
    perm = coeff_c * (phi ** 4) * bvw_ratio
    return np.maximum(perm, 0.0)


def compute_perm_kozeny_carman(
    phi,
    coeff_c: float = 1000.0,
) -> np.ndarray:
    """Kozeny-Carman permeability model.

    K = C * PHI^3 / (1 - PHI)^2

    Args:
        phi: Effective porosity (fraction, 0-1).
        coeff_c: Calibration coefficient (default 1000).

    Returns:
        Permeability in mD.
    """
    phi = np.clip(np.asarray(phi, dtype=float), 0.0, 0.9999)
    perm = coeff_c * (phi ** 3) / ((1.0 - phi) ** 2 + 1e-12)
    return np.maximum(perm, 0.0)


def compute_perm_wyllie_rose(
    phi,
    swi: float = 0.2,
    coeff_c: float = 100.0,
    exp_a: float = 3.0,
    exp_b: float = 2.0,
) -> np.ndarray:
    """Wyllie-Rose permeability model.

    K = C * PHI^a / Swi^b

    Args:
        phi: Effective porosity (fraction, 0-1).
        swi: Irreducible water saturation (fraction, 0-1).
        coeff_c: Calibration coefficient.
        exp_a: Porosity exponent.
        exp_b: Swi exponent.

    Returns:
        Permeability in mD.
    """
    phi = np.asarray(phi, dtype=float)
    swi_val = np.clip(swi, 1e-6, 0.9999)
    perm = coeff_c * (phi ** exp_a) / (swi_val ** exp_b)
    return np.maximum(perm, 0.0)


def compute_perm_core_regression(
    phi,
    coeff_a: float = 25.0,
    coeff_b: float = -1.5,
) -> np.ndarray:
    """Empirical log-linear core regression model.

    K = 10^(a * PHI + b)

    Typically fitted against core-plug data using linear regression
    on log10(K) vs PHI.

    Args:
        phi: Effective porosity (fraction, 0-1).
        coeff_a: Slope coefficient.
        coeff_b: Intercept coefficient.

    Returns:
        Permeability in mD.
    """
    phi = np.asarray(phi, dtype=float)
    perm = np.power(10.0, coeff_a * phi + coeff_b)
    return np.maximum(perm, 0.0)
