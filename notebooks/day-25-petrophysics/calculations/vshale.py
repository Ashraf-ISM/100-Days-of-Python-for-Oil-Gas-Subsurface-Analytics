"""Shale volume calculations."""
from __future__ import annotations

import numpy as np


def compute_vsh_gr(gr, gr_min=None, gr_max=None):
    gr = np.asarray(gr, dtype=float)
    if gr_min is None:
        gr_min = np.nanpercentile(gr, 5)
    if gr_max is None:
        gr_max = np.nanpercentile(gr, 95)
    vsh = (gr - gr_min) / (gr_max - gr_min + 1e-9)
    return np.clip(vsh, 0.0, 1.0)
