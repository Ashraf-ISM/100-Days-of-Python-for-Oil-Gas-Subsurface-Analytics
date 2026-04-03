"""Plot entry points: all plots live in plotting/plot_tools.py"""
from __future__ import annotations

from PyQt5 import QtWidgets

from plotting import plot_tools


class PlotService:
    def __init__(self, ui: QtWidgets.QMainWindow, data_service):
        self.ui = ui
        self.data = data_service

    def _show_in_mdi(self, fig, title: str):
        mdi = getattr(self.ui, "mdiArea", None)
        if mdi is None or fig is None:
            return
        try:
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas  # type: ignore
            from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar  # type: ignore
        except Exception:
            return

        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        canvas = FigureCanvas(fig)
        toolbar = NavigationToolbar(canvas, widget)
        layout.addWidget(toolbar)
        layout.addWidget(canvas)

        sub = QtWidgets.QMdiSubWindow()
        sub.setWidget(widget)
        sub.setWindowTitle(title)
        mdi.addSubWindow(sub)
        sub.show()
        mdi.setActiveSubWindow(sub)

    def _get_df(self):
        well = self.data._get_current_well()
        if not well:
            return None
        return getattr(well, "data", None)

    def new_log_plot(self):
        df = self._get_df()
        if df is None:
            return
        fig = plot_tools.plot_multitrack(df, show=False)
        self._show_in_mdi(fig, "Multi-Track Log Plot")

    def new_crossplot(self):
        df = self._get_df()
        if df is None:
            return
        # Use first two curves
        cols = list(df.columns)
        if len(cols) < 2:
            return
        fig = plot_tools.plot_crossplot(df, cols[0], cols[1], show=False)
        self._show_in_mdi(fig, f"Crossplot: {cols[0]} vs {cols[1]}")

    def new_histogram(self):
        df = self._get_df()
        if df is None:
            return
        cols = list(df.columns)
        if not cols:
            return
        fig = plot_tools.plot_histogram(df, cols[0], show=False)
        self._show_in_mdi(fig, f"Histogram: {cols[0]}")

    def new_triple_combo(self):
        df = self._get_df()
        if df is None:
            return
        fig = plot_tools.plot_triple_combo(df, show=False)
        self._show_in_mdi(fig, "Triple Combo")
