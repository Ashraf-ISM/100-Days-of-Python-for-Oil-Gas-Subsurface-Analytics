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
        curves = self._get_selected_checkable_curves("pairplotcomboBox")
        if len(curves) < 2:
            curves = self._curve_columns(df)[: min(4, len(self._curve_columns(df)))]
        fig = plot_tools.plot_pairplot(df, curves, show=False)
        self._render_plot(fig, f"Pairplot: {', '.join(curves[:4])}")

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
