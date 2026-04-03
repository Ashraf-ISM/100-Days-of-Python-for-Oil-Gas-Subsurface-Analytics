"""Interpretation workflow connected to data."""
from __future__ import annotations

from PyQt5 import QtWidgets

from calculations import vshale, porosity, saturation, permeability, net_pay


class InterpretationService:
    def __init__(self, ui: QtWidgets.QMainWindow, data_service):
        self.ui = ui
        self.data = data_service

    def compute_vsh(self):
        well = self.data._get_current_well()
        if not well:
            return
        df = getattr(well, "data", None)
        if df is None or "GR" not in df.columns:
            QtWidgets.QMessageBox.warning(self.ui, "Calculations", "GR curve not found.")
            return
        df["VSH"] = vshale.compute_vsh_gr(df["GR"].values)
        self.data._refresh_views()

    def compute_phi(self):
        well = self.data._get_current_well()
        if not well:
            return
        df = getattr(well, "data", None)
        if df is None:
            return
        if "NPHI" in df.columns and "RHOB" in df.columns:
            df["PHIT"] = porosity.compute_phi_combo(df["NPHI"].values, df["RHOB"].values)
        elif "RHOB" in df.columns:
            df["PHIT"] = porosity.compute_phi_from_density(df["RHOB"].values)
        else:
            QtWidgets.QMessageBox.warning(self.ui, "Calculations", "NPHI/RHOB not found.")
            return
        self.data._refresh_views()

    def compute_sw(self):
        well = self.data._get_current_well()
        if not well:
            return
        df = getattr(well, "data", None)
        if df is None:
            return
        if "PHIT" not in df.columns:
            self.compute_phi()
        if "LLD" in df.columns:
            df["SW"] = saturation.compute_sw_archie(df["PHIT"].values, df["LLD"].values)
        else:
            QtWidgets.QMessageBox.warning(self.ui, "Calculations", "Resistivity (LLD) not found.")
            return
        self.data._refresh_views()

    def compute_perm(self):
        well = self.data._get_current_well()
        if not well:
            return
        df = getattr(well, "data", None)
        if df is None:
            return
        if "PHIT" not in df.columns:
            self.compute_phi()
        if "SW" not in df.columns:
            self.compute_sw()
        if "PHIT" in df.columns and "SW" in df.columns:
            df["PERM"] = permeability.compute_perm_timur(df["PHIT"].values, df["SW"].values)
            self.data._refresh_views()

    def compute_net_pay(self):
        well = self.data._get_current_well()
        if not well:
            return
        df = getattr(well, "data", None)
        if df is None:
            return
        # Ensure dependencies
        if "VSH" not in df.columns:
            self.compute_vsh()
        if "PHIT" not in df.columns:
            self.compute_phi()
        if "SW" not in df.columns:
            self.compute_sw()
        if "PERM" not in df.columns:
            self.compute_perm()

        vsh_cut = getattr(self.ui, "spinVshCutoff", None)
        phi_cut = getattr(self.ui, "spinPhiCutoff", None)
        sw_cut = getattr(self.ui, "spinSwCutoff", None)
        perm_cut = getattr(self.ui, "spinPermCutoff", None)

        vsh_val = vsh_cut.value() if vsh_cut else 0.4
        phi_val = phi_cut.value() if phi_cut else 0.05
        sw_val = sw_cut.value() if sw_cut else 0.65
        perm_val = perm_cut.value() if perm_cut else 0.1

        df["NET_PAY"] = net_pay.compute_net_pay(
            df["VSH"].values,
            df["PHIT"].values,
            df["SW"].values,
            df["PERM"].values,
            vsh_cut=vsh_val,
            phi_cut=phi_val,
            sw_cut=sw_val,
            perm_cut=perm_val,
        )
        self.data._refresh_views()
