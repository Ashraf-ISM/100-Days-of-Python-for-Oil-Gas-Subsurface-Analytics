"""
calculations/net_pay.py
=======================
Net-pay and hydrocarbon-pore-volume calculation from cutoff criteria.
"""

from __future__ import annotations
import numpy as np
from typing import Dict


def apply_cutoffs(depth: np.ndarray,
                  vshale: np.ndarray,
                  phie: np.ndarray,
                  sw: np.ndarray,
                  k: np.ndarray | None = None,
                  vsh_cutoff: float = 0.50,
                  phie_cutoff: float = 0.05,
                  sw_cutoff: float = 0.70,
                  k_cutoff: float = 1.0) -> Dict[str, np.ndarray]:
    """
    Returns dict with boolean mask 'net_pay' and derived NET, HPVT arrays.

    net_pay = (Vshale ≤ vsh_cutoff) AND (PHIE ≥ phie_cutoff) AND (Sw ≤ sw_cutoff)
              AND (if K provided) (K ≥ k_cutoff)
    """
    mask = (
        (vshale <= vsh_cutoff) &
        (phie >= phie_cutoff) &
        (sw <= sw_cutoff) &
        np.isfinite(vshale) &
        np.isfinite(phie) &
        np.isfinite(sw)
    )
    if k is not None:
        mask &= (k >= k_cutoff) & np.isfinite(k)

    # Approximate depth step
    if len(depth) > 1:
        step = np.median(np.diff(depth))
    else:
        step = 0.1

    # Net pay flag (0 or 1 per sample)
    net_flag = mask.astype(float)

    # HPVT = PHIE * (1 − Sw) * step for each net-pay sample
    hpvt = np.where(mask, phie * (1.0 - sw) * step, 0.0)

    return {
        "net_pay_mask": mask,
        "net_flag":     net_flag,
        "hpvt":         hpvt,
        "net_thickness":  float(net_flag.sum() * step),
        "gross_thickness": float(len(depth) * step),
        "hpv_total":       float(hpvt.sum()),
        "avg_phie_net":    float(np.nanmean(phie[mask])) if mask.any() else 0.0,
        "avg_sw_net":      float(np.nanmean(sw[mask])) if mask.any() else 0.0,
    }


def summarize_net_pay(result: dict) -> str:
    """Format a human-readable summary string."""
    lines = [
        f"  Net Thickness  : {result['net_thickness']:.2f} m",
        f"  Gross Thickness: {result['gross_thickness']:.2f} m",
        f"  N/G ratio      : {result['net_thickness'] / max(result['gross_thickness'], 0.01):.3f}",
        f"  HPV total      : {result['hpv_total']:.3f} m",
        f"  Avg PHIE (net) : {result['avg_phie_net']*100:.1f} %",
        f"  Avg Sw   (net) : {result['avg_sw_net']*100:.1f} %",
    ]
    return "\n".join(lines)