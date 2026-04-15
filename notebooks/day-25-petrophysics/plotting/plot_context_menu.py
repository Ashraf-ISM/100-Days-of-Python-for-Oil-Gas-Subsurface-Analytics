"""
Professional Plot Context Menu
===============================
Attach to any matplotlib FigureCanvas to give users a right-click menu
with professional plotting options identical to premium apps like Petrel,
IHS Kingdom, or MATLAB's Figure window.

Usage
-----
    from plotting.plot_context_menu import install_plot_context_menu
    install_plot_context_menu(canvas, fig, parent_widget)
"""
from __future__ import annotations

import io
from typing import Optional

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from PyQt5 import QtCore, QtGui, QtWidgets

# ─────────────────────────────────────────────────────────────────────────────
# Helper: themed menu
# ─────────────────────────────────────────────────────────────────────────────

_MENU_QSS = """
QMenu {
    background: #1C2B3A;
    color: #D6E8F7;
    border: 1px solid #2E4863;
    border-radius: 8px;
    padding: 4px 2px;
    font-size: 12px;
    font-family: 'Segoe UI', 'Inter', sans-serif;
}
QMenu::item {
    padding: 7px 22px 7px 14px;
    border-radius: 5px;
    margin: 1px 4px;
}
QMenu::item:selected {
    background: #2F6FB3;
    color: #FFFFFF;
}
QMenu::separator {
    height: 1px;
    background: #2E4863;
    margin: 4px 8px;
}
QMenu::item:disabled {
    color: #4A6480;
}
"""

_ICON_MAP = {
    "zoom_in":    "🔍",
    "zoom_out":   "🔎",
    "fit":        "⊞",
    "reset":      "↺",
    "pan":        "✥",
    "grid":       "⊞",
    "legend":     "≡",
    "crosshair":  "⊕",
    "stats":      "σ",
    "annotate":   "✎",
    "png":        "🖼",
    "svg":        "📐",
    "pdf":        "📄",
    "copy":       "📋",
    "csv":        "📊",
    "info":       "ℹ",
    "color":      "🎨",
    "style":      "✦",
    "invert":     "⬛",
    "dark":       "🌙",
    "log":        "📈",
    "aspect":     "⤢",
}


def _icon(key: str) -> str:
    return _ICON_MAP.get(key, "•")


# ─────────────────────────────────────────────────────────────────────────────
# Crosshair overlay
# ─────────────────────────────────────────────────────────────────────────────

class _CrosshairManager:
    """Manages a crosshair cursor overlay on a matplotlib figure."""

    def __init__(self, fig: Figure, canvas):
        self._fig = fig
        self._canvas = canvas
        self._active = False
        self._hlines: list = []
        self._vlines: list = []
        self._labels: list = []
        self._cid: Optional[int] = None

    def toggle(self):
        self._active = not self._active
        if self._active:
            self._cid = self._canvas.mpl_connect("motion_notify_event", self._on_move)
        else:
            if self._cid is not None:
                self._canvas.mpl_disconnect(self._cid)
                self._cid = None
            self._clear()
            self._canvas.draw_idle()

    def _clear(self):
        for artist in self._hlines + self._vlines + self._labels:
            try:
                artist.remove()
            except Exception:
                pass
        self._hlines.clear()
        self._vlines.clear()
        self._labels.clear()

    def _on_move(self, event):
        if event.inaxes is None:
            return
        self._clear()
        ax = event.inaxes
        hl = ax.axhline(event.ydata, color="#FF6B35", linewidth=0.9, linestyle="--", alpha=0.8, zorder=99)
        vl = ax.axvline(event.xdata, color="#FF6B35", linewidth=0.9, linestyle="--", alpha=0.8, zorder=99)
        lbl = ax.annotate(
            f"  x={event.xdata:.4g}  y={event.ydata:.4g}",
            xy=(event.xdata, event.ydata),
            fontsize=8,
            color="#FF6B35",
            backgroundcolor="rgba(255,255,255,0.7)",
            zorder=100,
        )
        self._hlines.append(hl)
        self._vlines.append(vl)
        self._labels.append(lbl)
        self._canvas.draw_idle()


# ─────────────────────────────────────────────────────────────────────────────
# Main context menu class
# ─────────────────────────────────────────────────────────────────────────────

class PlotContextMenu(QtCore.QObject):
    """
    Professional right-click context menu for a matplotlib FigureCanvas.

    Attach via:
        PlotContextMenu(canvas, fig, parent_widget)
    """

    def __init__(self, canvas, fig: Figure, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._canvas = canvas
        self._fig = fig
        self._parent = parent
        self._crosshair = _CrosshairManager(fig, canvas)
        self._dark_bg = False
        self._grid_on = True
        self._legend_on = True

        # Install event filter so we catch right-click on the canvas
        canvas.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        canvas.customContextMenuRequested.connect(self._show_menu)

    # ── Public ────────────────────────────────────────────────────────────────

    def _show_menu(self, pos: QtCore.QPoint):
        menu = QtWidgets.QMenu(self._parent)
        menu.setStyleSheet(_MENU_QSS)

        # ── View section ─────────────────────────────────────────────────────
        view_title = QtWidgets.QWidgetAction(menu)
        lbl = QtWidgets.QLabel(f"  📊  Plot Options", menu)
        lbl.setStyleSheet("color:#7DB4D8; font-size:10px; font-weight:700; padding:4px 10px 2px;")
        view_title.setDefaultWidget(lbl)
        menu.addAction(view_title)
        menu.addSeparator()

        act_zoom_in = menu.addAction(f"{_icon('zoom_in')}  Zoom In  (+)")
        act_zoom_in.setShortcut("Ctrl++")
        act_zoom_out = menu.addAction(f"{_icon('zoom_out')}  Zoom Out  (-)")
        act_zoom_out.setShortcut("Ctrl+-")
        act_fit = menu.addAction(f"{_icon('fit')}  Fit to Data")
        act_reset = menu.addAction(f"{_icon('reset')}  Reset View")
        menu.addSeparator()

        # ── Tools section ─────────────────────────────────────────────────────
        act_grid = menu.addAction(f"{_icon('grid')}  Toggle Grid")
        act_grid.setCheckable(True)
        act_grid.setChecked(self._grid_on)

        act_legend = menu.addAction(f"{_icon('legend')}  Toggle Legend")
        act_legend.setCheckable(True)
        act_legend.setChecked(self._legend_on)

        act_crosshair = menu.addAction(f"{_icon('crosshair')}  Crosshair Cursor")
        act_crosshair.setCheckable(True)
        act_crosshair.setChecked(self._crosshair._active)

        act_log_x = menu.addAction(f"{_icon('log')}  Toggle Log Scale X")
        act_log_y = menu.addAction(f"{_icon('log')}  Toggle Log Scale Y")
        act_invert_y = menu.addAction(f"{_icon('invert')}  Invert Y-Axis")
        menu.addSeparator()

        # ── Style section ─────────────────────────────────────────────────────
        style_menu = menu.addMenu(f"{_icon('style')}  Style")
        style_menu.setStyleSheet(_MENU_QSS)
        act_dark = style_menu.addAction(f"{_icon('dark')}  Dark Background")
        act_dark.setCheckable(True)
        act_dark.setChecked(self._dark_bg)
        act_white = style_menu.addAction(f"☀  White Background")
        style_menu.addSeparator()
        act_cmap_viridis = style_menu.addAction("Colormap: Viridis")
        act_cmap_rdbu = style_menu.addAction("Colormap: RdBu")
        act_cmap_plasma = style_menu.addAction("Colormap: Plasma")
        act_cmap_seismic = style_menu.addAction("Colormap: Seismic (Petro)")
        menu.addSeparator()

        # ── Depth/Analysis section ─────────────────────────────────────────────
        analysis_menu = menu.addMenu(f"{_icon('stats')}  Analysis")
        analysis_menu.setStyleSheet(_MENU_QSS)
        act_stats = analysis_menu.addAction(f"{_icon('stats')}  Show Statistics Overlay")
        act_annotate = analysis_menu.addAction(f"{_icon('annotate')}  Add Text Annotation")
        act_hline = analysis_menu.addAction("―  Add Horizontal Line")
        act_vline = analysis_menu.addAction("|  Add Vertical Line")
        menu.addSeparator()

        # ── Export section ─────────────────────────────────────────────────────
        export_menu = menu.addMenu(f"{_icon('png')}  Export / Save")
        export_menu.setStyleSheet(_MENU_QSS)
        act_save_png = export_menu.addAction(f"{_icon('png')}  Save as PNG  (High-DPI)")
        act_save_svg = export_menu.addAction(f"{_icon('svg')}  Save as SVG")
        act_save_pdf = export_menu.addAction(f"{_icon('pdf')}  Save as PDF")
        export_menu.addSeparator()
        act_copy = export_menu.addAction(f"{_icon('copy')}  Copy to Clipboard")
        menu.addSeparator()

        # ── Info ──────────────────────────────────────────────────────────────
        act_info = menu.addAction(f"{_icon('info')}  Plot Information")

        # ── Connect ──────────────────────────────────────────────────────────
        act_zoom_in.triggered.connect(self._zoom_in)
        act_zoom_out.triggered.connect(self._zoom_out)
        act_fit.triggered.connect(self._fit_to_data)
        act_reset.triggered.connect(self._reset_view)
        act_grid.triggered.connect(self._toggle_grid)
        act_legend.triggered.connect(self._toggle_legend)
        act_crosshair.triggered.connect(self._crosshair.toggle)
        act_log_x.triggered.connect(self._toggle_log_x)
        act_log_y.triggered.connect(self._toggle_log_y)
        act_invert_y.triggered.connect(self._invert_y)
        act_dark.triggered.connect(lambda: self._set_dark_bg(True))
        act_white.triggered.connect(lambda: self._set_dark_bg(False))
        act_cmap_viridis.triggered.connect(lambda: self._apply_colormap("viridis"))
        act_cmap_rdbu.triggered.connect(lambda: self._apply_colormap("RdBu"))
        act_cmap_plasma.triggered.connect(lambda: self._apply_colormap("plasma"))
        act_cmap_seismic.triggered.connect(lambda: self._apply_colormap("seismic"))
        act_stats.triggered.connect(self._show_statistics)
        act_annotate.triggered.connect(self._add_annotation)
        act_hline.triggered.connect(self._add_hline)
        act_vline.triggered.connect(self._add_vline)
        act_save_png.triggered.connect(self._save_png)
        act_save_svg.triggered.connect(self._save_svg)
        act_save_pdf.triggered.connect(self._save_pdf)
        act_copy.triggered.connect(self._copy_to_clipboard)
        act_info.triggered.connect(self._show_info)

        # Show at cursor
        global_pos = self._canvas.mapToGlobal(pos)
        menu.exec_(global_pos)

    # ── View actions ─────────────────────────────────────────────────────────

    def _get_axes(self) -> list:
        return [ax for ax in self._fig.get_axes() if not ax.get_label().startswith("cbar")]

    def _zoom_in(self):
        for ax in self._get_axes():
            xmin, xmax = ax.get_xlim()
            ymin, ymax = ax.get_ylim()
            cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
            dx, dy = (xmax - xmin) * 0.35, (ymax - ymin) * 0.35
            ax.set_xlim(cx - dx, cx + dx)
            ax.set_ylim(cy - dy, cy + dy)
        self._canvas.draw_idle()

    def _zoom_out(self):
        for ax in self._get_axes():
            xmin, xmax = ax.get_xlim()
            ymin, ymax = ax.get_ylim()
            cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
            dx, dy = (xmax - xmin) * 0.75, (ymax - ymin) * 0.75
            ax.set_xlim(cx - dx, cx + dx)
            ax.set_ylim(cy - dy, cy + dy)
        self._canvas.draw_idle()

    def _fit_to_data(self):
        for ax in self._get_axes():
            ax.relim()
            ax.autoscale_view()
        self._canvas.draw_idle()

    def _reset_view(self):
        for ax in self._get_axes():
            ax.set_xlim(auto=True)
            ax.set_ylim(auto=True)
            ax.relim()
            ax.autoscale_view()
        self._canvas.draw_idle()

    # ── Tools ──────────────────────────────────────────────────────────────

    def _toggle_grid(self):
        self._grid_on = not self._grid_on
        for ax in self._get_axes():
            ax.grid(self._grid_on, alpha=0.4)
        self._canvas.draw_idle()

    def _toggle_legend(self):
        self._legend_on = not self._legend_on
        for ax in self._get_axes():
            leg = ax.get_legend()
            if leg is not None:
                leg.set_visible(self._legend_on)
            else:
                if self._legend_on:
                    handles, labels = ax.get_legend_handles_labels()
                    if handles:
                        ax.legend(fontsize=8, framealpha=0.85)
        self._canvas.draw_idle()

    def _toggle_log_x(self):
        for ax in self._get_axes():
            cur = ax.get_xscale()
            ax.set_xscale("log" if cur == "linear" else "linear")
        self._canvas.draw_idle()

    def _toggle_log_y(self):
        for ax in self._get_axes():
            cur = ax.get_yscale()
            ax.set_yscale("log" if cur == "linear" else "linear")
        self._canvas.draw_idle()

    def _invert_y(self):
        for ax in self._get_axes():
            ymin, ymax = ax.get_ylim()
            ax.set_ylim(ymax, ymin)
        self._canvas.draw_idle()

    # ── Style ─────────────────────────────────────────────────────────────

    def _set_dark_bg(self, dark: bool):
        self._dark_bg = dark
        bg = "#1A2433" if dark else "#FFFFFF"
        fg = "#D6E8F7" if dark else "#18344F"
        grid_c = "#2E4863" if dark else "#D9E2EC"
        self._fig.patch.set_facecolor(bg)
        for ax in self._get_axes():
            ax.set_facecolor("#0F1C2A" if dark else "#FBFCFE")
            ax.tick_params(colors=fg)
            ax.xaxis.label.set_color(fg)
            ax.yaxis.label.set_color(fg)
            for spine in ax.spines.values():
                spine.set_color("#2E4863" if dark else "#C8D2DC")
            ax.grid(self._grid_on, color=grid_c, alpha=0.4)
        self._canvas.draw_idle()

    def _apply_colormap(self, cmap_name: str):
        for ax in self._get_axes():
            for collection in ax.collections:
                try:
                    collection.set_cmap(cmap_name)
                except Exception:
                    pass
            for img in ax.images:
                img.set_cmap(cmap_name)
        self._canvas.draw_idle()

    # ── Analysis ──────────────────────────────────────────────────────────

    def _show_statistics(self):
        lines: list[str] = []
        for ax in self._get_axes():
            for line in ax.get_lines():
                ydata = line.get_ydata()
                ydata = ydata[np.isfinite(ydata)] if len(ydata) > 0 else ydata
                if len(ydata) == 0:
                    continue
                lbl = line.get_label() or "Line"
                lines.append(
                    f"<b>{lbl}</b><br>"
                    f"N={len(ydata):,}  Min={ydata.min():.4g}  "
                    f"Max={ydata.max():.4g}  Mean={ydata.mean():.4g}  "
                    f"σ={ydata.std():.4g}"
                )
        if not lines:
            lines = ["No line data found on current axes."]
        msg = QtWidgets.QMessageBox(self._parent)
        msg.setWindowTitle("Plot Statistics")
        msg.setText("<br><br>".join(lines))
        msg.setTextFormat(QtCore.Qt.RichText)
        msg.setStyleSheet(
            "QMessageBox { background:#1C2B3A; color:#D6E8F7; font-size:12px; }"
            "QPushButton { background:#2F6FB3; color:white; border-radius:6px; padding:6px 18px; }"
        )
        msg.exec_()

    def _add_annotation(self):
        text, ok = QtWidgets.QInputDialog.getText(
            self._parent, "Add Annotation", "Enter annotation text:"
        )
        if not ok or not text.strip():
            return
        axes = self._get_axes()
        if not axes:
            return
        ax = axes[0]
        xmid = sum(ax.get_xlim()) / 2
        ymid = sum(ax.get_ylim()) / 2
        ax.annotate(
            text,
            xy=(xmid, ymid),
            fontsize=10,
            color="#FF6B35",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#FF6B35", alpha=0.85),
            ha="center",
            va="center",
            zorder=100,
        )
        self._canvas.draw_idle()

    def _add_hline(self):
        val, ok = QtWidgets.QInputDialog.getDouble(
            self._parent, "Horizontal Line", "Y value:", decimals=4
        )
        if not ok:
            return
        for ax in self._get_axes():
            ax.axhline(val, color="#FF6B35", linewidth=1.3, linestyle="--", alpha=0.85, zorder=90)
        self._canvas.draw_idle()

    def _add_vline(self):
        val, ok = QtWidgets.QInputDialog.getDouble(
            self._parent, "Vertical Line", "X value:", decimals=4
        )
        if not ok:
            return
        for ax in self._get_axes():
            ax.axvline(val, color="#2F6FB3", linewidth=1.3, linestyle="--", alpha=0.85, zorder=90)
        self._canvas.draw_idle()

    # ── Export ─────────────────────────────────────────────────────────────

    def _export_dialog(self, ext: str, desc: str) -> Optional[str]:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self._parent, f"Export Plot as {ext.upper()}",
            f"plot.{ext}", f"{desc} (*.{ext})"
        )
        return path or None

    def _save_png(self):
        path = self._export_dialog("png", "PNG Image")
        if path:
            self._fig.savefig(path, dpi=300, bbox_inches="tight", facecolor=self._fig.get_facecolor())
            QtWidgets.QMessageBox.information(self._parent, "Saved", f"Plot saved to:\n{path}")

    def _save_svg(self):
        path = self._export_dialog("svg", "SVG Vector Image")
        if path:
            self._fig.savefig(path, format="svg", bbox_inches="tight")
            QtWidgets.QMessageBox.information(self._parent, "Saved", f"Plot saved to:\n{path}")

    def _save_pdf(self):
        path = self._export_dialog("pdf", "PDF Document")
        if path:
            self._fig.savefig(path, format="pdf", bbox_inches="tight")
            QtWidgets.QMessageBox.information(self._parent, "Saved", f"Plot saved to:\n{path}")

    def _copy_to_clipboard(self):
        buf = io.BytesIO()
        self._fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        buf.seek(0)
        image = QtGui.QImage()
        image.loadFromData(buf.read(), "PNG")
        QtWidgets.QApplication.clipboard().setImage(image)
        QtWidgets.QMessageBox.information(self._parent, "Copied", "Plot copied to clipboard (PNG).")

    # ── Info ──────────────────────────────────────────────────────────────

    def _show_info(self):
        lines: list[str] = []
        for i, ax in enumerate(self._get_axes()):
            title = ax.get_title() or f"Axes {i+1}"
            xlabel = ax.get_xlabel() or "—"
            ylabel = ax.get_ylabel() or "—"
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            n_lines = len(ax.get_lines())
            n_coll = len(ax.collections)
            lines.append(
                f"<b>{title}</b>  |  X: {xlabel}  Y: {ylabel}<br>"
                f"X range: [{xlim[0]:.4g}, {xlim[1]:.4g}]  "
                f"Y range: [{ylim[0]:.4g}, {ylim[1]:.4g}]<br>"
                f"Lines: {n_lines}   Collections: {n_coll}"
            )
        if not lines:
            lines = ["No axes found."]
        msg = QtWidgets.QMessageBox(self._parent)
        msg.setWindowTitle("Plot Information")
        msg.setText("<br><br>".join(lines))
        msg.setTextFormat(QtCore.Qt.RichText)
        msg.setStyleSheet(
            "QMessageBox { background:#1C2B3A; color:#D6E8F7; font-size:12px; }"
            "QPushButton { background:#2F6FB3; color:white; border-radius:6px; padding:6px 18px; }"
        )
        msg.exec_()


# ─────────────────────────────────────────────────────────────────────────────
# Convenience installer
# ─────────────────────────────────────────────────────────────────────────────

def install_plot_context_menu(
    canvas,
    fig: Figure,
    parent: Optional[QtWidgets.QWidget] = None,
) -> PlotContextMenu:
    """
    Attach a professional right-click context menu to *canvas*.

    Returns the PlotContextMenu instance (keep a reference to prevent GC).
    """
    ctx = PlotContextMenu(canvas, fig, parent)
    # Store reference on canvas to avoid garbage collection
    if not hasattr(canvas, "_plot_context_menus"):
        canvas._plot_context_menus = []
    canvas._plot_context_menus.append(ctx)
    return ctx
