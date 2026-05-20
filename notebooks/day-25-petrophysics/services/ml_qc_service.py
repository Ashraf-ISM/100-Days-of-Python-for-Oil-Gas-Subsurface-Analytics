"""
ml_qc_service.py
================
UI ↔ backend bridge for the ML Based QC tab.

Follows the exact same pattern as QCService:
  - Reads all widget values through safe _get_widget / _combo_text helpers
  - Calls ml_qc_engine.run_ml_qc()
  - Updates summary labels, anomaly table, and matplotlib plots
  - Provides run / reset / export public methods

Widget name contract (all defined in the new tabMLQC in mainwindow.ui):
  comboMLQCWell, comboMLQCCurve, comboMLQCModel, spinMLQCContamination,
  checkMLQCMultiCurve, spinMLQCDepthFrom, spinMLQCDepthTo,
  btnRunMLQC, btnResetMLQC, btnExportMLQC,
  frameMLQCLogView,  lblMLQCLogPlaceholder,
  frameMLQCScatter,  lblMLQCScatterPlaceholder,
  frameMLQCFeatureBar, lblMLQCFeaturePlaceholder,
  lblMLQCScore, lblMLQCAnomalyCount, lblMLQCGoodPct,
  lblMLQCMissingPct, lblMLQCReliability, lblMLQCModel,
  tableMLQCIssues,
  lblMLQCStatus (optional progress label)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from PyQt5 import QtWidgets, QtCore, QtGui

try:
    from ml_qc.ml_qc_engine import run_ml_qc
    from ml_qc.ml_qc_models import MODEL_NAMES
    from ml_qc.ml_anomaly_report import MLQCResult, build_anomaly_rows
    _ML_AVAILABLE = True
except Exception as _ml_err:  # noqa: BLE001
    _ML_AVAILABLE = False
    MODEL_NAMES = ["Isolation Forest", "LOF", "One-Class SVM", "DBSCAN"]


class MLQCService:
    """ML-based Quality Control service for the PetroARX ML Based QC tab."""

    def __init__(self, ui: QtWidgets.QMainWindow, data_service=None):
        self.ui   = ui
        self.data = data_service
        self._last_result: MLQCResult | None = None
        self._last_export_df: pd.DataFrame | None = None
        self._plot_hosts: dict[str, QtWidgets.QWidget] = {}
        self._configure_controls()

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def run_ml_qc(self, *_args) -> None:
        """Run the ML QC pipeline and update all UI panels."""
        if not _ML_AVAILABLE:
            QtWidgets.QMessageBox.warning(
                self.ui, "ML QC",
                "scikit-learn is required for ML-based QC.\n"
                "Install it with:  pip install scikit-learn"
            )
            return

        self._set_status("Running ML QC …")
        QtWidgets.QApplication.processEvents()

        result = self._build_result()
        if result is None:
            self._set_status("No data — load a well first.")
            self._show_placeholders()
            return

        self._last_result = result
        self._build_export_df(result)

        # Update summary cards
        self._set_label("lblMLQCScore",        f"{result.qc_score:.0f}%")
        self._set_label("lblMLQCAnomalyCount", str(result.n_anomalies))
        self._set_label("lblMLQCGoodPct",      f"{result.good_pct:.1f}%")
        self._set_label("lblMLQCReliability",  f"{result.reliability_pct:.0f}%")
        self._set_label("lblMLQCModel",        result.model_name)

        # Missing % from raw curve
        missing_pct = self._compute_missing_pct()
        self._set_label("lblMLQCMissingPct", f"{missing_pct:.1f}%")

        # Anomaly table
        rows = build_anomaly_rows(result)
        self._fill_anomaly_table(rows)

        # Plots
        self._render_log_view(result)
        self._render_score_scatter(result)
        self._render_feature_bar(result)

        sev = result.severity_label
        self._set_status(
            f"ML QC complete — {result.n_anomalies} anomalies detected "
            f"({result.anomaly_pct:.1f}%)  |  Severity: {sev}"
        )

    def reset_ml_qc(self, *_args) -> None:
        """Clear all ML QC outputs."""
        self._last_result     = None
        self._last_export_df  = None
        for name in ("lblMLQCScore", "lblMLQCAnomalyCount",
                     "lblMLQCGoodPct", "lblMLQCMissingPct",
                     "lblMLQCReliability", "lblMLQCModel"):
            self._set_label(name, "—")
        table = self._get_widget("tableMLQCIssues")
        if table is not None:
            table.clearContents()
            table.setRowCount(0)
        self._show_placeholders()
        self._set_status("Ready")

    def export_ml_qc(self, *_args) -> None:
        """Export the anomaly data to CSV."""
        if self._last_export_df is None or self._last_export_df.empty:
            QtWidgets.QMessageBox.information(
                self.ui, "ML QC", "Run ML QC first to generate export data."
            )
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.ui, "Export ML QC Data", "ml_qc_anomalies.csv",
            "CSV Files (*.csv)"
        )
        if not path:
            return
        self._last_export_df.to_csv(path, index=False)
        QtWidgets.QMessageBox.information(
            self.ui, "ML QC", f"ML QC data exported:\n{path}"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Internal: build result
    # ──────────────────────────────────────────────────────────────────────────

    def _build_result(self) -> MLQCResult | None:
        well = self.data._get_current_well() if self.data is not None else None
        df   = getattr(well, "data", None) if well is not None else None
        curve_name = self._combo_text("comboMLQCCurve")
        if df is None or not curve_name or curve_name not in df.columns:
            return None

        depth_label, depth_series = self._depth_series(df)
        curve_series  = pd.to_numeric(df[curve_name], errors="coerce")
        model_name    = self._combo_text("comboMLQCModel") or "Isolation Forest"
        contamination = float(self._spin_value("spinMLQCContamination", 5)) / 100.0
        start_depth   = self._spin_value("spinMLQCDepthFrom", None)
        end_depth     = self._spin_value("spinMLQCDepthTo",   None)
        multi_curve   = self._is_checked("checkMLQCMultiCurve", True)

        return run_ml_qc(
            curve_series   = curve_series,
            depth_series   = depth_series,
            curve_name     = curve_name,
            all_curves_df  = df,
            model_name     = model_name,
            contamination  = contamination,
            start_depth    = float(start_depth) if start_depth else None,
            end_depth      = float(end_depth)   if end_depth   else None,
            use_multi_curve = multi_curve,
        )

    def _build_export_df(self, result: MLQCResult) -> None:
        if result.depth_series is None:
            self._last_export_df = None
            return
        self._last_export_df = pd.DataFrame({
            "DEPTH":          result.depth_series,
            result.curve_name: result.curve_series,
            "anomaly_flag":   result.anomaly_mask.astype(int),
            "anomaly_score":  result.anomaly_scores,
        })

    def _compute_missing_pct(self) -> float:
        well = self.data._get_current_well() if self.data is not None else None
        df   = getattr(well, "data", None) if well is not None else None
        curve_name = self._combo_text("comboMLQCCurve")
        if df is None or not curve_name or curve_name not in df.columns:
            return 0.0
        series = pd.to_numeric(df[curve_name], errors="coerce")
        return 100.0 * series.isna().sum() / max(len(series), 1)

    # ──────────────────────────────────────────────────────────────────────────
    # Plots
    # ──────────────────────────────────────────────────────────────────────────

    def _render_log_view(self, result: MLQCResult) -> None:
        try:
            from matplotlib.figure import Figure
        except Exception:
            return
        if result.curve_series is None or result.depth_series is None:
            return

        depth  = result.depth_series
        curve  = result.curve_series
        mask   = result.anomaly_mask
        scores = result.anomaly_scores

        fig = Figure(figsize=(4.5, 8.5), tight_layout=True)
        ax  = fig.add_subplot(111)
        ax.set_facecolor("#F8FBFE")

        # Normal samples
        normal = ~mask
        ax.plot(
            curve[normal], depth[normal],
            color="#2A5C9E", linewidth=0.9, alpha=0.75, label="Normal"
        )

        # Anomalies
        if mask.any():
            sc = ax.scatter(
                curve[mask], depth[mask],
                c=scores[mask] if scores is not None else "red",
                cmap="YlOrRd", vmin=0, vmax=result.max_score,
                s=22, zorder=4, label=f"Anomaly ({result.n_anomalies})",
                edgecolors="#8B0000", linewidths=0.5
            )
            cbar = fig.colorbar(sc, ax=ax, fraction=0.03, pad=0.01)
            cbar.set_label("Anomaly Score", fontsize=8, color="#24466B")
            cbar.ax.tick_params(labelsize=7)

        ax.set_title(
            f"{result.curve_name} — ML Anomaly Detection\n"
            f"Model: {result.model_name}",
            fontsize=10, fontweight="bold", color="#24466B"
        )
        ax.set_xlabel(result.curve_name, fontsize=9, color="#24466B")
        ax.set_ylabel("Depth", fontsize=9, color="#24466B")
        ax.invert_yaxis()
        ax.grid(color="#DCE6F0", linewidth=0.6, linestyle="--", alpha=0.7)
        ax.legend(loc="best", fontsize=8, frameon=True, framealpha=0.9)
        ax.tick_params(labelsize=8)

        self._render_figure("frameMLQCLogView", "lblMLQCLogPlaceholder", fig)

    def _render_score_scatter(self, result: MLQCResult) -> None:
        try:
            from matplotlib.figure import Figure
        except Exception:
            return
        if result.anomaly_scores is None or result.depth_series is None:
            return

        depth  = result.depth_series.to_numpy(dtype=float)
        scores = result.anomaly_scores.to_numpy(dtype=float)
        mask   = result.anomaly_mask.to_numpy(dtype=bool) if result.anomaly_mask is not None else np.zeros(len(depth), dtype=bool)

        fig = Figure(figsize=(5.5, 3.2), tight_layout=True)
        ax  = fig.add_subplot(111)
        ax.set_facecolor("#F8FBFE")

        # Threshold line (75th percentile of scores)
        threshold = float(np.percentile(scores, 75)) if len(scores) > 4 else 0.0

        ax.fill_betweenx(depth, 0, scores,
                         where=~mask, alpha=0.35, color="#3A72B5", label="Normal")
        ax.fill_betweenx(depth, 0, scores,
                         where=mask,  alpha=0.6,  color="#E55353", label="Anomaly")
        ax.axvline(threshold, color="#F59E0B", linewidth=1.2,
                   linestyle="--", label=f"P75={threshold:.3f}")
        ax.set_title("Anomaly Score vs Depth",
                     fontsize=10, fontweight="bold", color="#24466B")
        ax.set_xlabel("Anomaly Score", fontsize=9, color="#24466B")
        ax.set_ylabel("Depth",         fontsize=9, color="#24466B")
        ax.invert_yaxis()
        ax.grid(color="#DCE6F0", linewidth=0.6, linestyle="--", alpha=0.7)
        ax.legend(loc="best", fontsize=8, frameon=True, framealpha=0.9)
        ax.tick_params(labelsize=8)

        self._render_figure("frameMLQCScatter", "lblMLQCScatterPlaceholder", fig)

    def _render_feature_bar(self, result: MLQCResult) -> None:
        try:
            from matplotlib.figure import Figure
        except Exception:
            return

        names = result.feature_names
        if not names:
            return

        # Use mean absolute value per feature as a proxy for importance
        # (works even when the model doesn't expose native importance)
        fig = Figure(figsize=(5.5, 2.8), tight_layout=True)
        ax  = fig.add_subplot(111)
        ax.set_facecolor("#F8FBFE")

        if result.feature_importance is not None and len(result.feature_importance) == len(names):
            importance = result.feature_importance
        else:
            # Proxy: variance of each feature in the valid window
            importance = np.ones(len(names), dtype=float)

        importance = np.abs(importance)
        if importance.max() > 0:
            importance = importance / importance.max()

        colors = ["#E55353" if imp > 0.6 else "#F59E0B" if imp > 0.3 else "#3A72B5"
                  for imp in importance]
        bars = ax.barh(names, importance, color=colors, edgecolor="white", height=0.55)

        ax.set_xlim(0, 1.15)
        ax.set_title("Feature Contributions",
                     fontsize=10, fontweight="bold", color="#24466B")
        ax.set_xlabel("Relative Importance", fontsize=9, color="#24466B")
        ax.tick_params(axis="y", labelsize=8)
        ax.tick_params(axis="x", labelsize=8)
        ax.grid(axis="x", color="#DCE6F0", linewidth=0.6, linestyle="--", alpha=0.7)

        for bar, val in zip(bars, importance):
            ax.text(bar.get_width() + 0.02, bar.get_y() + bar.get_height() / 2,
                    f"{val:.2f}", va="center", ha="left", fontsize=8, color="#24466B")

        self._render_figure("frameMLQCFeatureBar", "lblMLQCFeaturePlaceholder", fig)

    # ──────────────────────────────────────────────────────────────────────────
    # Table
    # ──────────────────────────────────────────────────────────────────────────

    def _fill_anomaly_table(
        self, rows: list[tuple[str, str, str, str, str]]
    ) -> None:
        table = self._get_widget("tableMLQCIssues")
        if table is None:
            return
        table.clearContents()
        table.setRowCount(len(rows))

        _SEVERITY_COLORS = {
            "Critical": ("#FFEDED", "#C0392B"),
            "Warning":  ("#FFF8ED", "#D97706"),
            "Info":     ("#EDF5FF", "#2563EB"),
        }

        for ri, (depth, curve, value, score, severity) in enumerate(rows):
            items = [depth, curve, value, score, severity]
            bg, fg = _SEVERITY_COLORS.get(severity, ("#FFFFFF", "#1B2B40"))
            for ci, text in enumerate(items):
                item = QtWidgets.QTableWidgetItem(text)
                item.setBackground(QtGui.QColor(bg))
                item.setForeground(QtGui.QColor(fg))
                item.setTextAlignment(
                    QtCore.Qt.AlignCenter if ci != 1 else QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
                )
                table.setItem(ri, ci, item)

        table.resizeColumnsToContents()

    # ──────────────────────────────────────────────────────────────────────────
    # Initialisation
    # ──────────────────────────────────────────────────────────────────────────

    def _configure_controls(self) -> None:
        model_combo = self._get_widget("comboMLQCModel")
        if model_combo is not None and hasattr(model_combo, "clear"):
            model_combo.blockSignals(True)
            model_combo.clear()
            model_combo.addItems(MODEL_NAMES)
            model_combo.setCurrentText("Isolation Forest")
            model_combo.blockSignals(False)

        cont_spin = self._get_widget("spinMLQCContamination")
        if cont_spin is not None and hasattr(cont_spin, "setValue"):
            cont_spin.setValue(5)

    # ──────────────────────────────────────────────────────────────────────────
    # Plot host helpers (same pattern as QCService)
    # ──────────────────────────────────────────────────────────────────────────

    def _render_figure(self, frame_name: str, placeholder_name: str, fig) -> None:
        try:
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            from plotting.plot_context_menu import install_plot_context_menu
        except Exception:
            return

        host = self._ensure_plot_host(frame_name, placeholder_name)
        if host is None:
            return

        layout = host.layout()
        if layout is None:
            return
        while layout.count():
            item   = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        canvas = FigureCanvas(fig)
        canvas.setStyleSheet("background:#FFFFFF;border:0;")
        layout.addWidget(canvas)
        canvas.draw_idle()
        install_plot_context_menu(canvas, fig, host)

    def _ensure_plot_host(
        self, frame_name: str, placeholder_name: str
    ) -> QtWidgets.QWidget | None:
        frame = self._get_widget(frame_name)
        if frame is None:
            return None
        layout = frame.layout()
        if layout is None:
            return None

        placeholder = self._get_widget(placeholder_name)
        if placeholder is not None:
            placeholder.hide()

        host = self._plot_hosts.get(frame_name)
        if host is None:
            host        = QtWidgets.QWidget(frame)
            host_layout = QtWidgets.QVBoxLayout(host)
            host_layout.setContentsMargins(0, 0, 0, 0)
            host_layout.setSpacing(0)
            layout.addWidget(host, 1)
            self._plot_hosts[frame_name] = host
        host.show()
        return host

    def _show_placeholders(self) -> None:
        for frame_name, placeholder_name in (
            ("frameMLQCLogView",    "lblMLQCLogPlaceholder"),
            ("frameMLQCScatter",    "lblMLQCScatterPlaceholder"),
            ("frameMLQCFeatureBar", "lblMLQCFeaturePlaceholder"),
        ):
            placeholder = self._get_widget(placeholder_name)
            if placeholder is not None:
                placeholder.show()
            host = self._plot_hosts.get(frame_name)
            if host is not None and host.layout() is not None:
                while host.layout().count():
                    item   = host.layout().takeAt(0)
                    widget = item.widget()
                    if widget is not None:
                        widget.setParent(None)
                        widget.deleteLater()
                host.hide()

    # ──────────────────────────────────────────────────────────────────────────
    # Low-level widget accessors (safe, mirror QCService pattern)
    # ──────────────────────────────────────────────────────────────────────────

    def _get_widget(self, *names: str):
        for name in names:
            widget = getattr(self.ui, name, None)
            if widget is not None:
                return widget
        return None

    def _combo_text(self, *names: str) -> str:
        combo = self._get_widget(*names)
        if combo is None:
            return ""
        return combo.currentText().strip()

    def _spin_value(self, name: str, default):
        widget = self._get_widget(name)
        if widget is None:
            return default
        getter = getattr(widget, "value", None)
        return getter() if callable(getter) else default

    def _is_checked(self, name: str, default: bool) -> bool:
        widget = self._get_widget(name)
        if widget is None:
            return default
        getter = getattr(widget, "isChecked", None)
        return bool(getter()) if callable(getter) else default

    def _set_label(self, name: str, value: str) -> None:
        label = self._get_widget(name)
        if label is not None:
            label.setText(value)

    def _set_status(self, message: str) -> None:
        self._set_label("lblMLQCStatus", message)
        status_bar = getattr(self.ui, "statusBar", None)
        if callable(status_bar):
            status_bar().showMessage(message, 8000)

    def _depth_series(self, df: pd.DataFrame) -> tuple[str, pd.Series]:
        for col in ("DEPTH", "DEPT", "MD"):
            if col in df.columns:
                return col, pd.to_numeric(df[col], errors="coerce")
        label = getattr(df.index, "name", None) or "Depth"
        return label, pd.Series(pd.to_numeric(df.index, errors="coerce"), index=df.index)
