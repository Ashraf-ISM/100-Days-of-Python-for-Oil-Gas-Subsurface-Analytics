"""
preview_plot_service.py
-----------------------
Generates the professional multi-track well-log prediction preview figure
that is embedded inside the Missing Log Prediction panel.

Tracks rendered (matching PetroArx reference screenshot):
  Track 0 : GR  (green)
  Track 1 : NPHI (blue)
  Track 2 : Target log — Actual (black solid) vs Predicted (black dashed)
  Track 3 : RHOB (red)
  Track 4 : RT   (olive / dark-teal) — log scale
  
Missing depth intervals are shaded amber on every track.
"""
from __future__ import annotations

from typing import Optional, List, Tuple

import numpy as np
import pandas as pd

# ─── default colour / style constants ─────────────────────────────────────────
_TRACK_COLORS = {
    "GR":    "#22C55E",    # green
    "NPHI":  "#3B82F6",    # blue
    "RHOB":  "#EF4444",    # red
    "RT":    "#854D0E",    # brown-olive (log scale)
    "DT":    "#111827",    # near-black
    "DTC":   "#111827",
    "DTS":   "#6366F1",
    "CALI":  "#A855F7",
    "PE":    "#EC4899",
    "SP":    "#14B8A6",
}
_CLR_PREDICTED = "#6366F1"      # dashed indigo for predicted curve
_CLR_MISSING   = "#FEF3C7"      # amber-50 fill for missing intervals
_CLR_BG        = "#F8FAFC"
_CLR_TRACK_BG  = "#FFFFFF"
_CLR_GRID      = "#E5E7EB"
_CLR_TICK      = "#9CA3AF"

# Log-scale tracks
_LOG_SCALE_LOGS = {"RT", "RD", "ILD", "ILM", "LLD", "LLS", "RILD", "RILM",
                   "RS", "RM", "RXOZ", "MSFL", "FRES"}

_UNIT_MAP = {
    "GR": "gAPI", "NPHI": "v/v", "RHOB": "g/cc", "DT": "µs/ft",
    "DTC": "µs/ft", "DTS": "µs/ft", "RT": "ohm.m", "RD": "ohm.m",
    "ILD": "ohm.m", "CALI": "in", "PE": "b/e", "SP": "mV",
    "MD": "m", "DEPT": "m", "DEPTH": "m", "PORO": "v/v",
    "PHI": "v/v", "SW": "v/v", "VCL": "v/v", "VSH": "v/v",
}


def _guess_unit(name: str) -> str:
    key = name.upper().split("_")[0].split("-")[0].strip()
    if key in _UNIT_MAP:
        return _UNIT_MAP[key]
    for k, v in _UNIT_MAP.items():
        if k in key:
            return v
    return "—"


def _track_color(name: str) -> str:
    key = name.upper().split("_")[0].split("-")[0]
    if key in _TRACK_COLORS:
        return _TRACK_COLORS[key]
    # cycle through extra palette
    extras = ["#0EA5E9", "#8B5CF6", "#F97316", "#10B981", "#F43F5E"]
    return extras[abs(hash(key)) % len(extras)]


def _shade_missing(ax, vals: np.ndarray, depth: np.ndarray,
                   color: str = _CLR_MISSING) -> None:
    """Shade depth intervals where vals is NaN."""
    in_gap = False
    gap_start = None
    for v, d in zip(vals, depth):
        is_nan = np.isnan(float(v)) if not isinstance(v, str) else True
        if is_nan and not in_gap:
            gap_start = d
            in_gap = True
        elif not is_nan and in_gap:
            ax.axhspan(float(gap_start), float(d),
                       color=color, alpha=0.35, zorder=1)
            in_gap = False
    if in_gap and gap_start is not None and len(depth) > 0:
        ax.axhspan(float(gap_start), float(depth[-1]),
                   color=color, alpha=0.35, zorder=1)


class PreviewPlotService:
    """
    Builds and returns a matplotlib Figure for the prediction preview panel.

    Parameters
    ----------
    df           : well DataFrame (must contain a depth column)
    depth_col    : name of the depth column (DEPT / DEPTH / MD)
    target       : name of the target log (what was predicted)
    features     : ordered list of input feature log names to display as tracks
    pred_series  : pd.Series (index aligned to df) with predicted values,
                   or None if no model has been trained yet
    missing_ints : list of (start_depth, end_depth) tuples for missing intervals
    depth_scale  : "MD" or "TVD" (label only; actual depth column is depth_col)
    max_tracks   : cap on how many feature tracks to show alongside the target
    """

    def __init__(
        self,
        df: pd.DataFrame,
        depth_col: Optional[str],
        target: str,
        features: List[str],
        pred_series: Optional[pd.Series] = None,
        missing_ints: Optional[List[Tuple[float, float]]] = None,
        depth_scale: str = "TVD",
        max_tracks: int = 4,
    ):
        self.df          = df.copy()
        self.depth_col   = depth_col
        self.target      = target
        self.features    = features[:max_tracks]
        self.pred_series = pred_series
        self.missing_ints = missing_ints or []
        self.depth_scale  = depth_scale

    # ── public API ─────────────────────────────────────────────────────────────

    def build_figure(self, d_from: float = None, d_to: float = None,
                     lw: float = 0.9):
        """
        Build and return the matplotlib Figure.

        Parameters
        ----------
        d_from / d_to : optional depth window
        lw            : line width for log curves
        """
        try:
            import matplotlib
            matplotlib.use("Qt5Agg")
            import matplotlib.pyplot as plt
            from matplotlib.ticker import AutoMinorLocator, LogLocator
        except ImportError:
            return None

        # ── slice depth window ────────────────────────────────────────────────
        df = self.df.copy()
        if self.depth_col and self.depth_col in df.columns:
            depth_num = pd.to_numeric(df[self.depth_col], errors="coerce")
            if d_from is not None:
                df = df[depth_num >= d_from]
            if d_to is not None:
                df = df[depth_num <= d_to]

        depth = (
            pd.to_numeric(df[self.depth_col], errors="coerce").values
            if self.depth_col and self.depth_col in df.columns
            else np.arange(len(df))
        )

        # ── determine tracks ─────────────────────────────────────────────────
        # Always: target track, then feature tracks (up to max_tracks)
        all_tracks = [self.target] + [
            f for f in self.features if f != self.target and f in df.columns
        ]
        n = len(all_tracks)
        if n == 0:
            return None

        # ── figure creation ───────────────────────────────────────────────────
        fig_w = max(7, 1.9 * n)
        fig, axes = plt.subplots(
            1, n, figsize=(fig_w, 8),
            sharey=True, facecolor=_CLR_BG,
        )
        plt.subplots_adjust(
            left=0.07, right=0.99, top=0.92, bottom=0.05,
            wspace=0.30,
        )
        if n == 1:
            axes = [axes]

        for ax_idx, log_name in enumerate(all_tracks):
            ax = axes[ax_idx]
            colour = _track_color(log_name)
            ax.set_facecolor(_CLR_TRACK_BG)
            ax.invert_yaxis()

            # data
            vals = (
                pd.to_numeric(df[log_name], errors="coerce").values
                if log_name in df.columns else np.full(len(depth), np.nan)
            )

            # log scale for resistivity
            is_log = any(k in log_name.upper() for k in _LOG_SCALE_LOGS)
            if is_log:
                positive = vals[vals > 0]
                if positive.size > 0:
                    try:
                        ax.set_xscale("log")
                    except Exception:
                        pass

            # main curve
            ax.plot(vals, depth, color=colour, linewidth=lw, zorder=3, alpha=0.9)

            # predicted overlay (target track only)
            if ax_idx == 0 and self.pred_series is not None:
                pred_vals = self.pred_series.reindex(df.index).values
                ax.plot(
                    pred_vals, depth,
                    color=_CLR_PREDICTED, linewidth=lw,
                    linestyle="--", alpha=0.85, zorder=4,
                    label="Predicted",
                )

            # shade missing intervals
            _shade_missing(ax, vals, depth)

            # spine & tick styling
            ax.tick_params(axis="both", labelsize=6.5, colors=_CLR_TICK, length=3)
            ax.yaxis.set_minor_locator(AutoMinorLocator(5))
            ax.grid(True, axis="y", color=_CLR_GRID, linewidth=0.35, linestyle="--")
            ax.grid(True, axis="y", which="minor",
                    color=_CLR_GRID, linewidth=0.2, linestyle=":")
            ax.grid(True, axis="x", color=_CLR_GRID, linewidth=0.25)
            for sp in ax.spines.values():
                sp.set_edgecolor(_CLR_GRID)
                sp.set_linewidth(0.5)

            # unit + track header
            unit = _guess_unit(log_name)
            display = (f"{log_name} ({unit})" if ax_idx > 0
                       else f"{log_name} — Predicted  (dashed)")
            ax.set_title(display, fontsize=7.5, color=colour,
                         fontweight="bold", pad=4)

            # depth axis label on first track
            if ax_idx == 0:
                ax.set_ylabel(f"Depth ({self.depth_scale}) m",
                              fontsize=8, color="#374151")

            # x-axis range guard
            finite = vals[np.isfinite(vals)]
            if finite.size >= 2:
                lo, hi = float(np.nanmin(finite)), float(np.nanmax(finite))
                margin = (hi - lo) * 0.08 or 0.5
                if not is_log:
                    ax.set_xlim(lo - margin, hi + margin)

        # legend on first axis
        axes[0].plot([], [], color=_TRACK_COLORS.get("GR", "#22C55E"),
                     lw=lw, label="Actual")
        if self.pred_series is not None:
            axes[0].plot([], [], color=_CLR_PREDICTED,
                         lw=lw, ls="--", label="Predicted")
        axes[0].fill_between([], [], [], color=_CLR_MISSING,
                              alpha=0.35, label="Missing Interval")
        axes[0].legend(fontsize=6.5, loc="lower right",
                        framealpha=0.8, frameon=True)

        fig.suptitle(
            f"Prediction Preview — {self.target}",
            fontsize=9, color="#111827", fontweight="bold", y=0.97,
        )

        plt.close(fig)
        return fig
