"""Interpretation workflow entry points."""
from __future__ import annotations

from PyQt5 import QtWidgets


class InterpretationService:
    def __init__(self, ui: QtWidgets.QMainWindow):
        self.ui = ui

    def compute_vsh(self):
        QtWidgets.QMessageBox.information(self.ui, "Calculations", "Shale volume stub.")

    def compute_phi(self):
        QtWidgets.QMessageBox.information(self.ui, "Calculations", "Porosity stub.")

    def compute_sw(self):
        QtWidgets.QMessageBox.information(self.ui, "Calculations", "Water saturation stub.")

    def compute_perm(self):
        QtWidgets.QMessageBox.information(self.ui, "Calculations", "Permeability stub.")

    def compute_net_pay(self):
        QtWidgets.QMessageBox.information(self.ui, "Calculations", "Net pay stub.")
