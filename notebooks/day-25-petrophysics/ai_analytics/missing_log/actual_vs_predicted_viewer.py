"""
actual_vs_predicted_viewer.py

A professional "Actual vs Predicted Log" viewer dialog for the
Missing Log Prediction module.

Features
--------
* Depth-based well-log tracks (actual, predicted, error)
* All selected feature / input logs displayed as extra tracks
* Missing-interval shading on the actual track
* Toggle options: show/hide tracks, depth range, log scale, line width
* Colour-coded legend and metric badge strip
* Embeds a matplotlib FigureCanvas inside PyQt5
"""
from __future__ import annotations

from typing import Optional, List, Tuple

import numpy as np
import pandas as pd

from PyQt5 import QtWidgets, QtCore, QtGui

# ─── colour palette ───────────────────────────────────────────────────────────
_CLR_ACTUAL     = "#2563EB"   # blue
_CLR_PREDICTED  = "#10B981"   # emerald
_CLR_ERROR      = "#EF4444"   # red
_CLR_MISSING    = "#FEF3C7"   # amber-50 fill for missing intervals
_CLR_BORDER     = "#E2E8F0"
_CLR_BG         = "#F8FAFC"
_CLR_HEADER_BG  = "#1E293B"
_CLR_HEADER_FG  = "#F1F5F9"

# Standard log colours for feature tracks
_FEATURE_COLOURS = [
    "#7C3AED", "#0891B2", "#D97706", "#64748B",
    "#DB2777", "#059669", "#B45309", "#475569",
]


# ─────────────────────────────────────────────────────────────────────────────
class ActualVsPredictedDialog(QtWidgets.QDialog):
    """
    Full-featured Actual vs Predicted log viewer.

    Parameters
    ----------
    df          : well DataFrame (must include depth column)
    target      : name of the target log (what was predicted)
    features    : list of input feature log names to display
    result      : dict returned by TrainingWorker (contains X_test, y_test, y_pred)
    parent      : optional parent widget
    """

    def __init__(
        self,
        df: pd.DataFrame,
        target: str,
        features: List[str],
        result: dict,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Actual vs Predicted Log — Well Log Viewer")
        self.setMinimumSize(1200, 800)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(
            self.windowFlags() | QtCore.Qt.WindowMaximizeButtonHint
        )

        self._df       = df.copy()
        self._target   = target
        self._features = features
        self._result   = result

        # Resolve depth column
        self._depth_col = next(
            (c for c in df.columns if str(c).upper() in {"DEPTH", "DEPT", "MD"}),
            None,
        )

        # Build prediction series aligned to full depth
        self._pred_series = self._build_predicted_series()

        # ── layout: left options panel + right canvas ─────────────────────────
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._options_panel = self._build_options_panel()
        root.addWidget(self._options_panel)

        right = QtWidgets.QWidget()
        right.setStyleSheet(f"background:{_CLR_BG};")
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setContentsMargins(8, 8, 8, 8)

        self._canvas_holder = QtWidgets.QWidget()
        self._canvas_layout = QtWidgets.QVBoxLayout(self._canvas_holder)
        self._canvas_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self._canvas_holder, stretch=1)

        # metric strip
        self._metric_strip = self._build_metric_strip()
        right_layout.addWidget(self._metric_strip)

        # close button
        close_row = QtWidgets.QHBoxLayout()
        close_row.addStretch()
        close_btn = QtWidgets.QPushButton("✕  Close")
        close_btn.setStyleSheet(
            "QPushButton{background:#334155;color:#F1F5F9;border-radius:6px;"
            "padding:7px 24px;font-weight:700;font-size:12px;}"
            "QPushButton:hover{background:#475569;}"
        )
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        right_layout.addLayout(close_row)

        root.addWidget(right, stretch=1)

        # draw initial plot
        self._refresh_plot()

    # ─────────────────────────────────────────────────────────────────────────
    # Options panel
    # ─────────────────────────────────────────────────────────────────────────

    def _build_options_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        panel.setFixedWidth(230)
        panel.setStyleSheet(
            f"background:{_CLR_HEADER_BG}; color:{_CLR_HEADER_FG};"
        )
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(6)

        # ── title ─────────────────────────────────────────────────────────────
        title = QtWidgets.QLabel("🎛  Display Options")
        title.setStyleSheet(
            "font-size:13px;font-weight:700;color:#38BDF8;"
            "padding:4px 0 8px 0;border-bottom:1px solid #334155;"
        )
        layout.addWidget(title)

        # ── track toggles ─────────────────────────────────────────────────────
        sect1 = self._section_label("Tracks")
        layout.addWidget(sect1)

        self._chk_actual    = self._opt_check("Actual Log",          True,  _CLR_ACTUAL)
        self._chk_predicted = self._opt_check("Predicted Log",       True,  _CLR_PREDICTED)
        self._chk_error     = self._opt_check("Error (|Δ|) Track",   True,  _CLR_ERROR)
        self._chk_features  = self._opt_check("Feature Logs",        True,  "#7C3AED")
        self._chk_missing   = self._opt_check("Shade Missing Gaps",  True,  "#F59E0B")

        for chk in (self._chk_actual, self._chk_predicted,
                    self._chk_error, self._chk_features, self._chk_missing):
            layout.addWidget(chk)
            chk.stateChanged.connect(self._refresh_plot)

        layout.addSpacing(8)

        # ── feature log selector ──────────────────────────────────────────────
        sect2 = self._section_label("Feature Logs to Show")
        layout.addWidget(sect2)

        self._feature_list = QtWidgets.QListWidget()
        self._feature_list.setSelectionMode(
            QtWidgets.QAbstractItemView.MultiSelection
        )
        self._feature_list.setStyleSheet(
            "QListWidget{background:#0F172A;color:#CBD5E1;"
            "border:1px solid #334155;border-radius:4px;font-size:10px;}"
            "QListWidget::item:selected{background:#1D4ED8;color:white;}"
            "QListWidget::item:hover{background:#1E3A5F;}"
        )
        self._feature_list.setFixedHeight(120)
        for feat in self._features:
            item = QtWidgets.QListWidgetItem(feat)
            item.setSelected(True)
            self._feature_list.addItem(item)
        self._feature_list.itemSelectionChanged.connect(self._refresh_plot)
        layout.addWidget(self._feature_list)

        layout.addSpacing(8)

        # ── depth range ───────────────────────────────────────────────────────
        sect3 = self._section_label("Depth Range (m)")
        layout.addWidget(sect3)

        if self._depth_col is not None:
            depths = pd.to_numeric(
                self._df[self._depth_col], errors="coerce"
            ).dropna()
            d_min, d_max = float(depths.min()), float(depths.max())
        else:
            d_min, d_max = 0.0, 5000.0

        self._spin_depth_from = QtWidgets.QDoubleSpinBox()
        self._spin_depth_from.setRange(d_min, d_max)
        self._spin_depth_from.setValue(d_min)
        self._spin_depth_from.setSingleStep(10)
        self._spin_depth_from.setDecimals(1)
        self._spin_depth_from.setPrefix("From: ")
        self._spin_depth_from.setStyleSheet(self._spin_style())
        self._spin_depth_from.valueChanged.connect(self._refresh_plot)

        self._spin_depth_to   = QtWidgets.QDoubleSpinBox()
        self._spin_depth_to.setRange(d_min, d_max)
        self._spin_depth_to.setValue(d_max)
        self._spin_depth_to.setSingleStep(10)
        self._spin_depth_to.setDecimals(1)
        self._spin_depth_to.setPrefix("To:   ")
        self._spin_depth_to.setStyleSheet(self._spin_style())
        self._spin_depth_to.valueChanged.connect(self._refresh_plot)

        layout.addWidget(self._spin_depth_from)
        layout.addWidget(self._spin_depth_to)

        layout.addSpacing(8)

        # ── visual options ────────────────────────────────────────────────────
        sect4 = self._section_label("Visual")
        layout.addWidget(sect4)

        self._chk_logscale = self._opt_check("Log Scale (X axis)",  False, "#94A3B8")
        self._chk_logscale.stateChanged.connect(self._refresh_plot)
        layout.addWidget(self._chk_logscale)

        lw_row = QtWidgets.QHBoxLayout()
        lw_lbl = QtWidgets.QLabel("Line Width:")
        lw_lbl.setStyleSheet("font-size:10px;color:#94A3B8;")
        self._spin_lw = QtWidgets.QDoubleSpinBox()
        self._spin_lw.setRange(0.5, 4.0)
        self._spin_lw.setValue(1.2)
        self._spin_lw.setSingleStep(0.2)
        self._spin_lw.setDecimals(1)
        self._spin_lw.setStyleSheet(self._spin_style())
        self._spin_lw.valueChanged.connect(self._refresh_plot)
        lw_row.addWidget(lw_lbl)
        lw_row.addWidget(self._spin_lw)
        layout.addLayout(lw_row)

        layout.addStretch()

        # refresh button
        ref_btn = QtWidgets.QPushButton("↺  Refresh Plot")
        ref_btn.setStyleSheet(
            "QPushButton{background:#1D4ED8;color:white;border-radius:6px;"
            "padding:7px;font-weight:700;font-size:11px;}"
            "QPushButton:hover{background:#2563EB;}"
        )
        ref_btn.clicked.connect(self._refresh_plot)
        layout.addWidget(ref_btn)

        return panel

    # ─────────────────────────────────────────────────────────────────────────
    # Metric strip (R², RMSE, MAE, MAPE)
    # ─────────────────────────────────────────────────────────────────────────

    def _build_metric_strip(self) -> QtWidgets.QWidget:
        strip = QtWidgets.QWidget()
        strip.setStyleSheet(
            "background:#1E293B;border-radius:8px;margin-top:4px;"
        )
        row = QtWidgets.QHBoxLayout(strip)
        row.setContentsMargins(12, 6, 12, 6)
        row.setSpacing(20)

        r = self._result
        metrics = [
            ("R²",   f"{r.get('r2',   0):.4f}", "#34D399"),
            ("RMSE", f"{r.get('rmse', 0):.4f}", "#60A5FA"),
            ("MAE",  f"{r.get('mae',  0):.4f}", "#FBBF24"),
            ("MAPE", f"{r.get('mape', 0):.2f}%","#F472B6"),
            ("CV R²",f"{r.get('cv_mean',0):.4f} ± {r.get('cv_std',0):.4f}", "#A78BFA"),
            ("Algo", r.get("algorithm", "—"),    "#94A3B8"),
        ]

        for name, val, colour in metrics:
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(2)
            n_lbl = QtWidgets.QLabel(name)
            n_lbl.setStyleSheet("font-size:9px;color:#64748B;font-weight:600;")
            v_lbl = QtWidgets.QLabel(val)
            v_lbl.setStyleSheet(
                f"font-size:12px;color:{colour};font-weight:800;"
            )
            col.addWidget(n_lbl, alignment=QtCore.Qt.AlignCenter)
            col.addWidget(v_lbl, alignment=QtCore.Qt.AlignCenter)
            row.addLayout(col)

        row.addStretch()
        return strip

    # ─────────────────────────────────────────────────────────────────────────
    # Plot rendering
    # ─────────────────────────────────────────────────────────────────────────

    def _refresh_plot(self):
        """Rebuild and redisplay the matplotlib figure."""
        try:
            import matplotlib
            matplotlib.use("Qt5Agg")
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
            from matplotlib.backends.backend_qt5agg import (
                FigureCanvasQTAgg as FigureCanvas,
            )
            from matplotlib.ticker import AutoMinorLocator
        except ImportError:
            self._show_no_mpl()
            return

        # ── clear old canvas ──────────────────────────────────────────────────
        while self._canvas_layout.count():
            item = self._canvas_layout.takeAt(0)
            if item.widget():
                item.widget().close()
                item.widget().deleteLater()

        # ── gather options ────────────────────────────────────────────────────
        show_actual    = self._chk_actual.isChecked()
        show_predicted = self._chk_predicted.isChecked()
        show_error     = self._chk_error.isChecked()
        show_features  = self._chk_features.isChecked()
        shade_missing  = self._chk_missing.isChecked()
        log_scale      = self._chk_logscale.isChecked()
        lw             = self._spin_lw.value()
        d_from         = self._spin_depth_from.value()
        d_to           = self._spin_depth_to.value()

        # Selected feature logs
        sel_features = [
            self._feature_list.item(i).text()
            for i in range(self._feature_list.count())
            if self._feature_list.item(i).isSelected()
        ] if show_features else []

        # ── filter by depth ───────────────────────────────────────────────────
        df = self._df.copy()
        if self._depth_col:
            depth_num = pd.to_numeric(df[self._depth_col], errors="coerce")
            mask = (depth_num >= d_from) & (depth_num <= d_to)
            df = df[mask]

        depth = (
            pd.to_numeric(df[self._depth_col], errors="coerce").values
            if self._depth_col
            else np.arange(len(df))
        )

        actual_vals = (
            pd.to_numeric(df[self._target], errors="coerce").values
            if self._target in df.columns
            else None
        )

        # predicted series (already full-depth, slice to depth range)
        pred_vals = (
            self._pred_series.reindex(df.index).values
            if self._pred_series is not None
            else None
        )

        # ── figure layout ─────────────────────────────────────────────────────
        n_tracks = 0
        track_meta: list[dict] = []

        # Track 0: actual + predicted (combined)
        if show_actual or show_predicted:
            n_tracks += 1
            track_meta.append({"type": "main"})

        # Track 1: error
        if show_error and pred_vals is not None and actual_vals is not None:
            n_tracks += 1
            track_meta.append({"type": "error"})

        # Feature tracks
        for i, feat in enumerate(sel_features):
            if feat in df.columns:
                n_tracks += 1
                colour = _FEATURE_COLOURS[i % len(_FEATURE_COLOURS)]
                track_meta.append({"type": "feature", "name": feat, "colour": colour})

        if n_tracks == 0:
            return

        fig_w = max(6, 2.2 * n_tracks)
        fig, axes = plt.subplots(
            1, n_tracks,
            figsize=(fig_w, 10),
            sharey=True,
            facecolor=_CLR_BG,
        )
        if n_tracks == 1:
            axes = [axes]

        ax_idx = 0
        for meta in track_meta:
            ax = axes[ax_idx]
            ax.set_facecolor("#F0F4FF")
            ax.invert_yaxis()
            ax.grid(True, axis="y", color="#CBD5E1", linewidth=0.4, linestyle="--")

            if meta["type"] == "main":
                # ── actual ────────────────────────────────────────────────────
                if show_actual and actual_vals is not None:
                    ax.plot(
                        actual_vals, depth,
                        color=_CLR_ACTUAL, linewidth=lw,
                        label="Actual", zorder=3,
                    )
                    # shade missing intervals
                    if shade_missing:
                        self._shade_missing(ax, actual_vals, depth)

                # ── predicted ─────────────────────────────────────────────────
                if show_predicted and pred_vals is not None:
                    ax.plot(
                        pred_vals, depth,
                        color=_CLR_PREDICTED, linewidth=lw,
                        linestyle="--", label="Predicted", zorder=4,
                    )

                # x-axis label
                unit = self._guess_unit(self._target)
                ax.set_xlabel(
                    f"{self._target} ({unit})",
                    fontsize=8, color="#475569", labelpad=4,
                )
                ax.set_title(
                    f"Actual vs Predicted\n{self._target}",
                    fontsize=9, color="#1E293B", fontweight="bold", pad=6,
                )

                # legend patches
                handles = []
                if show_actual:
                    handles.append(
                        mpatches.Patch(color=_CLR_ACTUAL,     label="Actual")
                    )
                if show_predicted:
                    handles.append(
                        mpatches.Patch(color=_CLR_PREDICTED,  label="Predicted")
                    )
                if handles:
                    ax.legend(handles=handles, fontsize=7,
                              loc="lower right", framealpha=0.7)

            elif meta["type"] == "error":
                err = np.abs(actual_vals - pred_vals)
                ax.fill_betweenx(depth, 0, err,
                                 color=_CLR_ERROR, alpha=0.5, zorder=2)
                ax.plot(err, depth, color=_CLR_ERROR, linewidth=lw * 0.8, zorder=3)
                ax.set_xlabel("|Error|", fontsize=8, color="#475569", labelpad=4)
                ax.set_title("Error\n|Actual − Pred|", fontsize=9,
                             color="#B91C1C", fontweight="bold", pad=6)
                ax.set_facecolor("#FFF5F5")

            elif meta["type"] == "feature":
                feat_vals = pd.to_numeric(df[meta["name"]], errors="coerce").values
                colour    = meta["colour"]
                ax.plot(feat_vals, depth,
                        color=colour, linewidth=lw, zorder=3)
                unit = self._guess_unit(meta["name"])
                ax.set_xlabel(
                    f"{meta['name']} ({unit})",
                    fontsize=8, color="#475569", labelpad=4,
                )
                ax.set_title(meta["name"], fontsize=9,
                             color=colour, fontweight="bold", pad=6)
                ax.set_facecolor("#F5F0FF")

            # log scale
            if log_scale:
                try:
                    ax.set_xscale("log")
                except Exception:
                    pass

            # spine styling
            for spine in ax.spines.values():
                spine.set_edgecolor("#CBD5E1")
                spine.set_linewidth(0.6)
            ax.tick_params(axis="both", labelsize=7, colors="#475569")
            ax.yaxis.set_minor_locator(AutoMinorLocator(5))
            ax.grid(True, axis="y", which="minor",
                    color="#E2E8F0", linewidth=0.3, linestyle=":")
            ax_idx += 1

        # y-axis label on the first track
        axes[0].set_ylabel("Depth (m)", fontsize=9, color="#475569")

        fig.subplots_adjust(
            left=0.07, right=0.99, top=0.93, bottom=0.07,
            wspace=0.35,
        )

        canvas = FigureCanvas(fig)
        plt.close(fig)
        self._canvas_layout.addWidget(canvas)
        canvas.draw()

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _build_predicted_series(self) -> Optional[pd.Series]:
        """
        Build a full-depth predicted Series from the training result.

        The worker stores X_test / y_test indices implicitly via sklearn's
        train_test_split (random index). We reconstruct a full-depth series
        by predicting on ALL rows that have complete features.
        """
        result = self._result
        if result is None:
            return None

        model = result.get("model")
        if model is None:
            return None

        # Features used during training — infer from result
        features = []
        if "importances" in result and result["importances"]:
            features = list(result["importances"].keys())

        # fallback: try all numeric columns except target and depth
        if not features:
            skip = {self._target, self._depth_col or ""}
            features = [
                c for c in self._df.select_dtypes(include=[np.number]).columns
                if c not in skip
            ]

        # Filter columns that exist in df
        features = [f for f in features if f in self._df.columns]
        if not features:
            return None

        try:
            sub = self._df[features].copy()
            mask = sub.notna().all(axis=1)
            if not mask.any():
                return None
            X_all = sub[mask].values
            y_hat = model.predict(X_all)
            pred  = pd.Series(index=self._df.index, dtype=float)
            pred[mask] = y_hat
            return pred
        except Exception:
            return None

    @staticmethod
    def _shade_missing(ax, actual_vals: np.ndarray, depth: np.ndarray):
        """Shade depth intervals where actual log is NaN."""
        in_gap = False
        gap_start = None
        for i, (v, d) in enumerate(zip(actual_vals, depth)):
            is_nan = np.isnan(v) if not isinstance(v, str) else True
            if is_nan and not in_gap:
                gap_start = d
                in_gap = True
            elif not is_nan and in_gap:
                ax.axhspan(gap_start, d, color=_CLR_MISSING, alpha=0.4, zorder=1)
                in_gap = False
        if in_gap and gap_start is not None:
            ax.axhspan(gap_start, depth[-1], color=_CLR_MISSING, alpha=0.4, zorder=1)

    @staticmethod
    def _guess_unit(log_name: str) -> str:
        _UNIT_MAP = {
            "GR": "API", "NPHI": "V/V", "RHOB": "g/cc",
            "DT": "µs/ft", "DTC": "µs/ft", "DTS": "µs/ft",
            "RT": "Ω·m", "RD": "Ω·m", "ILD": "Ω·m",
            "CALI": "in", "PE": "b/e", "SP": "mV",
            "MD": "m", "DEPT": "m", "DEPTH": "m",
            "PORO": "V/V", "PHI": "V/V", "SW": "V/V",
            "VCL": "V/V", "VSH": "V/V", "TEMP": "°C",
        }
        key = log_name.upper().split("_")[0].split("-")[0].strip()
        if key in _UNIT_MAP:
            return _UNIT_MAP[key]
        for k, v in _UNIT_MAP.items():
            if k in key:
                return v
        return "—"

    def _show_no_mpl(self):
        lbl = QtWidgets.QLabel(
            "⚠  matplotlib is required for this view.\n\n"
            "Install it with:  pip install matplotlib"
        )
        lbl.setAlignment(QtCore.Qt.AlignCenter)
        lbl.setStyleSheet("color:#94A3B8;font-size:13px;")
        self._canvas_layout.addWidget(lbl)

    # ─── factory helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _section_label(text: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text.upper())
        lbl.setStyleSheet(
            "font-size:9px;font-weight:800;color:#64748B;"
            "letter-spacing:1px;padding:4px 0 2px 0;"
        )
        return lbl

    @staticmethod
    def _opt_check(label: str, default: bool, colour: str) -> QtWidgets.QCheckBox:
        chk = QtWidgets.QCheckBox(label)
        chk.setChecked(default)
        chk.setStyleSheet(
            f"QCheckBox{{color:#CBD5E1;font-size:10px;}}"
            f"QCheckBox::indicator:checked{{background:{colour};"
            f"border:1px solid {colour};border-radius:3px;}}"
            f"QCheckBox::indicator:unchecked{{background:#334155;"
            f"border:1px solid #475569;border-radius:3px;}}"
            f"QCheckBox::indicator{{width:12px;height:12px;}}"
        )
        return chk

    @staticmethod
    def _spin_style() -> str:
        return (
            "QDoubleSpinBox{background:#0F172A;color:#CBD5E1;"
            "border:1px solid #334155;border-radius:4px;"
            "padding:3px 4px;font-size:10px;}"
            "QDoubleSpinBox::up-button,QDoubleSpinBox::down-button"
            "{background:#1E293B;border:none;width:14px;}"
        )
