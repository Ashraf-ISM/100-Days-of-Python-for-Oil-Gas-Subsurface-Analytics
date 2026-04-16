"""Porosity calculations."""
from __future__ import annotations

import numpy as np

def compute_phi_from_density(rhob, rho_ma=2.65, rho_f=1.0):
    rhob = np.asarray(rhob, dtype=float)
    phi = (rho_ma - rhob) / (rho_ma - rho_f + 1e-9)
    return np.clip(phi, 0.0, 1.0)


def compute_phi_combo(nphi, rhob, rho_ma=2.65, rho_f=1.0):
    nphi = np.asarray(nphi, dtype=float)
    phi_d = compute_phi_from_density(rhob, rho_ma=rho_ma, rho_f=rho_f)
    phi = 0.5 * (nphi + phi_d)
    return np.clip(phi, 0.0, 1.0)
