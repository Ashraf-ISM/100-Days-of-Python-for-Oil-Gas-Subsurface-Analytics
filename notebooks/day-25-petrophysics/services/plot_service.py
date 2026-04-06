"""Plot entry points: all plots live in plotting/plot_tools.py"""
from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets

from plotting import plot_tools


class PlotService:
    def __init__(self, ui: QtWidgets.QMainWindow, data_service):
        self.ui = ui
        self.data = data_service
        self._plot_host: QtWidgets.QWidget | None = None

    def _ensure_log_viewer_host(self):
        frame = getattr(self.ui, "frameLogViewerCanvas", None)
        if frame is None:
            return None

        layout = frame.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(frame)
            layout.setContentsMargins(0, 0, 0, 0)

        if self._plot_host is None:
            self._plot_host = QtWidgets.QWidget(frame)
            host_layout = QtWidgets.QVBoxLayout(self._plot_host)
            host_layout.setContentsMargins(0, 0, 0, 0)
            host_layout.setSpacing(0)
            layout.addWidget(self._plot_host)

        placeholder = getattr(self.ui, "lblLogViewerPlaceholder", None)
        if placeholder is not None:
            placeholder.hide()
        return self._plot_host

    def _activate_log_viewer_tab(self):
        tab_widget = getattr(self.ui, "centralTabWidget", None)
        tab = getattr(self.ui, "tabLogViewer", None)
        if tab_widget is not None and tab is not None:
            tab_widget.setCurrentWidget(tab)

    def _render_plot(self, fig, title: str):
        if fig is None:
            return
        try:
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas  # type: ignore
            from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar  # type: ignore
        except Exception:
            return

        host = self._ensure_log_viewer_host()
        if host is None:
            return
        self._activate_log_viewer_tab()

        layout = host.layout()
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        title_label = QtWidgets.QLabel(title, host)
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_label.setStyleSheet(
            "padding:8px 0 6px 0;"
            "font-size:14px;"
            "font-weight:600;"
            "color:#24466B;"
            "background:#F7FAFD;"
            "border-bottom:1px solid #D5E1EC;"
        )

        canvas = FigureCanvas(fig)
        canvas.setStyleSheet("background:#FFFFFF;")
        toolbar = NavigationToolbar(canvas, host)
        toolbar.setStyleSheet(
            "QToolBar { background:#F7FAFD; border:0; border-bottom:1px solid #D5E1EC; }"
        )

        layout.addWidget(title_label)
        layout.addWidget(toolbar)
        layout.addWidget(canvas, 1)
        canvas.draw_idle()

    def _get_df(self):
        well = self.data._get_current_well()
        if not well:
            return None
        return getattr(well, "data", None)

    def new_log_plot(self):
        df = self._get_df()
        if df is None:
            return
        curves = self._get_selected_multitrack_curves()
        fig = plot_tools.plot_multitrack(df, curves=curves, show=False)
        self._render_plot(fig, "Multi-Track Log Plot")

    def new_crossplot(self):
        df = self._get_df()
        if df is None:
            return
        cols = self._curve_columns(df)
        if len(cols) < 2:
            return
        x_curve = self._combo_text(("comboLVCrossX", "comboXplotX")) or cols[0]
        y_curve = self._combo_text(("comboLVCrossY", "comboXplotY")) or cols[1]
        color_curve = self._combo_text(("comboLVCrossColor", "comboXplotColor"))
        if color_curve == "None":
            color_curve = None
        if x_curve not in df.columns or y_curve not in df.columns:
            return
        fig = plot_tools.plot_crossplot(df, x_curve, y_curve, color_curve=color_curve, show=False)
        title = f"Crossplot: {x_curve} vs {y_curve}"
        if color_curve:
            title += f" | Color: {color_curve}"
        self._render_plot(fig, title)

    def new_histogram(self):
        df = self._get_df()
        if df is None:
            return
        cols = self._curve_columns(df)
        if not cols:
            return
        curve = self._combo_text(("comboLVHistCurve", "comboHistCurve")) or cols[0]
        bins = self._spin_value("spinLVHistBins", default=40)
        if curve not in df.columns:
            return
        fig = plot_tools.plot_histogram(df, curve, bins=bins, show=False)
        self._render_plot(fig, f"Histogram: {curve}")
    def new_pairplot(self):
        df = self._get_df()
        if df is None:
            return

        import pandas as pd
        import seaborn as sns
        from PyQt5.QtWidgets import QMessageBox
    
        # -------------------------------
        # Step 1: Get selected curves
        # -------------------------------
        selected_curves = self._get_selected_checkable_curves("pairplotcomboBox")
    
        # If nothing selected → take ALL numeric curves
        if len(selected_curves) == 0:
            selected_curves = self._curve_columns(df)
    
        curves = [
            curve for curve in selected_curves
            if curve in df.columns and pd.api.types.is_numeric_dtype(df[curve])
        ]
    
        if len(curves) < 2:
            return
    
        # -------------------------------
        # ⚠️ Step 2: Performance control
        # -------------------------------
        MAX_CURVES = 8   # safe limit
    
        if len(curves) > MAX_CURVES:
            reply = QMessageBox.question(
                self.ui,
                "Large Pairplot Warning",
                f"You selected {len(curves)} curves.\n"
                f"This will generate {len(curves)**2} plots and may be very slow.\n\n"
                f"Do you want to continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
    
            if reply == QMessageBox.No:
                return
    
            # Optional: auto limit instead of crash
            curves = curves[:MAX_CURVES]
    
        # -------------------------------
        # Step 3: Color By (dynamic)
        # -------------------------------
        hue_name = self._pairplot_hue_name(df)
    
        # -------------------------------
        # Step 4: Prepare data
        # -------------------------------
        plot_df = df[curves].copy()
    
        if hue_name:
            plot_df[hue_name] = df[hue_name]
    
        plot_df = plot_df.dropna()
    
        # Sampling for speed (VERY IMPORTANT)
        if len(plot_df) > 2000:
            plot_df = plot_df.sample(2000, random_state=42)
    
        # -------------------------------
        # Step 5: Plot
        # -------------------------------
        pairgrid = sns.pairplot(
            plot_df,
            vars=curves,
            hue=hue_name,
            palette="tab10" if hue_name else None,
            diag_kind="kde"
        )
    
        pairgrid.fig.suptitle(
            f"Pairplot ({len(curves)} curves)",
            y=1.02,
            fontsize=14,
            fontweight="600"
        )
    
        self._render_plot(pairgrid.fig, f"Pairplot: {', '.join(curves[:4])}")

        def _pairplot_hue_name(self, df) -> str | None:
            """Resolve the optional hue column for pairplot from UI controls."""
            # Preferred control name in current UI.
            widget = getattr(self.ui, "pairplotcombocolorby", None)
            if widget is not None:
                if hasattr(widget, "currentText"):
                    text = widget.currentText().strip()
                else:
                    text = widget.text().strip()
                if text and text.lower() != "none" and text in df.columns:
                    return text

            # Backward compatibility for older prototypes.
            legacy_widget = getattr(self.ui, "colorByComboBox", None)
            if legacy_widget is not None:
                text = legacy_widget.currentText().strip()
                if text and text.lower() != "none" and text in df.columns:
                    return text

            return None
    
    def new_violinplot(self):
        df = self._get_df()
        if df is None:
            return
        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd
        import seaborn as sns

        selected_curves = self._get_selected_checkable_curves("violinplotcomboBox")
        if not selected_curves:
            selected_curves = self._curve_columns(df)[: min(4, len(self._curve_columns(df)))]

        curves = [
            curve
            for curve in selected_curves
            if curve in df.columns and pd.api.types.is_numeric_dtype(df[curve])
        ]
        if not curves:
            return

        fig, axes = plt.subplots(
            len(curves),
            1,
            figsize=(9, max(3.0, 2.8 * len(curves))),
            constrained_layout=True,
        )
        if len(curves) == 1:
            axes = [axes]

        palette = sns.color_palette("tab10", n_colors=len(curves))
        for axis, curve, color in zip(axes, curves, palette):
            series = df[curve].dropna()
            if series.empty:
                axis.set_axis_off()
                continue

            sns.violinplot(
                y=series,
                ax=axis,
                color=color,
                inner=None,
                cut=0,
                linewidth=1.0,
            )
            if axis.collections:
                violin_body = axis.collections[0]
                path = violin_body.get_paths()[0]
                vertices = path.vertices
                center = float(np.mean(vertices[:, 0]))
                vertices[vertices[:, 0] > center, 0] = center
            sns.boxplot(
                y=series,
                ax=axis,
                width=0.18,
                showfliers=False,
                color="white",
                linewidth=1.0,
            )
            axis.set_title(f"Half Violin & Boxplot of {curve}", fontsize=12, fontweight="600")
            axis.set_xlabel("")
            axis.set_ylabel(curve)
            axis.grid(axis="y", alpha=0.15)

        fig.suptitle("Violin Plot", fontsize=14, fontweight="600")
        self._render_plot(fig, f"Violin Plot: {', '.join(curves[:4])}")

    def new_triple_combo(self):
        df = self._get_df()
        if df is None:
            return
        track1 = self._get_selected_track_curves("triplecombotrack1")
        track2 = self._get_selected_track_curves("triplecombotrack2")
        track3 = self._get_selected_track_curves("triplecombotrack3")
        fig = plot_tools.plot_triple_combo_tracks(
            df, track1, track2, track3, show=False
        )
        self._render_plot(fig, "Triple Combo")

    def _get_selected_multitrack_curves(self):
        selected = self._get_selected_checkable_curves("multitrackcomboBox")
        return selected or None

    def _get_selected_track_curves(self, combo_name: str) -> list[str]:
        combo = getattr(self.ui, combo_name, None)
        if combo is None:
            return []
        model = combo.model()
        if model is None:
            return []
        selected: list[str] = []
        for i in range(model.rowCount()):
            item = model.item(i)
            if item is None:
                continue
            if item.checkState() == QtCore.Qt.Checked:
                selected.append(item.text())
        return selected

    def _get_selected_checkable_curves(self, combo_name: str) -> list[str]:
        combo = getattr(self.ui, combo_name, None)
        if combo is None:
            return []
        model = combo.model()
        if model is None:
            return []
        selected: list[str] = []
        for i in range(model.rowCount()):
            item = model.item(i)
            if item is None:
                continue
            if item.checkState() == QtCore.Qt.Checked:
                selected.append(item.text())
        return selected

    @staticmethod
    def _curve_columns(df) -> list[str]:
        return [str(column) for column in df.columns if str(column).upper() != "DEPTH"]

    def _combo_text(self, names: tuple[str, ...]) -> str | None:
        for name in names:
            combo = getattr(self.ui, name, None)
            if combo is None:
                continue
            text = combo.currentText().strip()
            if text:
                return text
        return None

    def _spin_value(self, name: str, default: int = 40) -> int:
        widget = getattr(self.ui, name, None)
        if widget is None:
            return default
        value_getter = getattr(widget, "value", None)
        if callable(value_getter):
            return int(value_getter())
        return default
