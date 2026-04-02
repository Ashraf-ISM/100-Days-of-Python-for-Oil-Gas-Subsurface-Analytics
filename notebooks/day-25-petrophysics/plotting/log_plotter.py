"""
plotting/log_plotter.py
=======================
Multi-track well-log display using Matplotlib embedded in a PyQt5 widget.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional

import numpy as np
import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSizePolicy

from core.data_model import WellData


# ── Track configuration dataclass ─────────────────────────────────────────────

class TrackConfig:
    def __init__(self, title: str = "Track",
                 curves: Optional[List[dict]] = None,
                 width_ratio: float = 1.0,
                 scale: str = "linear",
                 depth_grid: bool = True):
        self.title = title
        self.curves: List[dict] = curves or []    # [{"name": "GR", "color": "green", ...}]
        self.width_ratio = width_ratio
        self.scale = scale        # "linear" | "log"
        self.depth_grid = depth_grid


# ── Default track layout for a standard well ──────────────────────────────────

DEFAULT_TRACKS: List[TrackConfig] = [
    TrackConfig("GR / SP", [
        {"name": "GR",   "color": "#2ecc71", "lw": 1.2, "label": "GR (GAPI)"},
        {"name": "SP",   "color": "#f39c12", "lw": 1.0, "label": "SP (mV)", "ls": "--"},
    ]),
    TrackConfig("Resistivity", [
        {"name": "RT",   "color": "#e74c3c", "lw": 1.2, "label": "Rt (Ω·m)"},
        {"name": "RXO",  "color": "#c0392b", "lw": 0.8, "label": "Rxo (Ω·m)", "ls": "--"},
    ], scale="log"),
    TrackConfig("N-D Porosity", [
        {"name": "NPHI", "color": "#3498db", "lw": 1.2, "label": "NPHI (v/v)"},
        {"name": "RHOB", "color": "#e74c3c", "lw": 1.2, "label": "RHOB (g/cc)"},
    ]),
    TrackConfig("Vshale / Porosity", [
        {"name": "VSH",  "color": "#7f8c8d", "lw": 1.0, "label": "Vshale"},
        {"name": "PHIE", "color": "#27ae60", "lw": 1.2, "label": "PHIE (v/v)"},
    ]),
    TrackConfig("Sw / Permeability", [
        {"name": "SW",   "color": "#2980b9", "lw": 1.2, "label": "Sw"},
        {"name": "PERM", "color": "#8e44ad", "lw": 1.0, "label": "K (mD)", "ls": "-."},
    ], scale="log"),
]


class LogCanvas(FigureCanvas):
    """Matplotlib canvas for multi-track log display."""

    def __init__(self, parent: Optional[QWidget] = None, dpi: int = 96):
        n_tracks = 5
        widths = [1] + [tc.width_ratio for tc in DEFAULT_TRACKS]
        self.fig = Figure(figsize=(14, 10), dpi=dpi, facecolor="#F8FAFC")
        super().__init__(self.fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.updateGeometry()
        self._axes: List[plt.Axes] = []

    # ── public API ────────────────────────────────────────────────────────────

    def plot_well(self, well: WellData,
                  tracks: Optional[List[TrackConfig]] = None,
                  depth_from: float = None,
                  depth_to: float = None,
                  tops: Optional[List] = None):
        """
        Draw the well log.  Each TrackConfig maps to one subplot column.
        The leftmost column is the depth track.
        """
        tracks = tracks or DEFAULT_TRACKS
        self.fig.clear()

        depth = well.depth
        if depth_from is None:
            depth_from = float(depth.min())
        if depth_to is None:
            depth_to = float(depth.max())

        mask = (depth >= depth_from) & (depth <= depth_to)
        depth_disp = depth[mask]

        n = len(tracks) + 1  # +1 for depth track
        widths = [0.4] + [tc.width_ratio for tc in tracks]
        gs = self.fig.add_gridspec(1, n, width_ratios=widths,
                                   wspace=0.05, left=0.04, right=0.98,
                                   top=0.93, bottom=0.05)

        # ── Depth track ───────────────────────────────────────────────────────
        ax_depth = self.fig.add_subplot(gs[0, 0])
        ax_depth.set_ylim(depth_to, depth_from)
        ax_depth.yaxis.set_major_locator(plt.MultipleLocator(50))
        ax_depth.yaxis.set_minor_locator(plt.MultipleLocator(10))
        ax_depth.tick_params(axis="y", labelsize=7, colors="#475569")
        ax_depth.tick_params(axis="x", bottom=False, labelbottom=False)
        ax_depth.set_ylabel(f"Depth ({well.depth_unit})", fontsize=8, color="#475569")
        ax_depth.set_facecolor("#F8FAFC")
        ax_depth.grid(True, axis="y", color="#E2E8F0", linewidth=0.5)
        ax_depth.set_title("DEPTH", fontsize=7, color="#475569", pad=4)
        self._axes = [ax_depth]

        # ── Curve tracks ─────────────────────────────────────────────────────
        for i, tc in enumerate(tracks):
            ax = self.fig.add_subplot(gs[0, i + 1], sharey=ax_depth)
            ax.set_facecolor("#FFFFFF")
            ax.tick_params(axis="y", left=False, labelleft=False)
            ax.tick_params(axis="x", labelsize=6, colors="#475569")
            ax.set_title(tc.title, fontsize=8, color="#1E293B", pad=4)
            ax.grid(True, color="#E2E8F0", linewidth=0.4, linestyle=":")
            ax.set_ylim(depth_to, depth_from)

            plotted = False
            for cfg in tc.curves:
                cname = cfg["name"]
                curve = well.get_curve(cname)
                if curve is None or len(curve.data) == 0:
                    continue
                cdata = curve.data[mask]
                color = cfg.get("color", "#2563EB")
                lw    = cfg.get("lw", 1.0)
                ls    = cfg.get("ls", "-")
                label = cfg.get("label", cname)
                ax.plot(cdata, depth_disp,
                        color=color, lw=lw, linestyle=ls, label=label)
                plotted = True

            if tc.scale == "log":
                try:
                    ax.set_xscale("log")
                except Exception:
                    pass

            if plotted:
                ax.legend(loc="upper right", fontsize=5, framealpha=0.7)
            else:
                ax.text(0.5, 0.5, "No data", transform=ax.transAxes,
                        ha="center", va="center", color="#94A3B8", fontsize=8)

            # Formation tops
            if tops:
                for top in tops:
                    if depth_from <= top.depth <= depth_to:
                        ax.axhline(top.depth, color=top.color, lw=0.8, ls="--")
                        ax.text(ax.get_xlim()[1], top.depth, f"  {top.name}",
                                va="center", fontsize=6, color=top.color)

            self._axes.append(ax)

        self.fig.suptitle(f"Well: {well.name}  |  {depth_from:.0f}–{depth_to:.0f} {well.depth_unit}",
                          fontsize=9, color="#1E293B", y=0.97)
        self.draw()


class LogPlotWidget(QWidget):
    """Drop-in QWidget containing the log canvas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.canvas = LogCanvas(self)
        layout.addWidget(self.canvas)

    def plot(self, well: WellData,
             tracks: Optional[List[TrackConfig]] = None,
             depth_from: float = None,
             depth_to: float = None,
             tops=None):
        self.canvas.plot_well(well, tracks, depth_from, depth_to, tops)