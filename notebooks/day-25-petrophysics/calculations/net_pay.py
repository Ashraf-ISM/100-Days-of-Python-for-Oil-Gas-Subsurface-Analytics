"""Net pay calculation."""
from __future__ import annotations

import numpy as np


def compute_net_pay(vsh, phi, sw, perm=None, vsh_cut=0.4, phi_cut=0.05, sw_cut=0.65, perm_cut=0.1):
    """Return a pay flag based on the single-well cutoffs.

    The permeability argument is retained for backward compatibility, but the
    non-zone-based module only uses shale volume, porosity, and water
    saturation cutoffs.
    """

    _ = (perm, perm_cut)
    vsh = np.asarray(vsh, dtype=float)
    phi = np.asarray(phi, dtype=float)
    sw = np.asarray(sw, dtype=float)
    mask = (vsh <= vsh_cut) & (phi >= phi_cut) & (sw <= sw_cut)
    return mask.astype(int)
