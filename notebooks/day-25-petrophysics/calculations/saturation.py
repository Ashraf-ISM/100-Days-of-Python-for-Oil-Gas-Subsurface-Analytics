"""Water saturation calculations panel"""
from __future__ import annotations

import numpy as np


def compute_sw_archie(phi, rt, rw=0.1, a=1.0, m=2.0, n=2.0):
    phi = np.asarray(phi, dtype=float)
    rt = np.asarray(rt, dtype=float)
    sw = (a * rw / (rt * (phi ** m) + 1e-9)) ** (1.0 / n)
    return np.clip(sw, 0.0, 1.0)


def compute_sw_simandoux(phi, rt, vsh, rw=0.1, rsh=2.0, a=1.0, m=2.0, n=2.0):
    """Simple Simandoux-style Sw estimate.

    Uses the practical form:
    1/Rt = Vsh/Rsh + (Phi^m / (a*Rw)) * Sw^n
    """
    phi = np.asarray(phi, dtype=float)
    rt = np.asarray(rt, dtype=float)
    vsh = np.asarray(vsh, dtype=float)

    inv_rt = 1.0 / (rt + 1e-9)
    shale_term = vsh / (rsh + 1e-9)
    clean_term = np.maximum(inv_rt - shale_term, 0.0)
    sw_n = (clean_term * a * rw) / (np.power(np.clip(phi, 1e-6, None), m) + 1e-9)
    sw = np.power(np.clip(sw_n, 0.0, None), 1.0 / max(float(n), 1e-6))
    return np.clip(sw, 0.0, 1.0)


def compute_sw_modified_simandoux(phi, rt, vsh, rw=0.1, rsh=2.0, a=1.0, m=2.0, n=2.0):
    """Modified Simandoux with a simple clean-sand fraction correction."""
    phi = np.asarray(phi, dtype=float)
    rt = np.asarray(rt, dtype=float)
    vsh = np.asarray(vsh, dtype=float)

    effective_phi = np.clip(phi * (1.0 - np.clip(vsh, 0.0, 0.95)), 1e-6, None)
    return compute_sw_simandoux(effective_phi, rt, vsh, rw=rw, rsh=rsh, a=a, m=m, n=n)


def compute_sw_indonesia(phi, rt, vsh, rw=0.1, rsh=2.0, a=1.0, m=2.0, n=2.0):
    """Lightweight Indonesia approximation.

    Kept intentionally simple by blending Archie and Simandoux responses.
    """
    sw_archie = compute_sw_archie(phi, rt, rw=rw, a=a, m=m, n=n)
    sw_sim = compute_sw_simandoux(phi, rt, vsh, rw=rw, rsh=rsh, a=a, m=m, n=n)
    vsh_weight = np.clip(np.asarray(vsh, dtype=float), 0.0, 1.0)
    sw = (1.0 - vsh_weight) * sw_archie + vsh_weight * sw_sim
    return np.clip(sw, 0.0, 1.0)
