"""Plot entry points: all plots live in plotting/plot_tools.py"""
from __future__ import annotations

from PyQt5 import QtWidgets

from plotting import plot_tools


class PlotService:
    def __init__(self, ui: QtWidgets.QMainWindow, data_service):
        self.ui = ui
        self.data = data_service

    def _get_df(self):
        well = self.data._get_current_well()
        if not well:
            return None
        return getattr(well, "data", None)

    def new_log_plot(self):
        df = self._get_df()
        if df is None:
            return
        plot_tools.plot_multitrack(df)

    def new_crossplot(self):
        df = self._get_df()
        if df is None:
            return
        # Use first two curves
        cols = list(df.columns)
        if len(cols) < 2:
            return
        plot_tools.plot_crossplot(df, cols[0], cols[1])

    def new_histogram(self):
        df = self._get_df()
        if df is None:
            return
        cols = list(df.columns)
        if not cols:
            return
        plot_tools.plot_histogram(df, cols[0])

    def new_triple_combo(self):
        df = self._get_df()
        if df is None:
            return
        plot_tools.plot_triple_combo(df)
