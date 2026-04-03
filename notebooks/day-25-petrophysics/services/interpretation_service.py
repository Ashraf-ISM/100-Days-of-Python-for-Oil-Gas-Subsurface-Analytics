"""Interpretation workflow entry points."""
from __future__ import annotations

from PyQt5 import QtWidgets

from calculations import vshale, porosity, saturation, permeability, net_pay


class InterpretationService:
    def __init__(self, ui: QtWidgets.QMainWindow):
        self.ui = ui

    def compute_vsh(self):
        QtWidgets.QMessageBox.information(self.ui, "Interpretation", "Compute Vsh (stub).")

    def compute_phi(self):
        QtWidgets.QMessageBox.information(self.ui, "Interpretation", "Compute porosity (stub).")

    def compute_sw(self):
        QtWidgets.QMessageBox.information(self.ui, "Interpretation", "Compute water saturation (stub).")

    def compute_perm(self):
        QtWidgets.QMessageBox.information(self.ui, "Interpretation", "Compute permeability (stub).")

    def compute_net_pay(self):
        QtWidgets.QMessageBox.information(self.ui, "Interpretation", "Compute net pay (stub).")
