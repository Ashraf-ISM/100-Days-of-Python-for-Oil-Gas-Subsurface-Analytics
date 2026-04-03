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

    # ── generic plots ──────────────────────────────────────────────────────

    def _depth_mask(self, depth: np.ndarray,
                    depth_from: float | None,
                    depth_to: float | None) -> np.ndarray:
        if depth_from is None:
            depth_from = float(depth.min()) if len(depth) else 0.0
        if depth_to is None:
            depth_to = float(depth.max()) if len(depth) else 0.0
        return (depth >= depth_from) & (depth <= depth_to)

    def _get_curve_data(self, well: WellData, name: str,
                        depth_from: float | None,
                        depth_to: float | None) -> np.ndarray:
        curve = well.get_curve(name)
        if curve is None or len(curve.data) == 0:
            return np.array([])
        mask = self._depth_mask(well.depth, depth_from, depth_to)
        return curve.data[mask]

    def _plot_empty(self, title: str, subtitle: str = "No data"):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_facecolor("#FFFFFF")
        ax.axis("off")
        ax.text(0.5, 0.6, title, ha="center", va="center",
                fontsize=11, color="#1E293B")
        ax.text(0.5, 0.45, subtitle, ha="center", va="center",
                fontsize=9, color="#94A3B8")
        self.draw()

    def plot_histogram(self, well: WellData, curve_name: str,
                       depth_from: float | None = None,
                       depth_to: float | None = None):
        data = self._get_curve_data(well, curve_name, depth_from, depth_to)
        data = data[np.isfinite(data)]
        if len(data) == 0:
            self._plot_empty("Histogram", f"No data for {curve_name}")
            return
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.hist(data, bins=40, color="#3B82F6", alpha=0.8, edgecolor="#1E293B")
        ax.set_title(f"Histogram: {curve_name}", fontsize=10, color="#1E293B")
        ax.set_xlabel(curve_name, fontsize=8)
        ax.set_ylabel("Count", fontsize=8)
        ax.grid(True, color="#E2E8F0", linewidth=0.5, linestyle=":")
        self.draw()

    def plot_box(self, well: WellData, curve_name: str,
                 depth_from: float | None = None,
                 depth_to: float | None = None):
        data = self._get_curve_data(well, curve_name, depth_from, depth_to)
        data = data[np.isfinite(data)]
        if len(data) == 0:
            self._plot_empty("Box Plot", f"No data for {curve_name}")
            return
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.boxplot(data, vert=True, patch_artist=True,
                   boxprops=dict(facecolor="#22C55E", alpha=0.7, color="#166534"),
                   medianprops=dict(color="#0F172A"))
        ax.set_title(f"Box Plot: {curve_name}", fontsize=10, color="#1E293B")
        ax.set_ylabel(curve_name, fontsize=8)
        ax.grid(True, axis="y", color="#E2E8F0", linewidth=0.5, linestyle=":")
        self.draw()

    def plot_cross(self, well: WellData, x_name: str, y_name: str,
                   depth_from: float | None = None,
                   depth_to: float | None = None):
        x = self._get_curve_data(well, x_name, depth_from, depth_to)
        y = self._get_curve_data(well, y_name, depth_from, depth_to)
        if len(x) == 0 or len(y) == 0:
            self._plot_empty("Cross Plot", f"Missing {x_name} or {y_name}")
            return
        mask = np.isfinite(x) & np.isfinite(y)
        x = x[mask]
        y = y[mask]
        if len(x) == 0:
            self._plot_empty("Cross Plot", "No valid samples")
            return
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.scatter(x, y, s=6, c="#EF4444", alpha=0.6, edgecolors="none")
        ax.set_title(f"Cross Plot: {x_name} vs {y_name}", fontsize=10, color="#1E293B")
        ax.set_xlabel(x_name, fontsize=8)
        ax.set_ylabel(y_name, fontsize=8)
        ax.grid(True, color="#E2E8F0", linewidth=0.5, linestyle=":")
        self.draw()

    def plot_pair(self, well: WellData, curve_names: List[str],
                  depth_from: float | None = None,
                  depth_to: float | None = None):
        names = [n for n in curve_names if n]
        names = list(dict.fromkeys(names))  # unique, preserve order
        if len(names) < 2:
            self._plot_empty("Pair Plot", "Select at least two curves")
            return
        names = names[:4]  # keep it compact
        data = []
        for n in names:
            d = self._get_curve_data(well, n, depth_from, depth_to)
            data.append(d)

        self.fig.clear()
        n = len(names)
        gs = self.fig.add_gridspec(n, n, wspace=0.15, hspace=0.15)
        for i in range(n):
            for j in range(n):
                ax = self.fig.add_subplot(gs[i, j])
                ax.tick_params(labelsize=6)
                if i == j:
                    d = data[i]
                    d = d[np.isfinite(d)]
                    if len(d):
                        ax.hist(d, bins=25, color="#60A5FA", alpha=0.8)
                else:
                    x = data[j]
                    y = data[i]
                    mask = np.isfinite(x) & np.isfinite(y)
                    ax.scatter(x[mask], y[mask], s=4, c="#64748B", alpha=0.5, edgecolors="none")
                if i == n - 1:
                    ax.set_xlabel(names[j], fontsize=7)
                else:
                    ax.set_xticklabels([])
                if j == 0:
                    ax.set_ylabel(names[i], fontsize=7)
                else:
                    ax.set_yticklabels([])
        self.fig.suptitle("Pair Plot", fontsize=10, color="#1E293B", y=0.98)
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

    def plot_mode(self, well: WellData, mode: str,
                  curves: List[str],
                  depth_from: float = None,
                  depth_to: float = None):
        mode = (mode or "").lower()
        curves = [c for c in curves if c]

        if "hist" in mode:
            if curves:
                self.canvas.plot_histogram(well, curves[0], depth_from, depth_to)
            else:
                self.canvas._plot_empty("Histogram", "Select a curve")
            return

        if "box" in mode:
            if curves:
                self.canvas.plot_box(well, curves[0], depth_from, depth_to)
            else:
                self.canvas._plot_empty("Box Plot", "Select a curve")
            return

        if "cross" in mode:
            if len(curves) >= 2:
                self.canvas.plot_cross(well, curves[0], curves[1], depth_from, depth_to)
            else:
                self.canvas._plot_empty("Cross Plot", "Select X and Y curves")
            return

        if "pair" in mode:
            self.canvas.plot_pair(well, curves, depth_from, depth_to)
            return

        if "triple" in mode:
            if not curves:
                self.canvas._plot_empty("Triple Combo", "Select three curves")
                return
            tracks = [
                TrackConfig(curves[i], [{"name": curves[i], "color": "#2563EB", "lw": 1.1}])
                for i in range(min(3, len(curves)))
            ]
            self.canvas.plot_well(well, tracks, depth_from, depth_to, tops=None)
            return

        # Default: Multi-track plot with selected curves
        if curves:
            tracks = [
                TrackConfig(c, [{"name": c, "color": "#2563EB", "lw": 1.1}])
                for c in curves
            ]
            self.canvas.plot_well(well, tracks, depth_from, depth_to, tops=None)
        else:
            self.canvas.plot_well(well, None, depth_from, depth_to, tops=None)
