"""Shale volume calculations."""
from __future__ import annotations

import numpy as np

# Mapping from UI combo-box display text to method key used by compute_vsh_from_gr.
VSH_METHOD_MAP: dict[str, str] = {
    "Linear": "linear",
    "Larionov (Tertiary Rocks)": "larionov_tertiary",
    "Larionov (Older Rocks)": "larionov_older",
    "Clavier Model (Most Accurate)": "clavier",
    "Steiber Model": "steiber",
}

# --- Larionov (1969) empirical constants ---
_LARIONOV_TERTIARY_SCALE = 0.083   # pre-factor for Tertiary rocks
_LARIONOV_TERTIARY_BASE = 3.7      # exponent multiplier for Tertiary rocks
_LARIONOV_OLDER_SCALE = 0.33       # pre-factor for older (consolidated) rocks
_LARIONOV_OLDER_BASE = 2.0         # exponent multiplier for older rocks

# --- Clavier (1971) empirical constants ---
_CLAVIER_A = 3.38  # discriminant constant
_CLAVIER_B = 0.7   # IGR shift constant


def _igr(gr: np.ndarray, gr_min: float, gr_max: float) -> np.ndarray:
    """Compute the linear gamma-ray index (IGR) clamped to [0, 1]."""
    igr = (gr - gr_min) / (gr_max - gr_min + 1e-9)
    return np.clip(igr, 0.0, 1.0)


def compute_vsh_gr(gr, gr_min=None, gr_max=None):
    """Linear Vsh from gamma ray (IGR method)."""
    gr = np.asarray(gr, dtype=float)
    if gr_min is None:
        gr_min = np.nanpercentile(gr, 5)
    if gr_max is None:
        gr_max = np.nanpercentile(gr, 95)
    return _igr(gr, gr_min, gr_max)


def compute_vsh_larionov_tertiary(gr, gr_min=None, gr_max=None):
    """Larionov (1969) Vsh for Tertiary rocks.

    Vsh = 0.083 * (2 ** (3.7 * IGR) - 1)
    """
    gr = np.asarray(gr, dtype=float)
    if gr_min is None:
        gr_min = np.nanpercentile(gr, 5)
    if gr_max is None:
        gr_max = np.nanpercentile(gr, 95)
    igr = _igr(gr, gr_min, gr_max)
    vsh = _LARIONOV_TERTIARY_SCALE * (np.power(2.0, _LARIONOV_TERTIARY_BASE * igr) - 1.0)
    return np.clip(vsh, 0.0, 1.0)


def compute_vsh_larionov_older(gr, gr_min=None, gr_max=None):
    """Larionov (1969) Vsh for older (consolidated) rocks.

    Vsh = 0.33 * (2 ** (2 * IGR) - 1)
    """
    gr = np.asarray(gr, dtype=float)
    if gr_min is None:
        gr_min = np.nanpercentile(gr, 5)
    if gr_max is None:
        gr_max = np.nanpercentile(gr, 95)
    igr = _igr(gr, gr_min, gr_max)
    vsh = _LARIONOV_OLDER_SCALE * (np.power(2.0, _LARIONOV_OLDER_BASE * igr) - 1.0)
    return np.clip(vsh, 0.0, 1.0)


def compute_vsh_clavier(gr, gr_min=None, gr_max=None):
    """Clavier (1971) Vsh.

    Vsh = 1.7 - sqrt(3.38 - (IGR + 0.7) ** 2)
    """
    gr = np.asarray(gr, dtype=float)
    if gr_min is None:
        gr_min = np.nanpercentile(gr, 5)
    if gr_max is None:
        gr_max = np.nanpercentile(gr, 95)
    igr = _igr(gr, gr_min, gr_max)
    radicand = np.clip(_CLAVIER_A - (igr + _CLAVIER_B) ** 2, 0.0, None)
    vsh = 1.7 - np.sqrt(radicand)
    return np.clip(vsh, 0.0, 1.0)


def compute_vsh_steiber(gr, gr_min=None, gr_max=None):
    """Steiber (1970) Vsh.

    Vsh = IGR / (3 - 2 * IGR)
    """
    gr = np.asarray(gr, dtype=float)
    if gr_min is None:
        gr_min = np.nanpercentile(gr, 5)
    if gr_max is None:
        gr_max = np.nanpercentile(gr, 95)
    igr = _igr(gr, gr_min, gr_max)
    vsh = igr / (3.0 - 2.0 * igr + 1e-9)
    return np.clip(vsh, 0.0, 1.0)


def compute_vsh_from_gr(gr, gr_min=None, gr_max=None, method: str = "linear"):
    """Dispatch Vsh calculation to the chosen method.

    Parameters
    ----------
    gr:
        Gamma-ray values (array-like).
    gr_min, gr_max:
        Clean-sand and shale GR baseline values.  When *None* the P5/P95 of
        the supplied array are used as defaults.
    method:
        One of ``"linear"``, ``"larionov_tertiary"``, ``"larionov_older"``,
        ``"clavier"``, or ``"steiber"``.  Defaults to ``"linear"``.
    """
    _dispatch = {
        "linear": compute_vsh_gr,
        "larionov_tertiary": compute_vsh_larionov_tertiary,
        "larionov_older": compute_vsh_larionov_older,
        "clavier": compute_vsh_clavier,
        "steiber": compute_vsh_steiber,
    }
    func = _dispatch.get(method, compute_vsh_gr)
    return func(gr, gr_min=gr_min, gr_max=gr_max)
