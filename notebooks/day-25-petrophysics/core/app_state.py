"""PetroARX AppState — captures all restorable UI and interpretation parameters.

This module defines AppState, a dataclass that is pickled inside every .ash
project archive. When a project is loaded, AppState is used to restore all
spinbox values, combo selections, cutoff parameters, and the active-well
name so the application returns to its exact working state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


# ─────────────────────────────────────────────────────────────────────────────
#  Version tag embedded in every saved state; bump when adding new fields.
# ─────────────────────────────────────────────────────────────────────────────
APP_STATE_VERSION = "1.0"


@dataclass
class AppState:
    """All serialisable application state saved inside an .ash project file."""

    # ── Schema version ────────────────────────────────────────────────────────
    version: str = APP_STATE_VERSION

    # ── Session ───────────────────────────────────────────────────────────────
    active_well: str = ""
    """Name of the well that should be selected when the project is reopened."""

    rename_history: Dict[str, List[List[str]]] = field(default_factory=dict)
    """Per-well column-rename undo stacks, keyed by well name."""

    # ── Vsh / Shale Volume panel ──────────────────────────────────────────────
    vsh_gr_curve: str = ""
    vsh_gr_min: float = 15.0
    vsh_gr_max: float = 120.0
    vsh_method: str = "Linear"
    vsh_out_name: str = "VSH"

    # ── Porosity panel ────────────────────────────────────────────────────────
    phi_method: str = "Density-Neutron (PHIE)"
    phi_matrix_type: str = "Sandstone"
    phi_rho_ma: float = 2.65
    phi_rho_f: float = 1.0
    phi_dt_ma: float = 55.5
    phi_dt_f: float = 189.0
    phi_phi_sh: float = 0.1
    phi_vsh_cut: float = 0.5
    phi_shale_corr: bool = False
    phi_out_name: str = "PHIE"

    # ── Water Saturation panel ────────────────────────────────────────────────
    sw_method: str = "Archie"
    sw_rw: float = 0.05
    sw_a: float = 1.0
    sw_m: float = 2.0
    sw_n: float = 2.0
    sw_rsh: float = 2.0
    sw_rt_curve: str = ""
    sw_phi_curve: str = ""
    sw_out_name: str = "SW"

    # ── Net Pay cutoffs ───────────────────────────────────────────────────────
    net_pay_vsh_cut: float = 0.4
    net_pay_phi_cut: float = 0.05
    net_pay_sw_cut: float = 0.65
    net_pay_out_name: str = "NET_PAY"

    # ── QC panel ─────────────────────────────────────────────────────────────
    qc_curve: str = ""
    qc_method: str = ""
    qc_threshold: float = 3.0
    qc_window: int = 5
    qc_from: float = 0.0
    qc_to: float = 9999.0
    qc_check_missing: bool = True
    qc_check_outliers: bool = True
    qc_check_spikes: bool = True
    qc_check_negative: bool = False

    # ── Depth filter ─────────────────────────────────────────────────────────
    depth_from: float = 0.0
    depth_to: float = 9999.0

    # ── Extra / future-proof ──────────────────────────────────────────────────
    extra: Dict[str, Any] = field(default_factory=dict)
    """Arbitrary key-value store for future panel parameters."""

    # ─────────────────────────────────────────────────────────────────────────
    #  Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Return a plain dict (JSON-safe values only) for the manifest."""
        return {
            "version": self.version,
            "active_well": self.active_well,
            "vsh_method": self.vsh_method,
            "phi_method": self.phi_method,
            "sw_method": self.sw_method,
        }

    @classmethod
    def default(cls) -> "AppState":
        """Return a fresh default state."""
        return cls()
