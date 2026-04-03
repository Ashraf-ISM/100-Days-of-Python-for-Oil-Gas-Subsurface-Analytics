"""Water saturation calculations (Archie)."""
from __future__ import annotations

import numpy as np


def compute_sw_archie(phi, rt, rw=0.1, a=1.0, m=2.0, n=2.0):
    phi = np.asarray(phi, dtype=float)
    rt = np.asarray(rt, dtype=float)
    sw = (a * rw / (rt * (phi ** m) + 1e-9)) ** (1.0 / n)
    return np.clip(sw, 0.0, 1.0)
