"""Plot entry points: all plots live in plotting/plot_tools.py"""
from __future__ import annotations

from PyQt5 import QtWidgets

from plotting import plot_tools


class PlotService:
    def __init__(self, ui: QtWidgets.QMainWindow):
        self.ui = ui

    def new_log_plot(self):
        QtWidgets.QMessageBox.information(self.ui, "Plot", "Multi-track plot stub.")
        # plot_tools.plot_multitrack(...)

    def new_crossplot(self):
        QtWidgets.QMessageBox.information(self.ui, "Plot", "Crossplot stub.")
        # plot_tools.plot_crossplot(...)

    def new_histogram(self):
        QtWidgets.QMessageBox.information(self.ui, "Plot", "Histogram stub.")
        # plot_tools.plot_histogram(...)

    def new_triple_combo(self):
        QtWidgets.QMessageBox.information(self.ui, "Plot", "Triple combo stub.")
        # plot_tools.plot_triple_combo(...)
