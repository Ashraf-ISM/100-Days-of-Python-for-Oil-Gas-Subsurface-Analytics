from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Any

from PyQt5 import QtCore, QtGui, QtWidgets, uic

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
UI_DIR = ROOT_DIR / "ui"
UI_FILE = "advance_crossplot_widget.ui" 

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from plotting.plot_context_menu import install_plot_context_menu  # noqa: E402 


class AdvancedCrossplotWindow(QtWidgets.QMainWindow):
    """Standalone advanced crossplot workspace."""

    _TEMPLATE_INFO = {
        "Density - Neutron": (
            "Density-neutron crossplot is useful for lithology screening and gas effect "
            "checks. The template pre-selects neutron and density style curves when they "
            "exist in the active well."
        ),
        "Pickett Plot": (
            "Pickett plots compare porosity and resistivity, typically on log scales, to "
            "support water saturation interpretation and Archie trend review."
        ),
        "M-N Plot": (
            "M-N plotting usually relies on neutron, density, and sonic responses. This "
            "workspace applies a recommended curve preset, then lets you tune the final "
            "X and Y curves directly."
        ),
        "Buckles Plot": (
            "Buckles plots compare porosity and water saturation to highlight irreducible "
            "water trends and reservoir quality behaviour."
        ),
        "Generic Crossplot": (
            "Generic crossplot mode lets you mix any available well-log curves with the "
            "same advanced display, export, and toolbar controls."
        ),
    }

    _TEMPLATE_PRESETS = {
        "Density - Neutron": {
            "x": ("NPHI", "TNPH", "CNCF", "PHIN"),
            "y": ("RHOB", "DEN", "ZDEN", "RHOZ"),
            "color": ("GR", "CALI", "PHIE", "Vcl", "VSH"),
            "invert_x": True,
            "invert_y": True,
            "log_x": False,
            "log_y": False,
        },
        "Pickett Plot": {
            "x": ("PHIE", "PHIT", "NPHI", "PHI"),
            "y": ("RT", "ILD", "RESD", "AT90", "LLD", "RDEP"),
            "color": ("SW", "Sw", "Vcl", "GR"),
            "invert_x": False,
            "invert_y": False,
            "log_x": True,
            "log_y": True,
        },
        "M-N Plot": {
            "x": ("NPHI", "TNPH", "PHIE", "DT"),
            "y": ("RHOB", "DEN", "ZDEN", "DT"),
            "color": ("GR", "PE", "PEF", "CALI"),
            "invert_x": False,
            "invert_y": False,
            "log_x": False,
            "log_y": False,
        },
        "Buckles Plot": {
            "x": ("PHIE", "PHIT", "NPHI", "PHI"),
            "y": ("SW", "Sw", "SWT", "BVW"),
            "color": ("PERM", "KLOGH", "GR", "Vcl"),
            "invert_x": False,
            "invert_y": False,
            "log_x": False,
            "log_y": False,
        },
        "Generic Crossplot": {
            "x": (),
            "y": (),
            "color": ("GR", "PHIE", "RHOB", "NPHI"),
            "invert_x": False,
            "invert_y": False,
            "log_x": False,
            "log_y": False,
        },
    }

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._well: Any | None = None
        self._df = None
        self._log_info: dict[str, dict[str, Any]] = {}
        self._plot_df = None
        self._figure = None
        self._canvas = None
        self._nav_toolbar = None
        self._mpl_connect_id: int | None = None
        self._updating_controls = False

        self._build_ui()
        self._wire_controls()
        self._apply_window_chrome()
        self._reset_plot_state("Load a well in the main window to start advanced crossplotting.")

    def set_well_context(self, well: Any | None) -> None:
        self._well = well
        self._df = getattr(well, "data", None) if well is not None else None
        self._log_info = getattr(well, "log_info", {}) or {}

        if self._df is None or getattr(self._df, "empty", True):
            self._populate_curve_combos([])
            self._set_stats_rows([])
            self._reset_plot_state("The selected well does not contain plottable curve data.")
            self.statusBar().showMessage("No active well data available.", 5000)
            self._update_window_title()
            return

        curves = [
            str(column)
            for column in self._df.columns
            if str(column).strip() and str(column).upper() != "DEPTH"
        ]
        if len(curves) < 2:
            self._populate_curve_combos(curves)
            self._set_stats_rows([])
            self._reset_plot_state("At least two non-depth curves are required for a crossplot.")
            self._update_window_title()
            return
        self._populate_curve_combos(curves)
        self._apply_template(self._current_template_name(), preserve_existing=False)
        self._update_window_title()
        self._update_title()
        self._update_status_bar()

    def plot_current_crossplot(self) -> None:
        if self._df is None or getattr(self._df, "empty", True):
            self._reset_plot_state("Load a well with valid data before plotting.")
            return

        x_curve = self._combo_text("cboXCurve")
        y_curve = self._combo_text("cboYCurve")
        color_curve = self._combo_text("cboColorBy")
        if color_curve == "None":
            color_curve = None

        if not x_curve or x_curve not in self._df.columns:
            self._reset_plot_state("Choose a valid X curve from the loaded well.")
            return
        if not y_curve or y_curve not in self._df.columns:
            self._reset_plot_state("Choose a valid Y curve from the loaded well.")
            return

        try:
            import numpy as np
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
        except Exception as exc:
            self._reset_plot_state(f"Matplotlib dependencies are unavailable: {exc}")
            return

        plot_df = self._df[[x_curve, y_curve]].copy()
        if color_curve and color_curve in self._df.columns:
            plot_df[color_curve] = self._df[color_curve]

        plot_df = plot_df.replace([np.inf, -np.inf], np.nan).dropna(subset=[x_curve, y_curve])
        if color_curve and color_curve in plot_df.columns:
            plot_df = plot_df.dropna(subset=[color_curve])

        if plot_df.empty:
            self._reset_plot_state("No valid samples were found for the selected curves.")
            return

        x_values = plot_df[x_curve].to_numpy()
        y_values = plot_df[y_curve].to_numpy()

        fig, ax = plt.subplots(figsize=(9.2, 6.8), constrained_layout=True)
        fig.patch.set_facecolor("#FFFFFF")
        ax.set_facecolor("#FBFDFF")

        if self._is_hexbin_mode():
            hexbin = ax.hexbin(
                x_values,
                y_values,
                gridsize=38,
                mincnt=1,
                cmap="viridis",
                linewidths=0.0,
            )
            cbar = fig.colorbar(hexbin, ax=ax, pad=0.02)
            cbar.set_label("Point Density", fontsize=9)
        elif color_curve and color_curve in plot_df.columns:
            scatter = ax.scatter(
                x_values,
                y_values,
                c=plot_df[color_curve].to_numpy(),
                cmap="viridis",
                s=22,
                alpha=0.80,
                edgecolors="white",
                linewidths=0.30,
            )
            cbar = fig.colorbar(scatter, ax=ax, pad=0.02)
            cbar.set_label(self._axis_label(color_curve, self._combo_text("cboColorUnit")), fontsize=9)
        else:
            ax.scatter(
                x_values,
                y_values,
                s=22,
                alpha=0.78,
                color="#1A56DB",
                edgecolors="white",
                linewidths=0.30,
            )

        if self._workspace.chkLithologyTemplates.isChecked():
            self._draw_reference_overlays(ax, plot_df, x_curve, y_curve)

        if self._workspace.chkStatisticsBox.isChecked():
            self._draw_stats_box(ax, plot_df, x_curve, y_curve)

        ax.set_xlabel(self._axis_label(x_curve, self._combo_text("cboXUnit")))
        ax.set_ylabel(self._axis_label(y_curve, self._combo_text("cboYUnit")))
        ax.set_title(self._build_plot_title(), fontsize=11, fontweight="bold", color="#1A2340")
        ax.grid(self._workspace.chkGrid.isChecked(), color="#D8E2EE", linewidth=0.8, alpha=0.9)

        if self._workspace.chkLogX.isChecked():
            if (x_values > 0).all():
                ax.set_xscale("log")
        if self._workspace.chkLogY.isChecked():
            if (y_values > 0).all():
                ax.set_yscale("log")
        if self._workspace.chkInvertX.isChecked():
            ax.invert_xaxis()
        if self._workspace.chkInvertY.isChecked():
            ax.invert_yaxis()

        for spine in ax.spines.values():
            spine.set_color("#CBD5E1")

        canvas_host = self._workspace.plotFrame
        canvas_layout = self._workspace.canvasInnerLayout
        while canvas_layout.count():
            item = canvas_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        self._figure = fig
        self._plot_df = plot_df
        self._canvas = FigureCanvas(fig)
        self._canvas.setStyleSheet("background:#FFFFFF;")
        self._nav_toolbar = NavigationToolbar(self._canvas, self)
        self._nav_toolbar.hide()
        canvas_layout.addWidget(self._canvas)
        self._canvas.draw_idle()
        install_plot_context_menu(self._canvas, fig, canvas_host)

        self._connect_canvas_events()
        self._update_title()
        self._update_status_bar(point_count=len(plot_df))
        self._update_stats_table(plot_df, x_curve, y_curve)

    def show_with_well(self, well: Any | None) -> None:
        self.set_well_context(well)
        self.show()
        self.raise_()
        self.activateWindow()

    def _build_ui(self) -> None:
        ui_path = UI_DIR / UI_FILE
        self._workspace = uic.loadUi(str(ui_path))
        self.setCentralWidget(self._workspace)

    def _wire_controls(self) -> None:
        workspace = self._workspace

        workspace.btnPlotCrossplot.clicked.connect(self.plot_current_crossplot)
        workspace.cboCrossplotType.currentTextChanged.connect(self._on_template_changed)
        workspace.listTemplates.currentRowChanged.connect(self._on_template_row_changed)

        for widget_name in ("cboXCurve", "cboYCurve", "cboColorBy"):
            getattr(workspace, widget_name).currentTextChanged.connect(self._on_curve_changed)

        workspace.plot_style_for_cross_plot_comboBox.currentTextChanged.connect(self._update_title)

        workspace.btnHome.clicked.connect(lambda: self._toolbar_action("home"))
        workspace.btnBack.clicked.connect(lambda: self._toolbar_action("back"))
        workspace.btnForward.clicked.connect(lambda: self._toolbar_action("forward"))
        workspace.btnPan.clicked.connect(lambda: self._toolbar_action("pan"))
        workspace.btnZoom.clicked.connect(lambda: self._toolbar_action("zoom"))
        workspace.btnSubplots.clicked.connect(lambda: self._toolbar_action("configure_subplots"))
        workspace.btnSaveFig.clicked.connect(self.export_current_figure)
        workspace.btnCopyFig.clicked.connect(self.copy_current_figure_to_clipboard)

        workspace.btnExportPNG.clicked.connect(lambda: self.export_current_figure("png"))
        workspace.btnExportPDF.clicked.connect(lambda: self.export_current_figure("pdf"))
        workspace.btnExportSVG.clicked.connect(lambda: self.export_current_figure("svg"))
        workspace.btnExportCSV.clicked.connect(self.export_current_data)

    def _apply_window_chrome(self) -> None:
        self.setMinimumSize(1180, 760)
        self.resize(1420, 860)
        self._update_window_title()
        self.statusBar().showMessage("Ready")

    def _populate_curve_combos(self, curves: list[str]) -> None:
        self._updating_controls = True
        try:
            for combo_name in ("cboXCurve", "cboYCurve", "cboColorBy"):
                combo = getattr(self._workspace, combo_name)
                current_text = combo.currentText().strip()
                combo.blockSignals(True)
                combo.clear()
                if combo_name == "cboColorBy":
                    combo.addItem("None")
                combo.addItems(curves)
                if current_text:
                    index = combo.findText(current_text)
                    if index >= 0:
                        combo.setCurrentIndex(index)
                combo.blockSignals(False)
        finally:
            self._updating_controls = False

    def _on_template_changed(self, template_name: str) -> None:
        if self._updating_controls:
            return
        self._sync_template_list(template_name)
        self._apply_template(template_name, preserve_existing=False)
        self._update_title()

    def _on_template_row_changed(self, row: int) -> None:
        if row < 0 or row >= self._workspace.cboCrossplotType.count():
            return
        if self._workspace.cboCrossplotType.currentIndex() == row:
            return
        self._workspace.cboCrossplotType.setCurrentIndex(row)

    def _on_curve_changed(self, _text: str) -> None:
        if self._updating_controls:
            return
        self._sync_units()
        self._update_title()

    def _apply_template(self, template_name: str, *, preserve_existing: bool) -> None:
        preset = self._TEMPLATE_PRESETS.get(template_name, self._TEMPLATE_PRESETS["Generic Crossplot"])
        curves = [
            str(column)
            for column in getattr(self._df, "columns", [])
            if str(column).upper() != "DEPTH"
        ]

        self._updating_controls = True
        try:
            if not preserve_existing or not self._combo_text("cboXCurve"):
                self._set_combo_to_best_match(self._workspace.cboXCurve, preset["x"], curves)
            if not preserve_existing or not self._combo_text("cboYCurve"):
                self._set_combo_to_best_match(self._workspace.cboYCurve, preset["y"], curves)
            if not preserve_existing or self._combo_text("cboColorBy") in {"", "None"}:
                self._set_combo_to_best_match(self._workspace.cboColorBy, preset["color"], curves, allow_none=True)

            self._workspace.chkInvertX.setChecked(bool(preset["invert_x"]))
            self._workspace.chkInvertY.setChecked(bool(preset["invert_y"]))
            self._workspace.chkLogX.setChecked(bool(preset["log_x"]))
            self._workspace.chkLogY.setChecked(bool(preset["log_y"]))
        finally:
            self._updating_controls = False

        self._sync_units()
        self._update_quick_info(template_name)

    def _sync_template_list(self, template_name: str) -> None:
        index = self._workspace.cboCrossplotType.findText(template_name)
        if index >= 0:
            self._workspace.listTemplates.blockSignals(True)
            self._workspace.listTemplates.setCurrentRow(index)
            self._workspace.listTemplates.blockSignals(False)

    def _sync_units(self) -> None:
        self._set_unit_combo(self._workspace.cboXUnit, self._combo_text("cboXCurve"))
        self._set_unit_combo(self._workspace.cboYUnit, self._combo_text("cboYCurve"))
        color_curve = self._combo_text("cboColorBy")
        self._set_unit_combo(self._workspace.cboColorUnit, None if color_curve == "None" else color_curve)

    def _set_unit_combo(self, combo: QtWidgets.QComboBox, curve_name: str | None) -> None:
        unit = self._curve_unit(curve_name)
        if not unit:
            return
        index = combo.findText(unit)
        if index < 0:
            combo.insertItem(0, unit)
            index = 0
        combo.setCurrentIndex(index)

    def _curve_unit(self, curve_name: str | None) -> str:
        if not curve_name:
            return ""
        info = self._log_info.get(curve_name, {})
        return str(info.get("unit", "") or "").strip()

    def _set_combo_to_best_match(
        self,
        combo: QtWidgets.QComboBox,
        preferred_names: tuple[str, ...],
        curves: list[str],
        *,
        allow_none: bool = False,
    ) -> None:
        for preferred in preferred_names:
            index = combo.findText(preferred)
            if index >= 0:
                combo.setCurrentIndex(index)
                return

        if allow_none:
            none_index = combo.findText("None")
            if none_index >= 0:
                combo.setCurrentIndex(none_index)
                return

        for curve_name in curves:
            index = combo.findText(str(curve_name))
            if index >= 0:
                combo.setCurrentIndex(index)
                return

    def _draw_reference_overlays(self, ax, plot_df, x_curve: str, y_curve: str) -> None:
        x_name = x_curve.upper()
        y_name = y_curve.upper()
        if "NPHI" not in x_name and x_name not in {"TNPH", "CNCF", "PHIN"}:
            return
        if "RHOB" not in y_name and y_name not in {"DEN", "ZDEN", "RHOZ"}:
            return

        import numpy as np

        neutron = np.linspace(-0.05, 0.45, 40)
        sandstone = 2.65 - 0.75 * neutron
        limestone = 2.71 - 0.55 * neutron
        dolomite = 2.87 - 0.45 * neutron

        ax.plot(neutron, sandstone, color="#C2410C", linewidth=1.3, label="Sandstone")
        ax.plot(neutron, limestone, color="#0F766E", linewidth=1.3, label="Limestone")
        ax.plot(neutron, dolomite, color="#7C3AED", linewidth=1.3, label="Dolomite")

        if self._workspace.chkGasEffectZone.isChecked():
            gas_upper = sandstone - 0.10
            gas_lower = sandstone - 0.26
            ax.fill_between(
                neutron,
                gas_lower,
                gas_upper,
                color="#F59E0B",
                alpha=0.15,
                label="Gas Effect Zone",
            )

        ax.legend(loc="best", fontsize=8, frameon=True)

    def _draw_stats_box(self, ax, plot_df, x_curve: str, y_curve: str) -> None:
        x_values = plot_df[x_curve]
        y_values = plot_df[y_curve]
        stats_text = "\n".join(
            (
                f"N = {len(plot_df):,}",
                f"{x_curve} mean = {x_values.mean():.3f}",
                f"{y_curve} mean = {y_values.mean():.3f}",
                f"Corr = {x_values.corr(y_values):.3f}",
            )
        )
        ax.text(
            0.02,
            0.98,
            stats_text,
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=8.5,
            color="#1F2937",
            bbox={"boxstyle": "round,pad=0.35", "facecolor": "#FFFFFF", "edgecolor": "#CBD5E1", "alpha": 0.92},
        )

    def _update_stats_table(self, plot_df, x_curve: str, y_curve: str) -> None:
        x_unit = self._combo_text("cboXUnit")
        y_unit = self._combo_text("cboYUnit")
        rows = [
            ("Points Plotted", f"{len(plot_df):,}"),
            ("Well", str(getattr(self._well, "name", "Unknown"))),
            (f"X Range ({x_unit or '-'})", self._format_range(plot_df[x_curve])),
            (f"Y Range ({y_unit or '-'})", self._format_range(plot_df[y_curve])),
            (f"Mean {x_curve}", f"{plot_df[x_curve].mean():.4f}"),
            (f"Mean {y_curve}", f"{plot_df[y_curve].mean():.4f}"),
        ]
        self._set_stats_rows(rows)

    def _set_stats_rows(self, rows: list[tuple[str, str]]) -> None:
        table = self._workspace.statsTable
        table.setRowCount(len(rows))
        table.setColumnCount(2)
        for row_index, (label, value) in enumerate(rows):
            label_item = QtWidgets.QTableWidgetItem(label)
            value_item = QtWidgets.QTableWidgetItem(value)
            label_item.setFlags(QtCore.Qt.ItemIsEnabled)
            value_item.setFlags(QtCore.Qt.ItemIsEnabled)
            table.setItem(row_index, 0, label_item)
            table.setItem(row_index, 1, value_item)
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)

    def _reset_plot_state(self, message: str) -> None:
        canvas_host = self._workspace.plotFrame
        canvas_layout = self._workspace.canvasInnerLayout
        while canvas_layout.count():
            item = canvas_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        placeholder = QtWidgets.QLabel(message, canvas_host)
        placeholder.setAlignment(QtCore.Qt.AlignCenter)
        placeholder.setWordWrap(True)
        placeholder.setStyleSheet("color:#9CA3AF;font-size:14px;padding:24px;")
        canvas_layout.addStretch(1)
        canvas_layout.addWidget(placeholder)
        canvas_layout.addStretch(1)
        self._workspace.lblCoords.setText("X: --   Y: --")

        self._figure = None
        self._canvas = None
        self._nav_toolbar = None
        self._plot_df = None
        self._update_status_bar()

    def _connect_canvas_events(self) -> None:
        if self._canvas is None:
            return
        self._mpl_connect_id = self._canvas.mpl_connect("motion_notify_event", self._on_mouse_move)

    def _on_mouse_move(self, event) -> None:
        if event.xdata is None or event.ydata is None:
            self._workspace.lblCoords.setText("X: --   Y: --")
            return
        self._workspace.lblCoords.setText(f"X: {event.xdata:.4f}   Y: {event.ydata:.4f}")

    def _toolbar_action(self, action_name: str) -> None:
        if self._nav_toolbar is None:
            return
        action = getattr(self._nav_toolbar, action_name, None)
        if callable(action):
            action()

    def export_current_figure(self, default_format: str | None = None) -> None:
        if self._figure is None:
            QtWidgets.QMessageBox.information(self, "Export Figure", "Plot a crossplot before exporting.")
            return

        selected_filter = "PNG (*.png)"
        suffix = "png"
        if default_format == "pdf":
            selected_filter = "PDF (*.pdf)"
            suffix = "pdf"
        elif default_format == "svg":
            selected_filter = "SVG (*.svg)"
            suffix = "svg"

        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export Crossplot Figure",
            str(Path.home() / f"advanced_crossplot.{suffix}"),
            "PNG (*.png);;PDF (*.pdf);;SVG (*.svg)",
            selected_filter,
        )
        if not filename:
            return

        self._figure.savefig(filename, dpi=300, bbox_inches="tight")
        self.statusBar().showMessage(f"Figure exported to {filename}", 5000)

    def export_current_data(self) -> None:
        if self._plot_df is None or getattr(self._plot_df, "empty", True):
            QtWidgets.QMessageBox.information(self, "Export CSV", "Plot a crossplot before exporting data.")
            return

        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export Crossplot Data",
            str(Path.home() / "advanced_crossplot_data.csv"),
            "CSV Files (*.csv)",
        )
        if not filename:
            return

        self._plot_df.to_csv(filename, index=False)
        self.statusBar().showMessage(f"Crossplot data exported to {filename}", 5000)

    def copy_current_figure_to_clipboard(self) -> None:
        if self._figure is None:
            QtWidgets.QMessageBox.information(self, "Copy Figure", "Plot a crossplot before copying.")
            return

        buffer = io.BytesIO()
        self._figure.savefig(buffer, format="png", dpi=180, bbox_inches="tight")
        image = QtGui.QImage.fromData(buffer.getvalue(), "PNG")
        QtWidgets.QApplication.clipboard().setImage(image)
        self.statusBar().showMessage("Figure copied to clipboard.", 3000)

    def _update_quick_info(self, template_name: str) -> None:
        info = self._TEMPLATE_INFO.get(template_name, self._TEMPLATE_INFO["Generic Crossplot"])
        well_name = getattr(self._well, "name", "No well loaded")
        self._workspace.lblQuickInfoBody.setText(f"{info}\n\nActive well: {well_name}")

    def _update_title(self) -> None:
        self._workspace.lblPlotTitle.setText(self._build_plot_title())

    def _build_plot_title(self) -> str:
        x_curve = self._combo_text("cboXCurve") or "X"
        y_curve = self._combo_text("cboYCurve") or "Y"
        color_curve = self._combo_text("cboColorBy")
        mode = "Hexbin" if self._is_hexbin_mode() else "Scatter"
        title = f"{self._current_template_name()} | {mode} | {x_curve} vs {y_curve}"
        if color_curve and color_curve != "None" and not self._is_hexbin_mode():
            title += f" | Color: {color_curve}"
        return title

    def _update_window_title(self) -> None:
        well_name = getattr(self._well, "name", "No Active Well")
        self.setWindowTitle(f"PetroARX - Advanced Crossplot - {well_name}")

    def _update_status_bar(self, point_count: int | None = None) -> None:
        well_name = getattr(self._well, "name", "No active well")
        curve_count = 0 if self._df is None else len(getattr(self._df, "columns", []))
        if point_count is None:
            message = f"Active well: {well_name} | Curves: {curve_count}"
        else:
            message = f"Active well: {well_name} | Curves: {curve_count} | Points plotted: {point_count:,}"
        self.statusBar().showMessage(message)

    def _format_range(self, series) -> str:
        return f"{series.min():.4f} - {series.max():.4f}"

    def _current_template_name(self) -> str:
        return self._workspace.cboCrossplotType.currentText().strip() or "Generic Crossplot"

    def _is_hexbin_mode(self) -> bool:
        return self._workspace.plot_style_for_cross_plot_comboBox.currentText() == "Hexbin Plot"

    def _combo_text(self, combo_name: str) -> str:
        combo = getattr(self._workspace, combo_name, None)
        if combo is None:
            return ""
        return combo.currentText().strip()

    @staticmethod
    def _axis_label(curve_name: str, unit: str | None) -> str:
        if unit:
            return f"{curve_name} ({unit})"
        return curve_name
