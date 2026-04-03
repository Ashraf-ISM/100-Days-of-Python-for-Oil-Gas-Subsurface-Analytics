"""Net pay calculation."""
from __future__ import annotations

import numpy as np


def compute_net_pay(vsh, phi, sw, perm, vsh_cut=0.4, phi_cut=0.05, sw_cut=0.65, perm_cut=0.1):
    vsh = np.asarray(vsh, dtype=float)
    phi = np.asarray(phi, dtype=float)
    sw = np.asarray(sw, dtype=float)
    perm = np.asarray(perm, dtype=float)
    mask = (vsh <= vsh_cut) & (phi >= phi_cut) & (sw <= sw_cut) & (perm >= perm_cut)
    return mask.astype(int)
