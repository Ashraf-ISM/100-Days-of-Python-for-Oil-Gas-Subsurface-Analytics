"""Interpretation workflow connected to data."""
from __future__ import annotations

import numpy as np
from PyQt5 import QtCore, QtWidgets

from calculations import vshale, porosity, saturation, permeability, net_pay


class InterpretationService:
    def __init__(self, ui: QtWidgets.QMainWindow, data_service):
        self.ui = ui
        self.data = data_service
        self._net_pay_canvas = None
        self._net_pay_toolbar = None
        self._net_pay_plot_host = None
        self._net_pay_table = None
        self._net_pay_summary_labels: dict[str, QtWidgets.QLabel] = {}
        self._build_net_pay_workspace()

    def compute_vsh(self):
        well = self.data._get_current_well()
        if not well:
            return
        df = getattr(well, "data", None)
        gr_curve = self._combo_text("comboVclGR") or "GR"
        if df is None or gr_curve not in df.columns:
            QtWidgets.QMessageBox.warning(self.ui, "Calculations", "GR curve not found.")
            return
        gr_min = self._spin_value(("spinVclGRmin",), None)
        gr_max = self._spin_value(("spinVclGRmax",), None)
        out_name = self._line_text("lineVclOutName") or "VSH"
        vsh = vshale.compute_vsh_gr(df[gr_curve].values, gr_min=gr_min, gr_max=gr_max)
        df["VSH"] = vsh
        if out_name != "VSH":
            df[out_name] = vsh
        self.data._refresh_views()

    def compute_phi(self):
        well = self.data._get_current_well()
        if not well:
            return
        df = getattr(well, "data", None)
        if df is None:
            return
        method = self._combo_text("comboPhiMethod")
        rho_ma = self._spin_value(("spinPhiRhoma",), 2.65) or 2.65
        rho_f = self._spin_value(("spinPhiRhof",), 1.0) or 1.0
        out_name = self._line_text("linePhiOutName") or "PHIE"

        if method == "Neutron (PHIN)" and "NPHI" in df.columns:
            phi = np.clip(np.asarray(df["NPHI"].values, dtype=float), 0.0, 1.0)
        elif method == "Density (PHID)" and "RHOB" in df.columns:
            phi = porosity.compute_phi_from_density(df["RHOB"].values, rho_ma=rho_ma, rho_f=rho_f)
        elif method == "Sonic (DT)" and "DT" in df.columns:
            dt = np.asarray(df["DT"].values, dtype=float)
            phi = np.clip((dt - 55.5) / (189.0 - 55.5 + 1e-9), 0.0, 1.0)
        elif "NPHI" in df.columns and "RHOB" in df.columns:
            phi = porosity.compute_phi_combo(df["NPHI"].values, df["RHOB"].values, rho_ma=rho_ma, rho_f=rho_f)
        elif "RHOB" in df.columns:
            phi = porosity.compute_phi_from_density(df["RHOB"].values, rho_ma=rho_ma, rho_f=rho_f)
        else:
            QtWidgets.QMessageBox.warning(self.ui, "Calculations", "NPHI/RHOB not found.")
            return
        df["PHIT"] = phi
        if out_name != "PHIT":
            df[out_name] = phi
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
            out_name = self._line_text("linePermOutName") or "PERM"
            perm = permeability.compute_perm_timur(df["PHIT"].values, df["SW"].values)
            df["PERM"] = perm
            if out_name != "PERM":
                df[out_name] = perm
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

        vsh_val = self._spin_value(("spinNetPayVcl", "spinVshCutoff"), 0.4) or 0.4
        phi_val = self._spin_value(("spinNetPayPhi", "spinPhiCutoff"), 0.05) or 0.05
        sw_val = self._spin_value(("spinNetPaySw", "spinSwCutoff"), 0.65) or 0.65
        perm_val = self._spin_value(("spinNetPayPerm", "spinPermCutoff"), 0.1) or 0.1
        out_name = self._line_text("lineNetPayOut") or "NET_PAY"

        pay_flag = net_pay.compute_net_pay(
            df["VSH"].values,
            df["PHIT"].values,
            df["SW"].values,
            df["PERM"].values,
            vsh_cut=vsh_val,
            phi_cut=phi_val,
            sw_cut=sw_val,
            perm_cut=perm_val,
        )
        df["NET_PAY"] = pay_flag
        if out_name != "NET_PAY":
            df[out_name] = pay_flag
        self.data._refresh_views()

    def _combo_text(self, name: str) -> str:
        combo = getattr(self.ui, name, None)
        if combo is None:
            return ""
        return combo.currentText().strip()

    def _line_text(self, name: str) -> str:
        widget = getattr(self.ui, name, None)
        if widget is None:
            return ""
        getter = getattr(widget, "text", None)
        if callable(getter):
            return getter().strip()
        return ""

    def _spin_value(self, names: tuple[str, ...], default):
        for name in names:
            widget = getattr(self.ui, name, None)
            if widget is None:
                continue
            getter = getattr(widget, "value", None)
            if callable(getter):
                return getter()
        return default
