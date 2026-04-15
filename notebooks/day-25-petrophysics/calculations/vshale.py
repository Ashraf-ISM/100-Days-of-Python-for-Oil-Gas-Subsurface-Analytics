"""Shale volume calculations."""
from __future__ import annotations

import numpy as np

def compute_vsh_gr(gr, gr_min=None, gr_max=None, model: str = "linear"):
    gr = np.asarray(gr, dtype=float)
    if gr_min is None:
        gr_min = np.nanpercentile(gr, 5)  # GR Clean
    if gr_max is None:
        gr_max = np.nanpercentile(gr, 95)  # GR Shale
    igr = (gr - gr_min) / (gr_max - gr_min + 1e-9)
    igr = np.clip(igr, 0.0, 1.0)

    name = str(model or "linear").strip().lower()
    if "larionov" in name and "tertiary" in name:
        # Larionov for tertiary rocks.
        vsh = 0.083 * (2 ** (3.7 * igr) - 1.0)
    elif "larionov" in name:
        # Larionov for older rocks.
        vsh = 0.33 * (2 ** (2.0 * igr) - 1.0)
    elif "clavier" in name:
        inside = 3.38 - np.square(igr + 0.7)
        vsh = 1.7 - np.sqrt(np.clip(inside, 0.0, None))
    elif "steiber" in name:
        vsh = igr / (3.0 - 2.0 * igr + 1e-9)
    else:
        vsh = igr

    return np.clip(vsh, 0.0, 1.0)
