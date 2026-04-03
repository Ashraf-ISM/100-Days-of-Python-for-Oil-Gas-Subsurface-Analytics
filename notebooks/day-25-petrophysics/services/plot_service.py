"""Plot creation entry points (multi-track, triple combo, crossplot, histogram)."""
from __future__ import annotations

from PyQt5 import QtWidgets


class PlotService:
    def __init__(self, ui: QtWidgets.QMainWindow):
        self.ui = ui

    def new_log_plot(self):
        QtWidgets.QMessageBox.information(self.ui, "Plot", "Open multi-track plot (stub).")

    def new_crossplot(self):
        QtWidgets.QMessageBox.information(self.ui, "Plot", "Open crossplot (stub).")

    def new_histogram(self):
        QtWidgets.QMessageBox.information(self.ui, "Plot", "Open histogram (stub).")

    def new_triple_combo(self):
        QtWidgets.QMessageBox.information(self.ui, "Plot", "Open triple combo plot (stub).")
