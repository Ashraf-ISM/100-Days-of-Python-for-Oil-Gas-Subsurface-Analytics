"""Plot entry points: all plots live in plotting/plot_tools.py"""
from __future__ import annotations

from PyQt5 import QtWidgets

from plotting import plot_tools


class PlotService:
    def __init__(self, ui: QtWidgets.QMainWindow, data_service):
        self.ui = ui
        self.data = data_service
        self._plot_window: QtWidgets.QMainWindow | None = None
        self._plot_tabs: QtWidgets.QTabWidget | None = None

    def _ensure_plot_window(self):
        if self._plot_window is None:
            self._plot_window = QtWidgets.QMainWindow(self.ui)
            self._plot_window.setWindowTitle("PetroVision Plots")
            self._plot_window.resize(1100, 800)
            self._plot_tabs = QtWidgets.QTabWidget()
            self._plot_window.setCentralWidget(self._plot_tabs)
        self._plot_window.show()
        self._plot_window.raise_()
        self._plot_window.activateWindow()

    def _add_plot_tab(self, fig, title: str):
        if fig is None:
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

        self._ensure_plot_window()
        if self._plot_tabs is None:
            return
        idx = self._plot_tabs.addTab(widget, title)
        self._plot_tabs.setCurrentIndex(idx)

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
        self._add_plot_tab(fig, "Multi-Track Log Plot")

    def new_crossplot(self):
        df = self._get_df()
        if df is None:
            return
        # Use first two curves
        cols = list(df.columns)
        if len(cols) < 2:
            return
        fig = plot_tools.plot_crossplot(df, cols[0], cols[1], show=False)
        self._add_plot_tab(fig, f"Crossplot: {cols[0]} vs {cols[1]}")

    def new_histogram(self):
        df = self._get_df()
        if df is None:
            return
        cols = list(df.columns)
        if not cols:
            return
        fig = plot_tools.plot_histogram(df, cols[0], show=False)
        self._add_plot_tab(fig, f"Histogram: {cols[0]}")

    def new_triple_combo(self):
        df = self._get_df()
        if df is None:
            return
        fig = plot_tools.plot_triple_combo(df, show=False)
        self._add_plot_tab(fig, "Triple Combo")
