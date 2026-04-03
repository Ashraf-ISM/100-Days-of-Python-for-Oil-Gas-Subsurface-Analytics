"""Permeability calculations (Timur-style)."""
from __future__ import annotations

import numpy as np


def compute_perm_timur(phi, sw, a=1000.0, b=4.0, c=2.0):
    phi = np.asarray(phi, dtype=float)
    sw = np.asarray(sw, dtype=float)
    perm = a * (phi ** b) / ((sw + 1e-9) ** c)
    return np.maximum(perm, 0.0)
