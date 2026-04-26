"""Quality control entry points."""
from __future__ import annotations

import numpy as np
import pandas as pd
from PyQt5 import QtWidgets

try:
    from qc.spike_detector import SpikeDetector, DetectionMode
    _SPIKE_DETECTOR_AVAILABLE = True
except Exception:  # noqa: BLE001
    _SPIKE_DETECTOR_AVAILABLE = False


class QCService:
    def __init__(self, ui: QtWidgets.QMainWindow, data_service=None):
        self.ui = ui
        self.data = data_service
        self._last_rows: list[tuple[str, str, str, str]] = []
        self._last_export_frame: pd.DataFrame | None = None
        self._plot_hosts: dict[str, QtWidgets.QWidget] = {}
        self._configure_controls()

    def run_qc(self, *_args):
        qc_result = self._build_qc_result()
        if qc_result is None:
            self._show_qc_placeholders()
            return

        issue_rows = qc_result["issue_rows"]
        self._last_rows = issue_rows
        self._last_export_frame = qc_result["export_frame"]

        self._set_label(("lblQCMissingCount", "lblLVQCMissingCount"), str(int(qc_result["missing_mask"].sum())))
        self._set_label(("lblQCOutlierCount", "lblLVQCOutlierCount"), str(int(qc_result["outlier_mask"].sum())))
        self._set_label(("lblQCSpikeCount", "lblLVQCSpikeCount"), str(int(qc_result["spike_mask"].sum())))
        self._set_label(("lblQCRetainedPct", "lblLVQCRetainedPct"), f"{qc_result['retained_pct']:.1f}%")
        self._fill_issue_table(issue_rows)

        self._render_log_view(qc_result)
        self._render_histogram(qc_result)
        self._render_boxplot(qc_result)

    def export_qc(self):
        if self._last_export_frame is None or self._last_export_frame.empty:
            QtWidgets.QMessageBox.information(self.ui, "QC", "Run QC first to export cleaned data.")
            return

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.ui,
            "Export Cleaned Data",
            "qc_cleaned_data.csv",
            "CSV Files (*.csv)",
        )
        if not path:
            return

        self._last_export_frame.to_csv(path, index=False)
        QtWidgets.QMessageBox.information(self.ui, "QC", f"Cleaned QC data exported:\n{path}")

    def reset_qc(self):
        self._last_rows = []
        self._last_export_frame = None
        self._set_label(("lblQCMissingCount", "lblLVQCMissingCount"), "0")
        self._set_label(("lblQCOutlierCount", "lblLVQCOutlierCount"), "0")
        self._set_label(("lblQCSpikeCount", "lblLVQCSpikeCount"), "0")
        self._set_label(("lblQCRetainedPct", "lblLVQCRetainedPct"), "100%")
        table = self._get_widget("tableQCIssues", "tableLVQCIssues")
        if table is not None:
            table.clearContents()
            table.setRowCount(0)
        self._show_qc_placeholders()

    def _build_qc_result(self):
        well = self.data._get_current_well() if self.data is not None else None
        df = getattr(well, "data", None) if well is not None else None
        curve = self._current_curve_name()
        if df is None or curve not in getattr(df, "columns", []):
            return None

        depth_label, depth_series = self._depth_series(df)
        curve_series = pd.to_numeric(df[curve], errors="coerce")
        start_depth = self._spin_value(("spinQCFrom", "spinLVQCFrom"), None)
        end_depth = self._spin_value(("spinQCTo", "spinLVQCTo"), None)
        threshold = float(self._spin_value(("spinQCThreshold", "spinLVQCThreshold"), 3.0) or 3.0)
        window = max(int(self._spin_value(("spinQCWindow", "spinLVQCWindow"), 5) or 5), 3)
        method = self._combo_text("comboQCMethod", "comboLVQCMethod") or "Isolation Forest"
        smoothing = self._combo_text("comboQCSmoothing", "comboLVQCSmoothing") or "None"
        # New spike-specific controls (graceful fallback when widgets absent)
        spike_mode  = self._combo_text("comboQCSpikeMode") or "Standard"
        spike_conf  = float(self._spin_value("spinQCConfidence", 0.5) or 0.5) / 100.0 \
                      if self._spin_value("spinQCConfidence", None) is not None \
                         and self._spin_value("spinQCConfidence", 50) > 1 \
                      else float(self._spin_value("spinQCConfidence", 0.5) or 0.5)
        cross_log   = self._is_checked("checkQCCrossLog", True)
        correction  = self._combo_text("comboQCCorrection") or "local_median"

        visible_mask = depth_series.notna()
        if start_depth not in (None, 0):
            visible_mask &= depth_series >= float(start_depth)
        if end_depth not in (None, 0):
            visible_mask &= depth_series <= float(end_depth)

        if not visible_mask.any():
            QtWidgets.QMessageBox.information(self.ui, "QC", "No samples found inside the selected depth range.")
            return None

        finite_mask = visible_mask & curve_series.notna()
        if not finite_mask.any():
            QtWidgets.QMessageBox.information(self.ui, "QC", f"Curve '{curve}' has no numeric values in the selected range.")
            return None

        missing_mask = visible_mask & curve_series.isna() if self._is_checked(("checkQCMissing", "checkLVQCMissing"), True) else pd.Series(False, index=df.index)
        outlier_mask = pd.Series(False, index=df.index)
        spike_mask = pd.Series(False, index=df.index)
        spike_confidence_series = pd.Series(np.nan, index=df.index, dtype=float)
        negative_mask = pd.Series(False, index=df.index)

        valid_index = df.index[finite_mask]
        valid_values = curve_series.loc[valid_index].to_numpy(dtype=float)
        valid_depths = depth_series.loc[valid_index].to_numpy(dtype=float)

        # ── OUTLIER DETECTION ────────────────────────────────────────────────
        if self._is_checked(("checkQCOutliers", "checkLVQCOutliers"), True) and valid_values.size >= 8:
            if method == "Isolation Forest":
                detected = self._detect_isolation_forest(valid_depths, valid_values, threshold)
                outlier_mask.loc[valid_index] = detected

            elif method == "Moving Z-Score":
                # FIX: use a rolling window to compute local mean/std, then flag
                # points whose |z-score| exceeds the threshold.  We guard against
                # tiny windows and zero std, and we do NOT artificially inflate the
                # threshold with max(threshold, 0.5) – the user controls sensitivity
                # directly via the threshold spinner.
                s = curve_series.where(visible_mask)
                rolling_mean = s.rolling(window=window, center=True, min_periods=3).mean()
                rolling_std  = s.rolling(window=window, center=True, min_periods=3).std(ddof=1)
                # Replace zero / NaN std with a small fallback so we don't get
                # spurious flags when the curve is locally flat.
                rolling_std = rolling_std.where(rolling_std > 1e-9, other=np.nan)
                zscore = (s - rolling_mean) / rolling_std
                outlier_mask = visible_mask & zscore.abs().gt(threshold).fillna(False)

            elif method == "IQR Rule":
                # FIX: use threshold directly as the IQR fence multiplier.
                # Standard petrophysics practice: 1.5 = mild outlier, 3.0 = extreme.
                # The user's threshold spinner maps 1:1 to the fence multiplier.
                q1, q3 = np.percentile(valid_values, [25, 75])
                iqr = max(q3 - q1, 1e-9)
                lower = q1 - threshold * iqr
                upper = q3 + threshold * iqr
                outlier_mask = finite_mask & ((curve_series < lower) | (curve_series > upper))
 
            else:  # Global Z-Score
                # FIX: use robust statistics (median / MAD) instead of mean/std
                # so that the presence of outliers doesn't inflate the baseline.
                median = float(np.nanmedian(valid_values))
                mad    = float(np.nanmedian(np.abs(valid_values - median)))
                robust_std = max(mad * 1.4826, 1e-9)   # MAD → equivalent std
                zscore = (curve_series - median) / robust_std
                outlier_mask = visible_mask & zscore.abs().gt(threshold).fillna(False)

        # ── SPIKE DETECTION (enterprise 7-stage engine) ─────────────────────
        if self._is_checked(("checkQCSpikes", "checkLVQCSpikes"), True) and valid_values.size >= 5:
            if _SPIKE_DETECTOR_AVAILABLE:
                spike_result = SpikeDetector().detect(
                    curve_series=curve_series.loc[valid_index],
                    depth_series=depth_series.loc[valid_index],
                    curve_name=curve,
                    all_curves_df=df,
                    mode=spike_mode,
                    window=window,
                    mad_multiplier=threshold,
                    confidence_threshold=spike_conf,
                    cross_log_validation=cross_log,
                    correction=correction,
                )
                spike_mask.loc[valid_index] = spike_result.is_spike
                spike_confidence_series.loc[valid_index] = spike_result.confidence
            else:
                # Fallback: legacy rolling-median/MAD (single-pass)
                n = len(valid_values)
                spike_detected = np.zeros(n, dtype=bool)
                half_w = max(window // 2, 2)
                for i in range(1, n - 1):
                    lo = max(0, i - half_w)
                    hi = min(n, i + half_w + 1)
                    neighbours = np.concatenate([valid_values[lo:i], valid_values[i + 1:hi]])
                    if neighbours.size < 2:
                        continue
                    local_med = np.median(neighbours)
                    local_mad = np.median(np.abs(neighbours - local_med))
                    local_std = max(local_mad * 1.4826, 1e-9)
                    if abs(valid_values[i] - local_med) > threshold * local_std:
                        spike_detected[i] = True
                spike_mask.loc[valid_index] = spike_detected

        # ── NEGATIVE VALUE DETECTION ─────────────────────────────────────────
        if self._is_checked(("checkQCNegative", "checkLVQCNegative"), True):
            negative_mask = visible_mask & curve_series.lt(0).fillna(False)

        # ── CLEANING & EXPORT FRAME ──────────────────────────────────────────
        issue_mask = missing_mask | outlier_mask | spike_mask | negative_mask
        cleaned_series = curve_series.copy()
        cleaned_series.loc[issue_mask] = np.nan
        cleaned_series = cleaned_series.interpolate(limit_direction="both")
        cleaned_series = self._apply_smoothing(cleaned_series.where(visible_mask), smoothing, window)

        retained_mask  = visible_mask & ~issue_mask
        visible_count  = int(visible_mask.sum()) or 1
        retained_pct   = 100.0 * retained_mask.sum() / visible_count
        issue_rows = self._build_issue_rows(
            depth_series=depth_series,
            values=curve_series,
            missing_mask=missing_mask,
            outlier_mask=outlier_mask,
            spike_mask=spike_mask,
            negative_mask=negative_mask,
            spike_confidence=spike_confidence_series,
        )

        export_frame = pd.DataFrame(
            {
                depth_label: depth_series.where(visible_mask),
                curve: curve_series.where(visible_mask),
                f"{curve}_cleaned": cleaned_series.where(visible_mask),
                "missing_flag":      missing_mask.where(visible_mask, False).astype(int),
                "outlier_flag":      outlier_mask.where(visible_mask, False).astype(int),
                "spike_flag":        spike_mask.where(visible_mask, False).astype(int),
                "spike_confidence":  spike_confidence_series.where(visible_mask),
                "negative_flag":     negative_mask.where(visible_mask, False).astype(int),
            }
        ).loc[visible_mask].reset_index(drop=True)

        return {
            "curve": curve,
            "depth_label": depth_label,
            "depth_series": depth_series,
            "curve_series": curve_series,
            "cleaned_series": cleaned_series,
            "visible_mask": visible_mask,
            "missing_mask": missing_mask,
            "outlier_mask": outlier_mask,
            "spike_mask": spike_mask,
            "negative_mask": negative_mask,
            "retained_pct": retained_pct,
            "issue_rows": issue_rows,
            "export_frame": export_frame,
        }

    def _configure_controls(self) -> None:
        combo = self._get_widget("comboQCMethod", "comboLVQCMethod")
        if combo is not None and hasattr(combo, "clear"):
            combo.clear()
            combo.addItems(["Isolation Forest", "Moving Z-Score", "Z-Score", "IQR Rule"])
            combo.setCurrentText("Isolation Forest")

        # Spike mode selector
        spike_mode_combo = self._get_widget("comboQCSpikeMode")
        if spike_mode_combo is not None and hasattr(spike_mode_combo, "clear"):
            spike_mode_combo.blockSignals(True)
            spike_mode_combo.clear()
            spike_mode_combo.addItems(["Standard", "Advanced", "ML"])
            spike_mode_combo.setCurrentText("Standard")
            spike_mode_combo.blockSignals(False)

        # Correction method selector
        correction_combo = self._get_widget("comboQCCorrection")
        if correction_combo is not None and hasattr(correction_combo, "clear"):
            correction_combo.blockSignals(True)
            correction_combo.clear()
            correction_combo.addItems(["local_median", "linear", "cubic", "keep"])
            correction_combo.setCurrentText("local_median")
            correction_combo.blockSignals(False)

        # Confidence spinner default (0–100 integer % in UI)
        conf_spin = self._get_widget("spinQCConfidence")
        if conf_spin is not None and hasattr(conf_spin, "setValue"):
            conf_spin.setValue(50)

    def _depth_series(self, df) -> tuple[str, pd.Series]:
        if "DEPTH" in df.columns:
            return "DEPTH", pd.to_numeric(df["DEPTH"], errors="coerce")
        if "DEPT" in df.columns:
            return "DEPT", pd.to_numeric(df["DEPT"], errors="coerce")
        depth_label = getattr(df.index, "name", None) or "Depth"
        return depth_label, pd.Series(pd.to_numeric(df.index, errors="coerce"), index=df.index)

    def _detect_isolation_forest(
        self,
        depth_values: np.ndarray,
        curve_values: np.ndarray,
        threshold: float,
    ) -> np.ndarray:
        """Isolation Forest outlier detection.

        FIX: contamination now maps the *threshold* slider sensibly.
        threshold=1  → contamination≈0.10  (aggressive)
        threshold=3  → contamination≈0.05  (moderate, typical default)
        threshold=9  → contamination≈0.02  (conservative)
        Formula: contamination = clip(0.15 / threshold, 0.01, 0.15)
        """
        try:
            from sklearn.ensemble import IsolationForest
        except Exception:
            return np.zeros(curve_values.shape[0], dtype=bool)

        features = np.column_stack([depth_values, curve_values])
        feature_std  = np.nanstd(features, axis=0)
        feature_std[feature_std == 0] = 1.0
        features = (features - np.nanmean(features, axis=0)) / feature_std

        contamination = float(np.clip(0.15 / max(float(threshold), 0.5), 0.01, 0.15))
        model = IsolationForest(
            contamination=contamination,
            n_estimators=200,
            random_state=42,
        )
        return model.fit_predict(features) == -1

    def _apply_smoothing(self, series: pd.Series, method: str, window: int) -> pd.Series:
        window = max(int(window), 3)
        if method == "Moving Avg":
            return series.rolling(window=window, center=True, min_periods=1).mean()
        if method == "Median":
            return series.rolling(window=window, center=True, min_periods=1).median()
        return series

    def _build_issue_rows(
        self,
        *,
        depth_series: pd.Series,
        values: pd.Series,
        missing_mask: pd.Series,
        outlier_mask: pd.Series,
        spike_mask: pd.Series,
        negative_mask: pd.Series,
        spike_confidence: pd.Series | None = None,
    ) -> list[tuple[str, str, str, str]]:
        rows: list[tuple[str, str, str, str]] = []

        for mask, issue, action in (
            (missing_mask,  "Missing",  "Flagged"),
            (outlier_mask,  "Outlier",  "Review"),
            (negative_mask, "Negative", "Flagged"),
        ):
            for index in depth_series.index[mask][:250]:
                rows.append(
                    (
                        self._fmt_depth(depth_series.loc[index]),
                        issue,
                        self._fmt_value(values.loc[index]),
                        action,
                    )
                )

        # Spikes get a confidence-annotated action label: "Smooth [87%]"
        for index in depth_series.index[spike_mask][:250]:
            conf_val = None
            if spike_confidence is not None and index in spike_confidence.index:
                cv = spike_confidence.loc[index]
                try:
                    cv = float(cv)
                    if not np.isnan(cv):
                        conf_val = cv
                except Exception:  # noqa: BLE001
                    pass
            if conf_val is not None:
                action_str = f"Smooth [{int(round(conf_val * 100))}%]"
            else:
                action_str = "Smooth"
            rows.append(
                (
                    self._fmt_depth(depth_series.loc[index]),
                    "Spike",
                    self._fmt_value(values.loc[index]),
                    action_str,
                )
            )

        rows.sort(key=lambda row: self._safe_float(row[0]))
        return rows[:250]

    def _render_log_view(self, qc_result) -> None:
        try:
            from matplotlib.figure import Figure
        except Exception:
            return

        curve      = qc_result["curve"]
        depth_label = qc_result["depth_label"]
        depth       = qc_result["depth_series"]
        raw         = qc_result["curve_series"]
        cleaned     = qc_result["cleaned_series"]
        visible_mask = qc_result["visible_mask"]

        fig = Figure(figsize=(4.6, 7.5), tight_layout=True)
        ax  = fig.add_subplot(111)
        ax.set_facecolor("#FBFCFE")
        ax.plot(raw[visible_mask],     depth[visible_mask], color="#355C7D", linewidth=0.9, alpha=0.7, label="Original")
        ax.plot(cleaned[visible_mask], depth[visible_mask], color="#2F855A", linewidth=1.4, label="Cleaned")

        for mask_name, color, label in (
            ("missing_mask",  "#6C4CE0", "Missing"),
            ("outlier_mask",  "#D1495B", "Outlier"),
            ("spike_mask",    "#F59E0B", "Spike"),
            ("negative_mask", "#2563EB", "Negative"),
        ):
            mask    = qc_result[mask_name]
            flagged = visible_mask & mask
            if flagged.any():
                marker_x = cleaned[flagged].fillna(raw[flagged])
                ax.scatter(marker_x, depth[flagged], s=18, color=color, alpha=0.9, label=label, zorder=3)

        ax.set_title(f"{curve} Log View", fontsize=11, fontweight="bold", color="#24466B")
        ax.set_xlabel(curve, fontsize=9, color="#24466B")
        ax.set_ylabel(depth_label, fontsize=9, color="#24466B")
        ax.grid(color="#DCE6F0", linewidth=0.7)
        ax.invert_yaxis()
        ax.legend(loc="best", fontsize=8, frameon=True)
        self._render_figure("frameQCLogView", "lblQCLogViewPlaceholder", fig)

    def _render_histogram(self, qc_result) -> None:
        try:
            from matplotlib.figure import Figure
        except Exception:
            return

        curve   = qc_result["curve"]
        raw     = qc_result["curve_series"][qc_result["visible_mask"]].dropna().to_numpy(dtype=float)
        cleaned = qc_result["cleaned_series"][qc_result["visible_mask"]].dropna().to_numpy(dtype=float)

        fig = Figure(figsize=(5.4, 2.8), tight_layout=True)
        ax  = fig.add_subplot(111)
        ax.set_facecolor("#FBFCFE")
        ax.hist(raw,     bins=25, alpha=0.55, color="#D1495B", label="Before QC")
        ax.hist(cleaned, bins=25, alpha=0.55, color="#2A9D8F", label="After QC")
        ax.set_title(f"{curve} Histogram", fontsize=10, fontweight="bold", color="#24466B")
        ax.set_xlabel(curve, fontsize=8.5, color="#24466B")
        ax.set_ylabel("Frequency", fontsize=8.5, color="#24466B")
        ax.grid(axis="y", color="#E5EDF5", linewidth=0.7)
        ax.legend(fontsize=8)
        self._render_figure("frameQCHistogram", "lblQCHistPlaceholder", fig)

    def _render_boxplot(self, qc_result) -> None:
        try:
            from matplotlib.figure import Figure
        except Exception:
            return

        curve   = qc_result["curve"]
        raw     = qc_result["curve_series"][qc_result["visible_mask"]].dropna().to_numpy(dtype=float)
        cleaned = qc_result["cleaned_series"][qc_result["visible_mask"]].dropna().to_numpy(dtype=float)

        fig = Figure(figsize=(4.0, 2.8), tight_layout=True)
        ax  = fig.add_subplot(111)
        ax.set_facecolor("#FBFCFE")
        box = ax.boxplot(
            [raw, cleaned],
            labels=["Before QC", "After QC"],
            patch_artist=True,
            widths=0.5,
        )
        for patch, color in zip(box["boxes"], ("#F28B82", "#7CD4C6")):
            patch.set_facecolor(color)
            patch.set_alpha(0.8)
        ax.set_title(f"{curve} Boxplot", fontsize=10, fontweight="bold", color="#24466B")
        ax.set_ylabel(curve, fontsize=8.5, color="#24466B")
        ax.grid(axis="y", color="#E5EDF5", linewidth=0.7)
        self._render_figure("frameQCBoxplot", "lblQCBoxPlaceholder", fig)

    def _render_figure(self, frame_name: str, placeholder_name: str, fig) -> None:
        try:
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas  # type: ignore
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

    def _ensure_plot_host(self, frame_name: str, placeholder_name: str) -> QtWidgets.QWidget | None:
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

    def _show_qc_placeholders(self) -> None:
        for frame_name, placeholder_name in (
            ("frameQCLogView",  "lblQCLogViewPlaceholder"),
            ("frameQCHistogram", "lblQCHistPlaceholder"),
            ("frameQCBoxplot",  "lblQCBoxPlaceholder"),
        ):
            placeholder = self._get_widget(placeholder_name)
            if placeholder is not None:
                placeholder.show()
            host = self._plot_hosts.get(frame_name)
            if host is None or host.layout() is None:
                continue
            while host.layout().count():
                item   = host.layout().takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()
            host.hide()

    def _current_curve_name(self) -> str:
        return self._combo_text("comboQCCurve", "comboLVQCCurve") or ""

    def _combo_text(self, *names: str) -> str:
        combo = self._get_widget(*names)
        if combo is None:
            return ""
        return combo.currentText().strip()

    def _spin_value(self, names, default):
        if isinstance(names, str):
            names = (names,)
        widget = self._get_widget(*names)
        if widget is None:
            return default
        getter = getattr(widget, "value", None)
        if callable(getter):
            return getter()
        return default

    def _is_checked(self, names, default: bool) -> bool:
        if isinstance(names, str):
            names = (names,)
        widget = self._get_widget(*names)
        if widget is None:
            return default
        getter = getattr(widget, "isChecked", None)
        if callable(getter):
            return bool(getter())
        return default

    def _set_label(self, names, value: str) -> None:
        if isinstance(names, str):
            names = (names,)
        label = self._get_widget(*names)
        if label is not None:
            label.setText(value)

    def _fill_issue_table(self, rows: list[tuple[str, str, str, str]]) -> None:
        table = self._get_widget("tableQCIssues", "tableLVQCIssues")
        if table is None:
            return
        table.clearContents()
        table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for col_index, value in enumerate(row):
                table.setItem(row_index, col_index, QtWidgets.QTableWidgetItem(value))
        table.resizeColumnsToContents()

    def _get_widget(self, *names: str):
        for name in names:
            widget = getattr(self.ui, name, None)
            if widget is not None:
                return widget
        return None

    @staticmethod
    def _fmt_depth(value) -> str:
        try:
            return f"{float(value):.2f}"
        except Exception:
            return str(value)

    @staticmethod
    def _fmt_value(value) -> str:
        try:
            return f"{float(value):.3f}"
        except Exception:
            return ""

    @staticmethod
    def _safe_float(value: str) -> float:
        try:
            return float(value)
        except Exception:
            return float("inf")