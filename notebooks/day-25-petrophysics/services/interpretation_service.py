"""Interpretation workflow connected to data."""
from __future__ import annotations

import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

from calculations import vshale, porosity, saturation, permeability, net_pay


class InterpretationService:
    def __init__(self, ui: QtWidgets.QMainWindow, data_service):
        self.ui = ui
        self.data = data_service
        self._vsh_track_host = None
        self._vsh_hist_host = None
        self._vsh_box_host = None
        self._vsh_widgets: dict[str, QtWidgets.QWidget] = {}
        self._build_vsh_workspace()
        self._net_pay_canvas = None
        self._net_pay_toolbar = None
        self._net_pay_plot_host = None
        self._net_pay_table = None
        self._net_pay_summary_labels: dict[str, QtWidgets.QLabel] = {}
        self._build_net_pay_workspace()
        self._porosity_log_host = None
        self._porosity_crossplot_host = None
        self._porosity_hist_host = None
        self._porosity_activity_list = None
        self._porosity_kpi_labels: dict[str, QtWidgets.QLabel] = {}
        self._porosity_quality_labels: dict[str, QtWidgets.QLabel] = {}
        self._porosity_method_buttons: dict[str, QtWidgets.QPushButton] = {}
        self._porosity_activity_items: list[str] = []
        self._build_porosity_workspace()
        self._sw_log_host = None
        self._sw_crossplot_host = None
        self._sw_qc_host = None
        self._sw_activity_list = None
        self._sw_kpi_labels: dict[str, QtWidgets.QLabel] = {}
        self._sw_side_summary_labels: dict[str, QtWidgets.QLabel] = {}
        self._sw_quality_labels: dict[str, QtWidgets.QLabel] = {}
        self._sw_activity_items: list[str] = []
        self._build_sw_workspace()

    def compute_vsh(self):
        self.run_vsh_workflow()

    def run_vsh_workflow(self):
        well = self.data._get_current_well()
        if not well:
            return
        df = getattr(well, "data", None)
        if df is None:
            return

        self._sync_gr_curve_line(df)

        methods = self._selected_vsh_methods()
        primary_method = methods[0]
        gr_curve = self._combo_text("comboVclGR") or self._line_text("gRCurveLineEdit") or "GR"
        if gr_curve not in df.columns:
            QtWidgets.QMessageBox.warning(self.ui, "Calculations", "GR curve not found.")
            return
        gr_min = self._spin_value(("spinVclGRmin",), None)
        gr_max = self._spin_value(("spinVclGRmax",), None)
        if gr_max is None:
            gr_max = self._line_float("gRShaleLineEdit", None)
        out_name = self._line_text("lineVclOutName") or "VSH"

        method_columns: list[tuple[str, str]] = []
        for method in methods:
            vsh_values = self._compute_vsh_values(df[gr_curve].values, gr_min, gr_max, method)
            col_name = f"VSH_{self._slugify_method(method)}"
            df[col_name] = vsh_values
            method_columns.append((method, col_name))

        primary_col = method_columns[0][1]
        df["VSH"] = df[primary_col].values
        df["Vsh"] = df[primary_col].values
        if out_name != "VSH":
            df[out_name] = df[primary_col].values

        visible = self.data._filtered_dataframe(well)
        if visible is None or visible.empty:
            visible = df.copy()

        stats = self.compute_vsh_stats(visible, value_col=primary_col)
        method_text = ", ".join(methods)
        self._update_vsh_kpis(gr_min, gr_max, method_text, stats)
        self._plot_vsh_track(visible, gr_curve, method_columns)
        self._clear_vsh_distribution_hosts()
        interpretation = self.generate_vsh_interpretation(stats, methods)
        interp_widget = getattr(self.ui, "vshInterpretationText", None)
        if interp_widget is not None:
            interp_widget.setPlainText(interpretation)

        self.data._refresh_views()

    def compute_vsh_stats(self, df, value_col: str = "VSH"):
        import pandas as pd

        vsh_series = pd.to_numeric(df.get(value_col, df.get("VSH", df.get("Vsh"))), errors="coerce")
        vsh_series = vsh_series.dropna()
        if vsh_series.empty:
            return {"mean": 0.0, "min": 0.0, "max": 0.0, "shale_percent": 0.0}

        return {
            "mean": float(vsh_series.mean()),
            "min": float(vsh_series.min()),
            "max": float(vsh_series.max()),
            "shale_percent": float((vsh_series > 0.5).mean() * 100.0),
        }

    def generate_vsh_interpretation(self, stats, methods: list[str] | None = None):
        lines = []
        if methods:
            lines.append(f"Methods evaluated: {', '.join(methods)}.")

        if stats["mean"] > 0.4:
            lines.append("High shale content detected.")
        else:
            lines.append("Overall shale content is moderate to low.")

        if stats["shale_percent"] > 50:
            lines.append("Formation is predominantly shale.")
            lines.append("Expect weaker reservoir quality in many intervals.")
        else:
            lines.append("Significant clean sand intervals present.")
            lines.append("Reservoir-prone windows are available for downstream evaluation.")

        lines.append("Recommended downstream checks: porosity filtering, Sw cutoffs, and net-pay refinement.")
        return "\n".join(lines)

    def reset_vsh_panel(self):
        for name, value in (("spinVclGRmin", 15.0), ("spinVclGRmax", 120.0)):
            widget = getattr(self.ui, name, None)
            if widget is not None and hasattr(widget, "setValue"):
                widget.setValue(value)

        shale_line = getattr(self.ui, "gRShaleLineEdit", None)
        if shale_line is not None and hasattr(shale_line, "setText"):
            shale_line.setText("120")

        line = getattr(self.ui, "lineVclOutName", None)
        if line is not None:
            line.setText("VSH")

        combo = getattr(self.ui, "vshMethodComboBox", None)
        if combo is not None:
            self._set_checked_vsh_methods(["Linear"])
            if hasattr(combo, "setCurrentIndex"):
                combo.setCurrentIndex(0)

        for name in ("grCleanLabel", "grShaleLabel", "methodLabel", "vshMeanLabel", "vshRangeLabel", "shalePercentLabel"):
            self._set_label_text(name, "--")

        text = getattr(self.ui, "vshInterpretationText", None)
        if text is not None:
            text.clear()

        for host in (self._vsh_track_host, self._vsh_hist_host, self._vsh_box_host):
            if host is None or host.layout() is None:
                continue
            layout = host.layout()
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()

    def _compute_vsh_values(self, gr_values, gr_min, gr_max, method: str):
        import numpy as np

        gr = np.asarray(gr_values, dtype=float)
        if gr_min is None:
            gr_min = float(np.nanpercentile(gr, 5))
        if gr_max is None:
            gr_max = float(np.nanpercentile(gr, 95))

        igr = (gr - float(gr_min)) / (float(gr_max) - float(gr_min) + 1e-9)
        igr = np.clip(igr, 0.0, 1.0)
        method_name = str(method or "Linear").strip().lower()

        if "larionov" in method_name and "tertiary" in method_name:
            vsh = 0.083 * (2 ** (3.7 * igr) - 1.0)
        elif "larionov" in method_name:
            vsh = 0.33 * (2 ** (2.0 * igr) - 1.0)
        elif "clavier" in method_name:
            inside = 3.38 - np.square(igr + 0.7)
            vsh = 1.7 - np.sqrt(np.clip(inside, 0.0, None))
        else:
            vsh = igr

        return np.clip(vsh, 0.0, 1.0)

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
        self._append_porosity_activity("Porosity calculated")
        self.refresh_porosity_workspace()

    def reset_phi_panel(self):
        well_combo = getattr(self.ui, "comboPhiWell", None)
        if well_combo is not None and hasattr(well_combo, "currentText"):
            current_well = well_combo.currentText().strip()
            if current_well and current_well in getattr(self.data, "_wells", {}):
                self.data.set_current_well(current_well)

        method_combo = getattr(self.ui, "comboPhiMethod", None)
        if method_combo is not None:
            target_text = "Density-Neutron (PHIE)"
            index = method_combo.findText(target_text)
            if index >= 0:
                method_combo.setCurrentIndex(index)

        for name, value in (("spinPhiRhoma", 2.65), ("spinPhiRhof", 1.0)):
            widget = getattr(self.ui, name, None)
            if widget is not None and hasattr(widget, "setValue"):
                widget.setValue(value)

        vcl_widget = getattr(self.ui, "checkPhiVclCorr", None)
        if vcl_widget is not None and hasattr(vcl_widget, "setChecked"):
            vcl_widget.setChecked(True)

        out_widget = getattr(self.ui, "linePhiOutName", None)
        if out_widget is not None and hasattr(out_widget, "setText"):
            out_widget.setText("PHIE")

        self._sync_porosity_method_cards()
        self._append_porosity_activity("Porosity panel reset")
        self.refresh_porosity_workspace()

    def compute_sw(self):
        import pandas as pd

        well = self.data._get_current_well()
        if not well:
            return
        df = getattr(well, "data", None)
        if df is None:
            return

        rt_curve = self._combo_text("comboSwRt")
        if not rt_curve or rt_curve not in df.columns:
            rt_curve = "LLD" if "LLD" in df.columns else ("ILD" if "ILD" in df.columns else "")

        phi_curve = self._combo_text("comboSwPhie")
        if not phi_curve or phi_curve not in df.columns:
            for candidate in ("PHIE", "PHIT", "PHI"):
                if candidate in df.columns:
                    phi_curve = candidate
                    break

        if not phi_curve or phi_curve not in df.columns:
            self.compute_phi()
            if "PHIT" in df.columns:
                phi_curve = "PHIT"

        if not rt_curve or rt_curve not in df.columns:
            QtWidgets.QMessageBox.warning(self.ui, "Calculations", "Resistivity curve not found for Sw calculation.")
            return

        if not phi_curve or phi_curve not in df.columns:
            QtWidgets.QMessageBox.warning(self.ui, "Calculations", "Porosity curve not found for Sw calculation.")
            return

        rw = self._spin_value(("spinSwRw",), 0.05) or 0.05
        a_val = self._spin_value(("spinSwA",), 1.0) or 1.0
        m_val = self._slider_or_spin_value("sliderSwM", ("spinSwM",), 2.0)
        n_val = self._slider_or_spin_value("sliderSwN", ("spinSwN",), 2.0)
        method = (self._combo_text("comboSwMethod") or "Archie").strip()
        rsh_val = self._spin_value(("spinSwFormRw",), 2.0) or 2.0
        phi_values = pd.to_numeric(df[phi_curve], errors="coerce").to_numpy(dtype=float)
        rt_values = pd.to_numeric(df[rt_curve], errors="coerce").to_numpy(dtype=float)

        if method == "Archie":
            sw_values = saturation.compute_sw_archie(phi_values, rt_values, rw=rw, a=a_val, m=m_val, n=n_val)
        else:
            if "VSH" not in df.columns and "Vsh" not in df.columns:
                self.compute_vsh()
            vsh_col = "VSH" if "VSH" in df.columns else ("Vsh" if "Vsh" in df.columns else "")
            if not vsh_col:
                QtWidgets.QMessageBox.warning(self.ui, "Calculations", "VSH curve is required for the selected Sw method.")
                return
            vsh_values = pd.to_numeric(df[vsh_col], errors="coerce").to_numpy(dtype=float)
            if method == "Simandoux":
                sw_values = saturation.compute_sw_simandoux(
                    phi_values, rt_values, vsh_values, rw=rw, rsh=rsh_val, a=a_val, m=m_val, n=n_val
                )
            elif method == "Modified Simandoux":
                sw_values = saturation.compute_sw_modified_simandoux(
                    phi_values, rt_values, vsh_values, rw=rw, rsh=rsh_val, a=a_val, m=m_val, n=n_val
                )
            else:
                sw_values = saturation.compute_sw_indonesia(
                    phi_values, rt_values, vsh_values, rw=rw, rsh=rsh_val, a=a_val, m=m_val, n=n_val
                )

        df["SW"] = sw_values
        out_name = self._line_text("lineSwOutName") or "SW"
        if out_name != "SW":
            df[out_name] = sw_values

        self.data._refresh_views()
        self._append_sw_activity(f"Compute Sw ({method})")
        self.refresh_sw_workspace()

    def reset_sw_panel(self):
        combo = getattr(self.ui, "comboSwMethod", None)
        if combo is not None and hasattr(combo, "setCurrentText"):
            combo.setCurrentText("Archie")

        for name, value in (("spinSwRw", 0.05), ("spinSwA", 1.0)):
            widget = getattr(self.ui, name, None)
            if widget is not None and hasattr(widget, "setValue"):
                widget.setValue(value)

        for name, value in (("sliderSwM", 200), ("sliderSwN", 200), ("sliderSwFormM", 200), ("sliderSwFormN", 200)):
            widget = getattr(self.ui, name, None)
            if widget is not None and hasattr(widget, "setValue"):
                widget.setValue(value)

        line = getattr(self.ui, "lineSwOutName", None)
        if line is not None and hasattr(line, "setText"):
            line.setText("SW")

        self._append_sw_activity("Sw panel reset")
        self.refresh_sw_workspace()

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
        if not all(name in df.columns for name in ("VSH", "PHIT", "SW")):
            return

        vsh_val = self._spin_value(("spinNetPayVcl", "vshCutoffSpinBox", "spinVshCutoff"), 0.4) or 0.4
        phi_val = self._spin_value(("spinNetPayPhi", "phiCutoffSpinBox", "spinPhiCutoff"), 0.05) or 0.05
        sw_val = self._spin_value(("spinNetPaySw", "swCutoffSpinBox", "spinSwCutoff"), 0.65) or 0.65
        out_name = self._line_text("lineNetPayOut") or "NET_PAY"

        pay_flag = net_pay.compute_net_pay(
            df["VSH"].values,
            df["PHIT"].values,
            df["SW"].values,
            vsh_cut=vsh_val,
            phi_cut=phi_val,
            sw_cut=sw_val,
        )
        df["NET_PAY"] = pay_flag
        df["PayFlag"] = pay_flag
        if out_name != "NET_PAY":
            df[out_name] = pay_flag

        working = self.data._filtered_dataframe(well)
        if working is None or working.empty:
            working = df.copy()

        self.data._refresh_views()
        self._render_net_pay_results(working, vsh_val, phi_val, sw_val, out_name)

    def reset_net_pay(self):
        for name, default in (("spinNetPayVcl", 0.4), ("spinNetPayPhi", 0.05), ("spinNetPaySw", 0.65)):
            widget = getattr(self.ui, name, None)
            if widget is not None and hasattr(widget, "setValue"):
                widget.setValue(default)

        out_widget = getattr(self.ui, "lineNetPayOut", None)
        if out_widget is not None:
            out_widget.setText("NET_PAY")

        self._clear_net_pay_results()

    def _build_net_pay_workspace(self) -> None:
        tab = getattr(self.ui, "tabNetPay", None)
        if tab is None or getattr(self.ui, "_net_pay_workspace_built", False):
            return

        layout = tab.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(tab)

        preserved_widgets = {}
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is None:
                continue
            if widget.objectName() in {"comboNetPayWell", "spinNetPayVcl", "spinNetPayPhi", "spinNetPaySw", "lineNetPayOut", "btnCalcNetPay", "btnResetNetPay"}:
                widget.setParent(None)
                preserved_widgets[widget.objectName()] = widget
            else:
                widget.setParent(None)
                widget.deleteLater()

        for name, widget in preserved_widgets.items():
            setattr(self.ui, name, widget)

        main_layout = layout
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        top_row = QtWidgets.QHBoxLayout()
        top_row.setSpacing(12)

        controls_frame = QtWidgets.QFrame(tab)
        controls_frame.setStyleSheet(
            "QFrame { background:#F8FBFE; border:1px solid #D7E2EE; border-radius:14px; }"
        )
        controls_layout = QtWidgets.QVBoxLayout(controls_frame)
        controls_layout.setContentsMargins(14, 14, 14, 14)
        controls_layout.setSpacing(10)
        controls_title = QtWidgets.QLabel("Cutoff Inputs", controls_frame)
        controls_title.setStyleSheet("font-size:16px;font-weight:800;color:#24466B;")
        controls_layout.addWidget(controls_title)

        cutoff_grid = QtWidgets.QGridLayout()
        cutoff_grid.setHorizontalSpacing(10)
        cutoff_grid.setVerticalSpacing(8)
        for row, (label_text, widget_name, decimals, default) in enumerate((
            ("Vsh Cutoff", "spinNetPayVcl", 2, 0.40),
            ("PHI Cutoff", "spinNetPayPhi", 3, 0.05),
            ("Sw Cutoff", "spinNetPaySw", 2, 0.65),
        )):
            label = QtWidgets.QLabel(label_text, controls_frame)
            label.setStyleSheet("color:#355C7D;font-weight:600;")
            widget = getattr(self.ui, widget_name, None)
            if widget is not None:
                widget.setDecimals(decimals)
                widget.setSingleStep(0.01)
                widget.setMaximum(1.0)
                widget.setMinimum(0.0)
                widget.setValue(default)
            cutoff_grid.addWidget(label, row, 0)
            cutoff_grid.addWidget(widget, row, 1)
        controls_layout.addLayout(cutoff_grid)

        output_label = QtWidgets.QLabel("Output Curve", controls_frame)
        output_label.setStyleSheet("color:#355C7D;font-weight:600;")
        controls_layout.addWidget(output_label)
        out_widget = getattr(self.ui, "lineNetPayOut", None)
        if out_widget is not None:
            out_widget.setText("NET_PAY")
            controls_layout.addWidget(out_widget)

        perm_widget = getattr(self.ui, "spinNetPayPerm", None)
        if perm_widget is not None:
            perm_widget.hide()

        button_row = QtWidgets.QHBoxLayout()
        calc_btn = getattr(self.ui, "btnCalcNetPay", None)
        reset_btn = getattr(self.ui, "btnResetNetPay", None)
        if calc_btn is not None:
            calc_btn.setMinimumHeight(40)
            button_row.addWidget(calc_btn)
        if reset_btn is not None:
            reset_btn.setMinimumHeight(40)
            button_row.addWidget(reset_btn)
        controls_layout.addLayout(button_row)
        controls_layout.addStretch(1)

        self.ui.vshCutoffSpinBox = getattr(self.ui, "spinNetPayVcl", None)
        self.ui.phiCutoffSpinBox = getattr(self.ui, "spinNetPayPhi", None)
        self.ui.swCutoffSpinBox = getattr(self.ui, "spinNetPaySw", None)
        self.ui.runNetPayBtn = getattr(self.ui, "btnCalcNetPay", None)
        self.ui.resetNetPayBtn = getattr(self.ui, "btnResetNetPay", None)

        plot_frame = QtWidgets.QFrame(tab)
        plot_frame.setStyleSheet(
            "QFrame { background:#FFFFFF; border:1px solid #D7E2EE; border-radius:14px; }"
        )
        plot_layout = QtWidgets.QVBoxLayout(plot_frame)
        plot_layout.setContentsMargins(12, 12, 12, 12)
        plot_layout.setSpacing(8)
        plot_title = QtWidgets.QLabel("Pay Flag Plot", plot_frame)
        plot_title.setStyleSheet("font-size:16px;font-weight:800;color:#24466B;")
        plot_layout.addWidget(plot_title)
        self._net_pay_plot_host = QtWidgets.QWidget(plot_frame)
        self._net_pay_plot_host.setStyleSheet("background:#FFFFFF;")
        self._net_pay_plot_host.setLayout(QtWidgets.QVBoxLayout())
        self._net_pay_plot_host.layout().setContentsMargins(0, 0, 0, 0)
        plot_layout.addWidget(self._net_pay_plot_host, 1)
        self.ui.netPayPlotWidget = self._net_pay_plot_host

        summary_frame = QtWidgets.QFrame(tab)
        summary_frame.setStyleSheet(
            "QFrame { background:#F8FBFE; border:1px solid #D7E2EE; border-radius:14px; }"
        )
        summary_layout = QtWidgets.QVBoxLayout(summary_frame)
        summary_layout.setContentsMargins(14, 14, 14, 14)
        summary_layout.setSpacing(10)
        summary_title = QtWidgets.QLabel("Summary", summary_frame)
        summary_title.setStyleSheet("font-size:16px;font-weight:800;color:#24466B;")
        summary_layout.addWidget(summary_title)

        self._net_pay_summary_labels = {}
        for label_text, attr_name in (
            ("Net Pay Thickness", "netPayValueLabel"),
            ("Average PHI", "avgPhiLabel"),
            ("Average Sw", "avgSwLabel"),
            ("Pay Samples", "paySamplesLabel"),
        ):
            block = QtWidgets.QFrame(summary_frame)
            block.setStyleSheet("QFrame { background:#FFFFFF; border:1px solid #D7E2EE; border-radius:10px; }")
            block_layout = QtWidgets.QVBoxLayout(block)
            block_layout.setContentsMargins(10, 8, 10, 8)
            block_layout.setSpacing(2)
            label = QtWidgets.QLabel(label_text, block)
            label.setStyleSheet("font-size:11px;color:#5C718A;font-weight:600;")
            value = QtWidgets.QLabel("--", block)
            value.setStyleSheet("font-size:18px;color:#1F4E79;font-weight:800;")
            self._net_pay_summary_labels[attr_name] = value
            setattr(self.ui, attr_name, value)
            block_layout.addWidget(label)
            block_layout.addWidget(value)
            summary_layout.addWidget(block)

        summary_note = QtWidgets.QLabel("Ready to compute pay intervals for the active well.", summary_frame)
        summary_note.setWordWrap(True)
        summary_note.setStyleSheet(
            "background:#FFFFFF;border:1px solid #D7E2EE;border-radius:10px;padding:10px;color:#38556F;"
        )
        self.ui.lblNetPaySummaryText = summary_note
        summary_layout.addWidget(summary_note)
        summary_layout.addStretch(1)

        top_row.addWidget(controls_frame, 1)
        top_row.addWidget(plot_frame, 7)
        top_row.addWidget(summary_frame, 1)
        main_layout.addLayout(top_row, 3)

        table_frame = QtWidgets.QFrame(tab)
        table_frame.setStyleSheet(
            "QFrame { background:#FFFFFF; border:1px solid #D7E2EE; border-radius:14px; }"
        )
        table_layout = QtWidgets.QVBoxLayout(table_frame)
        table_layout.setContentsMargins(12, 12, 12, 12)
        table_layout.setSpacing(8)
        table_title = QtWidgets.QLabel("Pay Flag Table", table_frame)
        table_title.setStyleSheet("font-size:16px;font-weight:800;color:#24466B;")
        table_layout.addWidget(table_title)

        table = QtWidgets.QTableWidget(table_frame)
        table.setAlternatingRowColors(True)
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Depth", "Vsh", "PHI", "Sw", "PayFlag"])
        table.horizontalHeader().setStretchLastSection(True)
        table.setSortingEnabled(False)
        table.setStyleSheet("QTableWidget { background:#FFFFFF; }")
        self._net_pay_table = table
        self.ui.netPayTable = table
        table_layout.addWidget(table)
        main_layout.addWidget(table_frame, 2)

        self._net_pay_canvas = None
        self._net_pay_toolbar = None
        self.ui._net_pay_workspace_built = True

    def _render_net_pay_results(self, df, vsh_cut: float, phi_cut: float, sw_cut: float, out_name: str) -> None:
        import pandas as pd

        table = self._net_pay_table
        if table is not None:
            depth_col = self.data._depth_column(df)
            display = df.copy()
            for required in ("VSH", "PHIT", "SW", "NET_PAY"):
                if required not in display.columns:
                    display[required] = np.nan

            if depth_col is None or depth_col not in display.columns:
                display.insert(0, "Depth", np.arange(len(display), dtype=float))
                depth_col = "Depth"

            display = display[[depth_col, "VSH", "PHIT", "SW", "NET_PAY"]].copy()
            display.rename(columns={depth_col: "Depth", "VSH": "Vsh", "PHIT": "PHI", "SW": "Sw", "NET_PAY": "PayFlag"}, inplace=True)
            self._fill_net_pay_table(table, display)

        depth_col = self.data._depth_column(df)
        if depth_col is not None and depth_col in df.columns:
            depth_series = pd.to_numeric(df[depth_col], errors="coerce")
        else:
            depth_series = pd.Series(np.arange(len(df), dtype=float), index=df.index)

        pay_series = pd.to_numeric(df.get("NET_PAY", 0), errors="coerce").fillna(0).astype(int)
        pay_mask = pay_series.to_numpy(dtype=int) == 1

        vsh_values = pd.to_numeric(df.get("VSH"), errors="coerce")
        phi_values = pd.to_numeric(df.get("PHIT"), errors="coerce")
        sw_values = pd.to_numeric(df.get("SW"), errors="coerce")

        net_thickness = self._estimate_thickness(depth_series.to_numpy(dtype=float), pay_mask)
        pay_count = int(pay_mask.sum())
        average_phi = float(np.nanmean(phi_values.to_numpy(dtype=float)[pay_mask])) if pay_count else 0.0
        average_sw = float(np.nanmean(sw_values.to_numpy(dtype=float)[pay_mask])) if pay_count else 0.0
        pay_ratio = 100.0 * pay_count / max(int(len(df)), 1)

        self._set_label_text("netPayValueLabel", f"{net_thickness:.2f} m")
        self._set_label_text("avgPhiLabel", f"{average_phi:.3f}")
        self._set_label_text("avgSwLabel", f"{average_sw:.3f}")
        self._set_label_text("paySamplesLabel", f"{pay_count:,} samples ({pay_ratio:.1f}%)")
        self._set_label_text(
            "lblNetPaySummaryText",
            f"Cutoffs applied: Vsh ≤ {vsh_cut:.2f}, PHI ≥ {phi_cut:.3f}, Sw ≤ {sw_cut:.2f}. Output curve: {out_name}.",
        )

        self._render_net_pay_plot(df, depth_series, pay_mask, vsh_cut, phi_cut, sw_cut)

    def _render_net_pay_plot(self, df, depth_series, pay_mask, vsh_cut: float, phi_cut: float, sw_cut: float) -> None:
        import pandas as pd

        try:
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas  # type: ignore
            from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar  # type: ignore
            from matplotlib.figure import Figure
        except Exception:
            return

        host = self._net_pay_plot_host
        if host is None:
            return

        layout = host.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(host)
            layout.setContentsMargins(0, 0, 0, 0)

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        depth = np.asarray(depth_series, dtype=float)
        vsh = pd.to_numeric(df.get("VSH"), errors="coerce").to_numpy(dtype=float)
        phi = pd.to_numeric(df.get("PHIT"), errors="coerce").to_numpy(dtype=float)
        sw = pd.to_numeric(df.get("SW"), errors="coerce").to_numpy(dtype=float)
        flag = np.asarray(pay_mask, dtype=int)

        fig = Figure(figsize=(7.0, 8.0), dpi=100)
        fig.patch.set_facecolor("white")
        ax_logs = fig.add_subplot(2, 1, 1)
        ax_flag = fig.add_subplot(2, 1, 2, sharey=ax_logs)

        ax_logs.plot(vsh, depth, color="#C2410C", linewidth=1.1, label="Vsh")
        ax_logs.plot(phi, depth, color="#2563EB", linewidth=1.1, label="PHI")
        ax_logs.plot(sw, depth, color="#0F766E", linewidth=1.1, label="Sw")
        ax_logs.axvline(vsh_cut, color="#C2410C", linestyle="--", linewidth=0.9, alpha=0.8)
        ax_logs.axvline(phi_cut, color="#2563EB", linestyle="--", linewidth=0.9, alpha=0.8)
        ax_logs.axvline(sw_cut, color="#0F766E", linestyle="--", linewidth=0.9, alpha=0.8)
        ax_logs.invert_yaxis()
        ax_logs.set_xlabel("Normalized value", fontsize=9, color="#24466B")
        ax_logs.set_ylabel("Depth", fontsize=9, color="#24466B")
        ax_logs.grid(True, linestyle="--", alpha=0.25)
        ax_logs.legend(loc="upper right", fontsize=8, frameon=False)
        ax_logs.set_title("Cutoff Curves", fontsize=10, color="#24466B")

        ax_flag.step(flag, depth, where="mid", color="#1F4E79", linewidth=1.2)
        ax_flag.fill_betweenx(depth, 0, flag, step="mid", color="#90CDF4", alpha=0.8)
        ax_flag.invert_yaxis()
        ax_flag.set_xlim(-0.05, 1.05)
        ax_flag.set_xlabel("PayFlag", fontsize=9, color="#24466B")
        ax_flag.set_ylabel("Depth", fontsize=9, color="#24466B")
        ax_flag.set_yticklabels([])
        ax_flag.grid(True, axis="x", linestyle="--", alpha=0.25)
        ax_flag.set_title("Pay Flag Interval", fontsize=10, color="#24466B")

        fig.tight_layout()

        canvas = FigureCanvas(fig)
        canvas.setStyleSheet("background:#FFFFFF;")
        toolbar = NavigationToolbar(canvas, host)
        toolbar.setStyleSheet("QToolBar { background:#F8FBFE; border:0; border-bottom:1px solid #D7E2EE; }")
        layout.addWidget(toolbar)
        layout.addWidget(canvas, 1)
        canvas.draw_idle()
        self._net_pay_canvas = canvas
        self._net_pay_toolbar = toolbar

    def _fill_net_pay_table(self, table, df) -> None:
        import pandas as pd

        table.setRowCount(len(df))
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Depth", "Vsh", "PHI", "Sw", "PayFlag"])
        for row_index, (_, row) in enumerate(df.iterrows()):
            for column_index, column_name in enumerate(["Depth", "Vsh", "PHI", "Sw", "PayFlag"]):
                value = row.get(column_name, "")
                if column_name == "PayFlag":
                    text = str(int(value)) if pd.notna(value) else ""
                else:
                    text = self._format_value(value, column_name)
                item = QtWidgets.QTableWidgetItem(text)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
                table.setItem(row_index, column_index, item)
        table.resizeColumnsToContents()

    def _clear_net_pay_results(self) -> None:
        for name in ("netPayValueLabel", "avgPhiLabel", "avgSwLabel", "paySamplesLabel"):
            self._set_label_text(name, "--")
        self._set_label_text("lblNetPaySummaryText", "Ready to compute pay intervals for the active well.")
        if self._net_pay_table is not None:
            self._net_pay_table.clearContents()
            self._net_pay_table.setRowCount(0)
        if self._net_pay_plot_host is not None and self._net_pay_plot_host.layout() is not None:
            layout = self._net_pay_plot_host.layout()
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()

    def _estimate_thickness(self, depth_values, pay_mask) -> float:
        depth = np.asarray(depth_values, dtype=float)
        depth = depth[np.isfinite(depth)]
        if depth.size < 2:
            return float(pay_mask.sum())
        steps = np.abs(np.diff(depth))
        steps = steps[np.isfinite(steps) & (steps > 0)]
        step = float(np.nanmedian(steps)) if steps.size else 1.0
        return float(pay_mask.sum() * step)

    def _build_sw_workspace(self) -> None:
        if getattr(self.ui, "_sw_workspace_built", False):
            return

        tab = getattr(self.ui, "tabWaterSaturation", None)
        if tab is None:
            return

        layout = tab.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(tab)

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        panel_style = "QFrame { background:#FFFFFF; border:1px solid #D7E2EE; border-radius:12px; }"
        soft_style = "QFrame { background:#F7FAFD; border:1px solid #D7E2EE; border-radius:10px; }"
        field_style = "QLineEdit, QComboBox, QDoubleSpinBox { background:#FFFFFF; border:1px solid #C9D7E6; border-radius:8px; padding:5px 8px; min-height:26px; }"

        main_row = QtWidgets.QHBoxLayout()
        main_row.setSpacing(12)

        left_panel = QtWidgets.QFrame(tab)
        left_panel.setMinimumWidth(320)
        left_panel.setMaximumWidth(360)
        left_panel.setStyleSheet(panel_style)
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)

        left_header = QtWidgets.QLabel("Archie Parameters", left_panel)
        left_header.setStyleSheet("background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #2F6FB3, stop:1 #4A8ACE);color:#FFFFFF;border-radius:8px;padding:8px 10px;font-size:16px;font-weight:800;")
        left_layout.addWidget(left_header)

        self.ui.comboSwWell = QtWidgets.QComboBox(left_panel)
        self.ui.comboSwWell.setStyleSheet(field_style)
        left_layout.addWidget(self._build_sw_field(left_panel, "Well", self.ui.comboSwWell))

        self.ui.comboSwMethod = QtWidgets.QComboBox(left_panel)
        self.ui.comboSwMethod.setStyleSheet(field_style)
        self.ui.comboSwMethod.addItems(["Archie", "Simandoux", "Modified Simandoux", "Indonesia"])
        left_layout.addWidget(self._build_sw_field(left_panel, "Method", self.ui.comboSwMethod))

        resistivity_frame = self._build_sw_group(left_panel, "Resistivity Curve")
        resistivity_layout = resistivity_frame.layout()
        self.ui.spinSwRw = QtWidgets.QDoubleSpinBox(resistivity_frame)
        self.ui.spinSwRw.setDecimals(5)
        self.ui.spinSwRw.setRange(0.001, 10.0)
        self.ui.spinSwRw.setValue(0.05000)
        self.ui.spinSwRw.setStyleSheet(field_style)
        resistivity_layout.addWidget(self._build_sw_field(resistivity_frame, "Rw (ohm.m)", self.ui.spinSwRw))

        a_row = QtWidgets.QWidget(resistivity_frame)
        a_layout = QtWidgets.QHBoxLayout(a_row)
        a_layout.setContentsMargins(0, 0, 0, 0)
        a_layout.setSpacing(6)
        self.ui.spinSwA = QtWidgets.QDoubleSpinBox(a_row)
        self.ui.spinSwA.setDecimals(3)
        self.ui.spinSwA.setRange(0.1, 3.0)
        self.ui.spinSwA.setValue(1.0)
        self.ui.spinSwA.setStyleSheet(field_style)
        clear_a_btn = QtWidgets.QToolButton(a_row)
        clear_a_btn.setText("x")
        clear_a_btn.setToolTip("Reset a to default")
        clear_a_btn.clicked.connect(lambda: self.ui.spinSwA.setValue(1.0))
        a_layout.addWidget(self.ui.spinSwA, 1)
        a_layout.addWidget(clear_a_btn, 0)
        resistivity_layout.addWidget(self._build_sw_field(resistivity_frame, "a (Tortuosity)", a_row))

        m_widget, self.ui.sliderSwM = self._build_sw_slider(resistivity_frame, 2.0)
        resistivity_layout.addWidget(self._build_sw_field(resistivity_frame, "m (Cementation)", m_widget))
        n_widget, self.ui.sliderSwN = self._build_sw_slider(resistivity_frame, 2.0)
        resistivity_layout.addWidget(self._build_sw_field(resistivity_frame, "n (Saturation)", n_widget))
        left_layout.addWidget(resistivity_frame)

        formation_frame = self._build_sw_group(left_panel, "Formation Properties")
        formation_layout = formation_frame.layout()
        self.ui.spinSwFormRw = QtWidgets.QDoubleSpinBox(formation_frame)
        self.ui.spinSwFormRw.setDecimals(3)
        self.ui.spinSwFormRw.setRange(0.001, 10.0)
        self.ui.spinSwFormRw.setValue(1.000)
        self.ui.spinSwFormRw.setStyleSheet(field_style)
        formation_layout.addWidget(self._build_sw_field(formation_frame, "Rw (ohm.m)", self.ui.spinSwFormRw))
        form_m_widget, self.ui.sliderSwFormM = self._build_sw_slider(formation_frame, 2.0)
        formation_layout.addWidget(self._build_sw_field(formation_frame, "m (Cementation)", form_m_widget))
        form_n_widget, self.ui.sliderSwFormN = self._build_sw_slider(formation_frame, 2.0)
        formation_layout.addWidget(self._build_sw_field(formation_frame, "n (Saturation)", form_n_widget))
        left_layout.addWidget(formation_frame)

        por_frame = self._build_sw_group(left_panel, "Porosity")
        por_layout = por_frame.layout()
        self.ui.comboSwPhie = QtWidgets.QComboBox(por_frame)
        self.ui.comboSwPhie.setStyleSheet(field_style)
        por_layout.addWidget(self._build_sw_field(por_frame, "PHIE Curve", self.ui.comboSwPhie))
        left_layout.addWidget(por_frame)

        action_row = QtWidgets.QHBoxLayout()
        self.ui.btnCalcSw = QtWidgets.QPushButton("Compute Sw", left_panel)
        self.ui.btnCalcSw.setMinimumHeight(38)
        self.ui.btnCalcSw.setStyleSheet("QPushButton { background:#2B6CB0; color:#FFFFFF; border:none; border-radius:9px; font-weight:800; } QPushButton:hover { background:#245C96; }")
        self.ui.btnResetSw = QtWidgets.QPushButton("Reset", left_panel)
        self.ui.btnResetSw.setMinimumHeight(38)
        self.ui.btnResetSw.setStyleSheet("QPushButton { background:#EDF3FA; color:#355C7D; border:1px solid #C9D7E6; border-radius:9px; font-weight:700; }")
        self.ui.btnResetSw.clicked.connect(self.reset_sw_panel)
        action_row.addWidget(self.ui.btnCalcSw, 2)
        action_row.addWidget(self.ui.btnResetSw, 1)
        left_layout.addLayout(action_row)

        activity_frame = QtWidgets.QFrame(left_panel)
        activity_frame.setStyleSheet(soft_style)
        activity_layout = QtWidgets.QVBoxLayout(activity_frame)
        activity_layout.setContentsMargins(8, 8, 8, 8)
        activity_layout.setSpacing(6)
        activity_title = QtWidgets.QLabel("Activity", activity_frame)
        activity_title.setStyleSheet("font-size:12px;font-weight:800;color:#355C7D;")
        self._sw_activity_list = QtWidgets.QListWidget(activity_frame)
        self._sw_activity_list.setStyleSheet("QListWidget { background:#FFFFFF; border:1px solid #D7E2EE; border-radius:8px; } QListWidget::item { padding:6px 4px; }")
        activity_layout.addWidget(activity_title)
        activity_layout.addWidget(self._sw_activity_list)
        left_layout.addWidget(activity_frame, 1)

        right_col = QtWidgets.QVBoxLayout()
        right_col.setSpacing(10)

        kpi_frame = QtWidgets.QFrame(tab)
        kpi_frame.setStyleSheet(panel_style)
        kpi_layout = QtWidgets.QHBoxLayout(kpi_frame)
        kpi_layout.setContentsMargins(10, 10, 10, 10)
        kpi_layout.setSpacing(8)
        self._sw_kpi_labels = {}
        for key, title, value, color in (
            ("avg", "Sw Avg", "0.42", "#2B6CB0"),
            ("min", "Sw Min", "0.18", "#0F8B8D"),
            ("max", "Sw Max", "0.85", "#117A65"),
            ("net", "Net Pay", "38 m", "#2E8B57"),
        ):
            card = QtWidgets.QFrame(kpi_frame)
            card.setStyleSheet("QFrame { background:#F8FBFE; border:1px solid #D7E2EE; border-radius:10px; }")
            card_layout = QtWidgets.QVBoxLayout(card)
            card_layout.setContentsMargins(10, 8, 10, 8)
            card_layout.setSpacing(2)
            title_label = QtWidgets.QLabel(title, card)
            title_label.setStyleSheet("font-size:12px;color:#5C718A;font-weight:700;")
            value_label = QtWidgets.QLabel(value, card)
            value_label.setStyleSheet(f"font-size:28px;color:{color};font-weight:900;")
            self._sw_kpi_labels[key] = value_label
            card_layout.addWidget(title_label)
            card_layout.addWidget(value_label)
            kpi_layout.addWidget(card)
        right_col.addWidget(kpi_frame, 0)

        body_row = QtWidgets.QHBoxLayout()
        body_row.setSpacing(10)

        plots_frame = QtWidgets.QFrame(tab)
        plots_frame.setStyleSheet(panel_style)
        plots_layout = QtWidgets.QVBoxLayout(plots_frame)
        plots_layout.setContentsMargins(10, 10, 10, 10)
        plots_layout.setSpacing(8)
        self.ui.tabsSw = QtWidgets.QTabWidget(plots_frame)
        self.ui.tabsSw.setStyleSheet(
            "QTabWidget::pane { border:1px solid #D7E2EE; border-radius:10px; background:#FFFFFF; }"
            "QTabBar::tab { background:#EDF3FA; color:#4D6680; padding:8px 14px; margin-right:4px; border-top-left-radius:8px; border-top-right-radius:8px; }"
            "QTabBar::tab:selected { background:#2B6CB0; color:#FFFFFF; font-weight:700; }"
        )
        self.ui.tabSwLog = QtWidgets.QWidget(self.ui.tabsSw)
        self.ui.tabSwCrossplot = QtWidgets.QWidget(self.ui.tabsSw)
        self.ui.tabSwQC = QtWidgets.QWidget(self.ui.tabsSw)
        self.ui.tabsSw.addTab(self.ui.tabSwLog, "Log View")
        self.ui.tabsSw.addTab(self.ui.tabSwCrossplot, "Crossplot (Rn vs PHIE)")
        self.ui.tabsSw.addTab(self.ui.tabSwQC, "QC")
        for page_name, page_widget in (("log", self.ui.tabSwLog), ("cross", self.ui.tabSwCrossplot), ("qc", self.ui.tabSwQC)):
            page_layout = QtWidgets.QVBoxLayout(page_widget)
            page_layout.setContentsMargins(0, 0, 0, 0)
            page_layout.setSpacing(0)
            host = QtWidgets.QFrame(page_widget)
            host.setStyleSheet(soft_style)
            host.setMinimumHeight(420)
            page_layout.addWidget(host)
            if page_name == "log":
                self._sw_log_host = host
            elif page_name == "cross":
                self._sw_crossplot_host = host
            else:
                self._sw_qc_host = host
        plots_layout.addWidget(self.ui.tabsSw, 1)

        bottom_bar = QtWidgets.QFrame(plots_frame)
        bottom_bar.setStyleSheet("QFrame { background:#F7FAFD; border:1px solid #D7E2EE; border-radius:10px; }")
        bottom_layout = QtWidgets.QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(10, 8, 10, 8)
        bottom_layout.setSpacing(8)
        self.ui.btnSwComputeBottom = QtWidgets.QPushButton("Compute Sw", bottom_bar)
        self.ui.btnSwComputeBottom.setMinimumHeight(34)
        self.ui.btnSwComputeBottom.setStyleSheet("QPushButton { background:#2B6CB0; color:#FFFFFF; border:none; border-radius:8px; font-weight:800; }")
        self.ui.btnSwComputeBottom.clicked.connect(self.compute_sw)
        self.ui.btnSaveSw = QtWidgets.QPushButton("Save Curve", bottom_bar)
        self.ui.btnSaveSw.setMinimumHeight(34)
        self.ui.btnSaveSw.setStyleSheet("QPushButton { background:#FFFFFF; color:#355C7D; border:1px solid #C9D7E6; border-radius:8px; font-weight:700; }")
        self.ui.btnExportSw = QtWidgets.QPushButton("Export Results", bottom_bar)
        self.ui.btnExportSw.setMinimumHeight(34)
        self.ui.btnExportSw.setStyleSheet("QPushButton { background:#FFFFFF; color:#355C7D; border:1px solid #C9D7E6; border-radius:8px; font-weight:700; }")
        self.ui.btnSaveSw.clicked.connect(lambda: QtWidgets.QMessageBox.information(self.ui, "Sw", "Curve saved to current well dataset."))
        self.ui.btnExportSw.clicked.connect(lambda: QtWidgets.QMessageBox.information(self.ui, "Sw", "Export is ready for integration."))
        bottom_layout.addWidget(self.ui.btnSwComputeBottom)
        bottom_layout.addWidget(self.ui.btnSaveSw)
        bottom_layout.addWidget(self.ui.btnExportSw)
        bottom_layout.addStretch(1)
        plots_layout.addWidget(bottom_bar, 0)

        side_frame = QtWidgets.QFrame(tab)
        side_frame.setMinimumWidth(260)
        side_frame.setStyleSheet(panel_style)
        side_layout = QtWidgets.QVBoxLayout(side_frame)
        side_layout.setContentsMargins(10, 10, 10, 10)
        side_layout.setSpacing(8)
        side_title = QtWidgets.QLabel("Water Saturation (Sw)", side_frame)
        side_title.setStyleSheet("font-size:18px;font-weight:900;color:#24466B;")
        side_layout.addWidget(side_title)

        mini_summary = QtWidgets.QFrame(side_frame)
        mini_summary.setStyleSheet(soft_style)
        mini_layout = QtWidgets.QHBoxLayout(mini_summary)
        mini_layout.setContentsMargins(8, 8, 8, 8)
        mini_layout.setSpacing(8)
        self._sw_side_summary_labels = {}
        for key, title in (("avg", "Sw Avg"), ("min", "Sw Min"), ("max", "N-O Max")):
            block = QtWidgets.QFrame(mini_summary)
            block.setStyleSheet("QFrame { background:#FFFFFF; border:1px solid #D7E2EE; border-radius:8px; }")
            block_layout = QtWidgets.QVBoxLayout(block)
            block_layout.setContentsMargins(8, 6, 8, 6)
            block_layout.setSpacing(2)
            t = QtWidgets.QLabel(title, block)
            t.setStyleSheet("font-size:10px;color:#6C7E90;font-weight:700;")
            v = QtWidgets.QLabel("--", block)
            v.setStyleSheet("font-size:26px;color:#1F4E79;font-weight:900;")
            self._sw_side_summary_labels[key] = v
            block_layout.addWidget(t)
            block_layout.addWidget(v)
            mini_layout.addWidget(block)
        side_layout.addWidget(mini_summary)

        quality_box = QtWidgets.QFrame(side_frame)
        quality_box.setStyleSheet(soft_style)
        quality_layout = QtWidgets.QVBoxLayout(quality_box)
        quality_layout.setContentsMargins(8, 8, 8, 8)
        quality_layout.setSpacing(6)
        quality_title = QtWidgets.QLabel("Data Quality", quality_box)
        quality_title.setStyleSheet("font-size:16px;font-weight:900;color:#24466B;")
        quality_layout.addWidget(quality_title)
        self._sw_quality_labels = {}
        for key, text in (("rt", "Rt available"), ("phi", "PHIE available"), ("rw", "Formation Rw constant assumption"), ("unc", "High uncertainty zone detected")):
            label = QtWidgets.QLabel(text, quality_box)
            label.setStyleSheet("font-size:12px;color:#355C7D;")
            quality_layout.addWidget(label)
            self._sw_quality_labels[key] = label
        side_layout.addWidget(quality_box)
        side_layout.addStretch(1)

        body_row.addWidget(plots_frame, 1)
        body_row.addWidget(side_frame, 0)
        right_col.addLayout(body_row, 1)

        main_row.addWidget(left_panel, 0)
        main_row.addLayout(right_col, 1)
        layout.addLayout(main_row)

        self.ui.comboSwWell.currentTextChanged.connect(lambda *_: self.refresh_sw_workspace())
        self.ui.comboSwRt.currentTextChanged.connect(lambda *_: self.refresh_sw_workspace())
        self.ui.comboSwPhie.currentTextChanged.connect(lambda *_: self.refresh_sw_workspace())
        self.ui.refresh_sw_tab = self.refresh_sw_workspace

        if not self._sw_activity_items:
            self._sw_activity_items = [
                "LAS loaded for well GOR-1",
                "PHIE curve selected",
                "Formation Rw constant assumption",
            ]

        self.ui._sw_workspace_built = True
        self._populate_sw_wells()
        self.refresh_sw_workspace()

    def _build_sw_group(self, parent, title: str) -> QtWidgets.QFrame:
        frame = QtWidgets.QFrame(parent)
        frame.setStyleSheet("QFrame { background:#F8FBFE; border:1px solid #D7E2EE; border-radius:10px; }")
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        title_label = QtWidgets.QLabel(title, frame)
        title_label.setStyleSheet("font-size:14px;font-weight:800;color:#274B72;")
        layout.addWidget(title_label)
        return frame

    def _build_sw_field(self, parent, label_text: str, widget: QtWidgets.QWidget) -> QtWidgets.QWidget:
        row = QtWidgets.QWidget(parent)
        row_layout = QtWidgets.QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        label = QtWidgets.QLabel(label_text, row)
        label.setStyleSheet("color:#355C7D;font-weight:700;")
        row_layout.addWidget(label, 1)
        row_layout.addWidget(widget, 2)
        return row

    def _build_sw_slider(self, parent, value: float) -> tuple[QtWidgets.QWidget, QtWidgets.QSlider]:
        row = QtWidgets.QWidget(parent)
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal, row)
        slider.setRange(100, 300)
        slider.setValue(int(value * 100.0))
        slider.setSingleStep(1)
        value_label = QtWidgets.QLabel(f"{value:.3f}", row)
        value_label.setFixedWidth(48)
        value_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        value_label.setStyleSheet("color:#355C7D;font-weight:700;")
        slider.valueChanged.connect(lambda val, lbl=value_label: lbl.setText(f"{val / 100.0:.3f}"))
        layout.addWidget(slider, 1)
        layout.addWidget(value_label, 0)
        return row, slider

    def _slider_or_spin_value(self, slider_name: str, spin_names: tuple[str, ...], default: float) -> float:
        slider = getattr(self.ui, slider_name, None)
        if slider is not None and hasattr(slider, "value"):
            try:
                return float(slider.value()) / 100.0
            except Exception:
                pass
        value = self._spin_value(spin_names, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    def _populate_sw_wells(self) -> None:
        combo = getattr(self.ui, "comboSwWell", None)
        if combo is None:
            return

        current_text = combo.currentText().strip()
        wells = sorted(getattr(self.data, "_wells", {}).keys())
        combo.blockSignals(True)
        combo.clear()
        if wells:
            combo.addItems(wells)
            target = current_text if current_text in wells else getattr(self.data, "_current_well", None)
            if target in wells:
                combo.setCurrentText(target)
            elif combo.count():
                combo.setCurrentIndex(0)
        else:
            combo.addItem("No wells loaded")
        combo.blockSignals(False)

    def _populate_sw_curve_selectors(self, df) -> None:
        rt_combo = getattr(self.ui, "comboSwRt", None)
        phi_combo = getattr(self.ui, "comboSwPhie", None)
        if rt_combo is None or phi_combo is None:
            return

        columns = [str(c) for c in getattr(df, "columns", [])]
        rt_candidates = [c for c in columns if any(token in c.upper() for token in ("LLD", "ILD", "RT", "RES"))]
        phi_candidates = [c for c in columns if any(token in c.upper() for token in ("PHIE", "PHIT", "PHI"))]

        current_rt = rt_combo.currentText().strip()
        current_phi = phi_combo.currentText().strip()

        rt_combo.blockSignals(True)
        rt_combo.clear()
        rt_combo.addItems(rt_candidates or ["LLD"])
        if current_rt in rt_candidates:
            rt_combo.setCurrentText(current_rt)
        rt_combo.blockSignals(False)

        phi_combo.blockSignals(True)
        phi_combo.clear()
        phi_combo.addItems(phi_candidates or ["PHIE"])
        if current_phi in phi_candidates:
            phi_combo.setCurrentText(current_phi)
        phi_combo.blockSignals(False)

    def refresh_sw_workspace(self) -> None:
        import pandas as pd

        if not getattr(self.ui, "_sw_workspace_built", False):
            return

        self._populate_sw_wells()
        well = self.data._get_current_well()
        if well is None:
            self._show_sw_placeholder(self._sw_log_host, "Log View", "Load a well to display water saturation diagnostics.")
            self._show_sw_placeholder(self._sw_crossplot_host, "Crossplot", "Load a well to display Rt vs PHIE crossplot.")
            self._show_sw_placeholder(self._sw_qc_host, "QC", "Quality summary will appear after loading curves.")
            self._refresh_sw_activity_log()
            return

        df = getattr(well, "data", None)
        if df is None or getattr(df, "empty", True):
            self._show_sw_placeholder(self._sw_log_host, "Log View", "No usable well data found.")
            self._show_sw_placeholder(self._sw_crossplot_host, "Crossplot", "No usable well data found.")
            self._show_sw_placeholder(self._sw_qc_host, "QC", "No usable well data found.")
            self._refresh_sw_activity_log()
            return

        self._populate_sw_curve_selectors(df)

        visible = self.data._filtered_dataframe(well)
        if visible is None or getattr(visible, "empty", True):
            visible = df.copy()

        depth_col = self.data._depth_column(visible)
        rt_col = self._combo_text("comboSwRt")
        phi_col = self._combo_text("comboSwPhie")

        sw_col = self._line_text("lineSwOutName") or "SW"
        if sw_col in visible.columns:
            sw_series = pd.to_numeric(visible[sw_col], errors="coerce")
        elif "SW" in visible.columns:
            sw_series = pd.to_numeric(visible["SW"], errors="coerce")
        elif rt_col in visible.columns and phi_col in visible.columns:
            rw = self._spin_value(("spinSwRw",), 0.05) or 0.05
            a_val = self._spin_value(("spinSwA",), 1.0) or 1.0
            m_val = self._slider_or_spin_value("sliderSwM", ("spinSwM",), 2.0)
            n_val = self._slider_or_spin_value("sliderSwN", ("spinSwN",), 2.0)
            method = (self._combo_text("comboSwMethod") or "Archie").strip()
            rsh_val = self._spin_value(("spinSwFormRw",), 2.0) or 2.0
            phi_vals = pd.to_numeric(visible[phi_col], errors="coerce").to_numpy(dtype=float)
            rt_vals = pd.to_numeric(visible[rt_col], errors="coerce").to_numpy(dtype=float)
            if method == "Archie":
                sw_values = saturation.compute_sw_archie(phi_vals, rt_vals, rw=rw, a=a_val, m=m_val, n=n_val)
            else:
                vsh_col = "VSH" if "VSH" in visible.columns else ("Vsh" if "Vsh" in visible.columns else "")
                if vsh_col:
                    vsh_vals = pd.to_numeric(visible[vsh_col], errors="coerce").to_numpy(dtype=float)
                    if method == "Simandoux":
                        sw_values = saturation.compute_sw_simandoux(
                            phi_vals, rt_vals, vsh_vals, rw=rw, rsh=rsh_val, a=a_val, m=m_val, n=n_val
                        )
                    elif method == "Modified Simandoux":
                        sw_values = saturation.compute_sw_modified_simandoux(
                            phi_vals, rt_vals, vsh_vals, rw=rw, rsh=rsh_val, a=a_val, m=m_val, n=n_val
                        )
                    else:
                        sw_values = saturation.compute_sw_indonesia(
                            phi_vals, rt_vals, vsh_vals, rw=rw, rsh=rsh_val, a=a_val, m=m_val, n=n_val
                        )
                else:
                    sw_values = saturation.compute_sw_archie(phi_vals, rt_vals, rw=rw, a=a_val, m=m_val, n=n_val)
            sw_series = pd.Series(sw_values, index=visible.index)
        else:
            sw_series = pd.Series(dtype=float)

        self._set_sw_kpis(visible, sw_series, depth_col, phi_col)
        self._set_sw_quality(visible, rt_col, phi_col)
        self._render_sw_log_view(visible, depth_col, rt_col, sw_series, phi_col)
        self._render_sw_crossplot(visible, rt_col, phi_col, sw_series)
        self._render_sw_qc_panel(visible, rt_col, phi_col, sw_series)
        self._refresh_sw_activity_log()

    def _set_sw_kpis(self, df, sw_series, depth_col: str | None, phi_col: str) -> None:
        import pandas as pd

        if sw_series is None or getattr(sw_series, "empty", True):
            for label in self._sw_kpi_labels.values():
                label.setText("--")
            for label in self._sw_side_summary_labels.values():
                label.setText("--")
            return

        valid_sw = pd.to_numeric(sw_series, errors="coerce").dropna()
        if valid_sw.empty:
            for label in self._sw_kpi_labels.values():
                label.setText("--")
            for label in self._sw_side_summary_labels.values():
                label.setText("--")
            return

        if depth_col and depth_col in df.columns:
            depth = pd.to_numeric(df[depth_col], errors="coerce")
        else:
            depth = pd.Series(np.arange(len(df), dtype=float), index=df.index)

        phi_series = pd.to_numeric(df[phi_col], errors="coerce") if phi_col in df.columns else pd.Series(np.nan, index=df.index)
        pay_mask = (pd.to_numeric(sw_series, errors="coerce") <= 0.60) & (phi_series >= 0.10)
        thickness = self._estimate_thickness(depth.to_numpy(dtype=float), pay_mask.fillna(False).to_numpy(dtype=bool))

        self._sw_kpi_labels["avg"].setText(f"{valid_sw.mean():.2f}")
        self._sw_kpi_labels["min"].setText(f"{valid_sw.min():.2f}")
        self._sw_kpi_labels["max"].setText(f"{valid_sw.max():.2f}")
        self._sw_kpi_labels["net"].setText(f"{thickness:.0f} m")

        if "avg" in self._sw_side_summary_labels:
            self._sw_side_summary_labels["avg"].setText(f"{valid_sw.mean():.2f}")
        if "min" in self._sw_side_summary_labels:
            self._sw_side_summary_labels["min"].setText(f"{valid_sw.min():.2f}")
        if "max" in self._sw_side_summary_labels:
            self._sw_side_summary_labels["max"].setText(f"{valid_sw.max():.2f}")

    def _set_sw_quality(self, df, rt_col: str, phi_col: str) -> None:
        import pandas as pd

        rt_ok = rt_col in df.columns and pd.to_numeric(df[rt_col], errors="coerce").dropna().size > 0
        phi_ok = phi_col in df.columns and pd.to_numeric(df[phi_col], errors="coerce").dropna().size > 0

        if "rt" in self._sw_quality_labels:
            self._sw_quality_labels["rt"].setText(("✔ " if rt_ok else "⚠ ") + "Rt available" if rt_ok else "⚠ Rt missing")
        if "phi" in self._sw_quality_labels:
            self._sw_quality_labels["phi"].setText(("✔ " if phi_ok else "⚠ ") + "PHIE available" if phi_ok else "⚠ PHIE missing")
        if "rw" in self._sw_quality_labels:
            self._sw_quality_labels["rw"].setText("⚠ Formation Rw constant assumption set")
        if "unc" in self._sw_quality_labels:
            self._sw_quality_labels["unc"].setText("⚠ High uncertainty zone detected" if rt_ok and phi_ok else "⚠ Uncertainty elevated due to missing curves")

    def _show_sw_placeholder(self, host, title: str, message: str) -> None:
        if host is None:
            return
        layout = host.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(host)
            layout.setContentsMargins(8, 8, 8, 8)
        self._clear_layout(layout)
        label = QtWidgets.QLabel(f"{title}\n\n{message}", host)
        label.setWordWrap(True)
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setStyleSheet("background:#F8FBFE;border:1px dashed #C9D7E6;border-radius:10px;color:#6C7E90;padding:16px;")
        layout.addWidget(label, 1)

    def _refresh_sw_activity_log(self) -> None:
        if self._sw_activity_list is None:
            return
        if not self._sw_activity_items:
            self._sw_activity_items = ["LAS loaded", "PHIE selected", "Rw assumption active"]
        self._sw_activity_list.clear()
        for item in self._sw_activity_items[-8:]:
            self._sw_activity_list.addItem(item)

    def _append_sw_activity(self, message: str) -> None:
        text = message.strip()
        if not text:
            return
        self._sw_activity_items.append(text)
        self._sw_activity_items = self._sw_activity_items[-8:]
        self._refresh_sw_activity_log()

    def _render_sw_log_view(self, df, depth_col: str | None, rt_col: str, sw_series, phi_col: str) -> None:
        import numpy as np
        import pandas as pd

        if depth_col is None or depth_col not in df.columns:
            depth = np.arange(len(df), dtype=float)
            depth_label = "Index"
        else:
            depth = pd.to_numeric(df[depth_col], errors="coerce").to_numpy(dtype=float)
            depth_label = depth_col

        gr_col = self._pick_gr_curve_name(df)
        gr = pd.to_numeric(df[gr_col], errors="coerce").to_numpy(dtype=float) if gr_col and gr_col in df.columns else None
        rt = pd.to_numeric(df[rt_col], errors="coerce").to_numpy(dtype=float) if rt_col in df.columns else None
        phi = pd.to_numeric(df[phi_col], errors="coerce").to_numpy(dtype=float) if phi_col in df.columns else None
        sw = pd.to_numeric(sw_series, errors="coerce").to_numpy(dtype=float) if sw_series is not None else np.array([])

        mask = np.isfinite(depth)
        if rt is not None:
            mask &= np.isfinite(rt)
        if sw.size:
            mask &= np.isfinite(sw)

        if not np.any(mask):
            self._show_sw_placeholder(self._sw_log_host, "Log View", "No valid samples available for Sw track rendering.")
            return

        depth = depth[mask]
        if gr is not None:
            gr = gr[mask]
        if rt is not None:
            rt = rt[mask]
        if phi is not None:
            phi = phi[mask]
        if sw.size:
            sw = sw[mask]

        if sw.size == 0:
            self._show_sw_placeholder(self._sw_log_host, "Log View", "Sw has not been computed for the current selection.")
            return

        try:
            from matplotlib.figure import Figure
        except Exception:
            self._show_sw_placeholder(self._sw_log_host, "Log View", "Matplotlib is unavailable in this environment.")
            return

        fig = Figure(figsize=(11.0, 6.2), dpi=100, constrained_layout=True)
        fig.patch.set_facecolor("white")
        axes = fig.subplots(1, 3, sharey=True)
        if not isinstance(axes, (list, tuple, np.ndarray)):
            axes = [axes]
        ax_gr, ax_rt, ax_sw = axes

        if gr is not None:
            ax_gr.plot(gr, depth, color="#D4A72C", linewidth=1.1)
            ax_gr.fill_betweenx(depth, np.nanmin(gr), gr, color="#F5E9BF", alpha=0.45)
        ax_gr.set_title("Gamma Ray", fontsize=10, color="#24466B")
        ax_gr.set_xlabel("GR", fontsize=9)
        ax_gr.grid(True, linestyle="--", alpha=0.18)

        if rt is not None:
            positive = np.where(rt > 0, rt, np.nan)
            ax_rt.plot(positive, depth, color="#2563EB", linewidth=1.1)
            if np.isfinite(positive).sum() > 3:
                ax_rt.set_xscale("log")
        ax_rt.set_title("Resistivity", fontsize=10, color="#24466B")
        ax_rt.set_xlabel(rt_col or "Rt", fontsize=9)
        ax_rt.grid(True, linestyle=":", alpha=0.22)

        if sw.size:
            ax_sw.plot(sw, depth, color="#0F8B8D", linewidth=1.2)
            ax_sw.fill_betweenx(depth, 0, sw, color="#C7F1EB", alpha=0.6)
            pay_mask = sw <= 0.60
            if phi is not None:
                pay_mask &= np.nan_to_num(phi, nan=0.0) >= 0.10
            starts = np.where(np.diff(np.r_[False, pay_mask, False].astype(int)) == 1)[0]
            ends = np.where(np.diff(np.r_[False, pay_mask, False].astype(int)) == -1)[0]
            for start, end in zip(starts, ends):
                y0 = depth[start]
                y1 = depth[end - 1]
                for ax in axes:
                    ax.axhspan(min(y0, y1), max(y0, y1), color="#D8F0D6", alpha=0.18)
        ax_sw.set_xlim(0, 1)
        ax_sw.set_title("Water Saturation (Sw)", fontsize=10, color="#24466B")
        ax_sw.set_xlabel("Sw", fontsize=9)
        ax_sw.grid(True, linestyle="--", alpha=0.18)

        for ax in axes:
            ax.invert_yaxis()
            ax.set_ylabel(depth_label, fontsize=9)

        self._render_figure_to_host(self._sw_log_host, fig)

    def _render_sw_crossplot(self, df, rt_col: str, phi_col: str, sw_series) -> None:
        import pandas as pd

        if rt_col not in df.columns or phi_col not in df.columns or sw_series is None:
            self._show_sw_placeholder(self._sw_crossplot_host, "Crossplot", "Rt and PHIE curves are required for crossplot diagnostics.")
            return

        rt = pd.to_numeric(df[rt_col], errors="coerce")
        phi = pd.to_numeric(df[phi_col], errors="coerce")
        sw = pd.to_numeric(sw_series, errors="coerce")
        mask = rt.notna() & phi.notna() & sw.notna() & (rt > 0)
        if not mask.any():
            self._show_sw_placeholder(self._sw_crossplot_host, "Crossplot", "No valid Rt/PHIE/Sw points for crossplot.")
            return

        try:
            from matplotlib.figure import Figure
        except Exception:
            self._show_sw_placeholder(self._sw_crossplot_host, "Crossplot", "Matplotlib is unavailable in this environment.")
            return

        fig = Figure(figsize=(7.8, 5.8), dpi=100, constrained_layout=True)
        fig.patch.set_facecolor("white")
        ax = fig.add_subplot(1, 1, 1)
        sc = ax.scatter(phi[mask] * 100.0, rt[mask], c=sw[mask], cmap="YlGnBu_r", s=16, alpha=0.86, edgecolors="none")
        ax.set_yscale("log")
        ax.set_title("Crossplot (Rn vs PHIE)", fontsize=11, color="#24466B")
        ax.set_xlabel("PHIE %", fontsize=9)
        ax.set_ylabel(rt_col, fontsize=9)
        ax.grid(True, linestyle=":", alpha=0.22)
        fig.colorbar(sc, ax=ax, shrink=0.82, label="Sw")
        self._render_figure_to_host(self._sw_crossplot_host, fig)

    def _render_sw_qc_panel(self, df, rt_col: str, phi_col: str, sw_series) -> None:
        import pandas as pd

        if self._sw_qc_host is None:
            return

        layout = self._sw_qc_host.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(self._sw_qc_host)
            layout.setContentsMargins(8, 8, 8, 8)
        self._clear_layout(layout)

        rt_ok = rt_col in df.columns and pd.to_numeric(df[rt_col], errors="coerce").dropna().size > 0
        phi_ok = phi_col in df.columns and pd.to_numeric(df[phi_col], errors="coerce").dropna().size > 0
        sw_ok = sw_series is not None and pd.to_numeric(sw_series, errors="coerce").dropna().size > 0

        panel = QtWidgets.QFrame(self._sw_qc_host)
        panel.setStyleSheet("QFrame { background:#F8FBFE; border:1px solid #D7E2EE; border-radius:10px; }")
        panel_layout = QtWidgets.QVBoxLayout(panel)
        panel_layout.setContentsMargins(12, 12, 12, 12)
        panel_layout.setSpacing(8)
        title = QtWidgets.QLabel("Data Quality", panel)
        title.setStyleSheet("font-size:16px;font-weight:900;color:#24466B;")
        panel_layout.addWidget(title)

        entries = [
            ("✔" if rt_ok else "⚠", "Rt available" if rt_ok else "Rt missing"),
            ("✔" if phi_ok else "⚠", "PHIE available" if phi_ok else "PHIE missing"),
            ("⚠", "Formation Rw constant assumption set"),
            ("✔" if sw_ok else "⚠", "Sw curve computed" if sw_ok else "Sw not computed"),
        ]
        for icon, text in entries:
            row = QtWidgets.QLabel(f"{icon}  {text}", panel)
            row.setStyleSheet("font-size:13px;color:#355C7D;")
            panel_layout.addWidget(row)

        panel_layout.addStretch(1)
        layout.addWidget(panel, 1)

    def _build_porosity_workspace(self) -> None:
        if getattr(self.ui, "_porosity_workspace_built", False):
            return

        tab = getattr(self.ui, "tabPorosity", None)
        if tab is None:
            return

        layout = tab.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(tab)

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll_area = QtWidgets.QScrollArea(tab)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_area.setStyleSheet("border:0;background:transparent;")

        content = QtWidgets.QWidget(scroll_area)
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(14, 14, 14, 14)
        content_layout.setSpacing(14)

        panel_style = "QFrame { background:#FFFFFF; border:1px solid #D7E2EE; border-radius:16px; }"
        soft_panel_style = "QFrame { background:#F8FBFE; border:1px solid #D7E2EE; border-radius:14px; }"
        field_style = (
            "QLineEdit, QComboBox, QDoubleSpinBox { background:#FFFFFF; border:1px solid #C9D7E6; border-radius:8px; padding:6px 10px; min-height:26px; }"
            "QCheckBox { spacing:8px; color:#274B72; font-weight:600; }"
        )
        tab_style = (
            "QTabWidget::pane { border:1px solid #D7E2EE; border-radius:14px; background:#FFFFFF; }"
            "QTabBar::tab { background:#EEF4FA; color:#56708A; padding:9px 16px; margin-right:6px; border-top-left-radius:10px; border-top-right-radius:10px; min-width:88px; }"
            "QTabBar::tab:selected { background:#FFFFFF; color:#1F4E79; font-weight:700; }"
        )

        def clear_layout(target_layout):
            while target_layout.count():
                item = target_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()

        def build_card(parent, title: str, value: str, accent: str) -> tuple[QtWidgets.QFrame, QtWidgets.QLabel]:
            card = QtWidgets.QFrame(parent)
            card.setStyleSheet(panel_style)
            card_layout = QtWidgets.QVBoxLayout(card)
            card_layout.setContentsMargins(12, 10, 12, 10)
            card_layout.setSpacing(4)
            title_label = QtWidgets.QLabel(title, card)
            title_label.setStyleSheet("font-size:11px;color:#5C718A;font-weight:700;letter-spacing:0.2px;")
            value_label = QtWidgets.QLabel(value, card)
            value_label.setStyleSheet(f"font-size:20px;font-weight:800;color:{accent};")
            value_label.setWordWrap(True)
            card_layout.addWidget(title_label)
            card_layout.addWidget(value_label)
            return card, value_label

        def build_info_button(parent, tooltip: str) -> QtWidgets.QToolButton:
            button = QtWidgets.QToolButton(parent)
            button.setAutoRaise(True)
            button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
            button.setToolTip(tooltip)
            button.setIcon(self.ui.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxInformation))
            button.setIconSize(QtCore.QSize(16, 16))
            button.setFixedSize(22, 22)
            return button

        def build_field_row(parent, label_text: str, widget: QtWidgets.QWidget, tooltip: str) -> QtWidgets.QWidget:
            row = QtWidgets.QWidget(parent)
            row_layout = QtWidgets.QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)
            label = QtWidgets.QLabel(label_text, row)
            label.setStyleSheet("color:#355C7D;font-weight:700;")
            info = build_info_button(row, tooltip)
            row_layout.addWidget(label, 0)
            row_layout.addStretch(1)
            row_layout.addWidget(widget, 0)
            row_layout.addWidget(info, 0)
            return row

        def build_section(parent, title: str, body_text: str | None = None) -> tuple[QtWidgets.QFrame, QtWidgets.QVBoxLayout]:
            frame = QtWidgets.QFrame(parent)
            frame.setStyleSheet(panel_style)
            frame_layout = QtWidgets.QVBoxLayout(frame)
            frame_layout.setContentsMargins(14, 14, 14, 14)
            frame_layout.setSpacing(10)
            title_label = QtWidgets.QLabel(title, frame)
            title_label.setStyleSheet("font-size:15px;font-weight:800;color:#24466B;")
            frame_layout.addWidget(title_label)
            if body_text:
                info_label = QtWidgets.QLabel(body_text, frame)
                info_label.setWordWrap(True)
                info_label.setStyleSheet("color:#6C7E90;font-size:12px;line-height:1.4;")
                frame_layout.addWidget(info_label)
            return frame, frame_layout

        def style_method_button(button: QtWidgets.QPushButton, selected: bool) -> None:
            if selected:
                button.setStyleSheet(
                    "QPushButton { background:#EAF2FF; border:1px solid #2B6CB0; border-radius:12px; color:#1F4E79; font-weight:800; padding:10px 12px; text-align:left; }"
                )
            else:
                button.setStyleSheet(
                    "QPushButton { background:#FFFFFF; border:1px solid #D7E2EE; border-radius:12px; color:#355C7D; font-weight:700; padding:10px 12px; text-align:left; }"
                    "QPushButton:hover { border-color:#9BB8D9; background:#F8FBFE; }"
                )

        hero_frame = QtWidgets.QFrame(content)
        hero_frame.setStyleSheet(
            "QFrame { background:qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FFFFFF, stop:1 #F5F9FD); border:1px solid #D7E2EE; border-radius:18px; }"
        )
        hero_layout = QtWidgets.QHBoxLayout(hero_frame)
        hero_layout.setContentsMargins(18, 16, 18, 16)
        hero_layout.setSpacing(14)

        hero_icon = QtWidgets.QLabel("PHIE", hero_frame)
        hero_icon.setAlignment(QtCore.Qt.AlignCenter)
        hero_icon.setFixedSize(58, 58)
        hero_icon.setStyleSheet(
            "background:#EAF2FF;color:#1F4E79;border:1px solid #BFD2EA;border-radius:14px;font-size:15px;font-weight:900;"
        )
        hero_layout.addWidget(hero_icon, 0)

        hero_text = QtWidgets.QVBoxLayout()
        hero_title = QtWidgets.QLabel("Porosity Calculation", hero_frame)
        hero_title.setStyleSheet("font-size:24px;font-weight:900;color:#173A5E;")
        hero_subtitle = QtWidgets.QLabel(
            "Density-neutron centered porosity workspace for interpretation, preview, and quick quality review.",
            hero_frame,
        )
        hero_subtitle.setWordWrap(True)
        hero_subtitle.setStyleSheet("color:#5C718A;font-size:12px;")
        hero_text.addWidget(hero_title)
        hero_text.addWidget(hero_subtitle)
        hero_text.addStretch(1)
        hero_layout.addLayout(hero_text, 1)
        content_layout.addWidget(hero_frame)

        workspace_row = QtWidgets.QHBoxLayout()
        workspace_row.setSpacing(14)

        controls_frame = QtWidgets.QFrame(content)
        controls_frame.setMinimumWidth(340)
        controls_frame.setMaximumWidth(380)
        controls_frame.setStyleSheet(panel_style)
        controls_layout = QtWidgets.QVBoxLayout(controls_frame)
        controls_layout.setContentsMargins(14, 14, 14, 14)
        controls_layout.setSpacing(12)

        controls_title = QtWidgets.QLabel("Porosity Inputs", controls_frame)
        controls_title.setStyleSheet("font-size:18px;font-weight:900;color:#24466B;")
        controls_layout.addWidget(controls_title)

        well_combo = QtWidgets.QComboBox(controls_frame)
        well_combo.setStyleSheet(field_style)
        well_combo.setMinimumHeight(34)
        self.ui.comboPhiWell = well_combo
        controls_layout.addWidget(build_field_row(controls_frame, "Well", well_combo, "Choose the active well used for porosity preview and calculation."))

        method_group = QtWidgets.QFrame(controls_frame)
        method_group.setStyleSheet(soft_panel_style)
        method_layout = QtWidgets.QVBoxLayout(method_group)
        method_layout.setContentsMargins(12, 12, 12, 12)
        method_layout.setSpacing(8)
        method_header = QtWidgets.QHBoxLayout()
        method_title = QtWidgets.QLabel("Method", method_group)
        method_title.setStyleSheet("font-size:13px;font-weight:800;color:#355C7D;")
        method_header.addWidget(method_title)
        method_header.addStretch(1)
        method_header.addWidget(build_info_button(method_group, "Method cards stay synchronized with the calculation engine."))
        method_layout.addLayout(method_header)

        method_combo = QtWidgets.QComboBox(method_group)
        method_combo.addItems(["Density-Neutron (PHIE)", "Sonic (DT)", "Neutron (PHIN)"])
        method_combo.hide()
        self.ui.comboPhiMethod = method_combo

        method_buttons = QtWidgets.QVBoxLayout()
        method_buttons.setSpacing(8)
        self._porosity_method_buttons = {}
        method_specs = [
            ("Density-Neutron (PHIE)", "Density-Neutron\nPHIE"),
            ("Sonic (DT)", "Sonic\nDT"),
            ("Neutron (PHIN)", "Neutron\nPHIN"),
        ]
        for method_text, button_text in method_specs:
            button = QtWidgets.QPushButton(button_text, method_group)
            button.setCheckable(True)
            button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
            button.setMinimumHeight(56)
            button.setProperty("methodText", method_text)
            style_method_button(button, method_text == "Density-Neutron (PHIE)")
            button.clicked.connect(lambda _checked=False, target=method_text: self._select_porosity_method(target))
            self._porosity_method_buttons[method_text] = button
            method_buttons.addWidget(button)
        method_layout.addLayout(method_buttons)
        controls_layout.addWidget(method_group)

        rock_frame, rock_layout = build_section(controls_frame, "Rock Properties")
        rho_ma_spin = QtWidgets.QDoubleSpinBox(rock_frame)
        rho_ma_spin.setDecimals(3)
        rho_ma_spin.setMinimum(2.0)
        rho_ma_spin.setMaximum(3.5)
        rho_ma_spin.setSingleStep(0.01)
        rho_ma_spin.setValue(2.65)
        rho_ma_spin.setStyleSheet(field_style)
        self.ui.spinPhiRhoma = rho_ma_spin
        rock_layout.addWidget(build_field_row(rock_frame, "Matrix Density (g/cc)", rho_ma_spin, "Typical limestone matrix density used for density-neutron porosity calculations."))
        controls_layout.addWidget(rock_frame)

        fluid_frame, fluid_layout = build_section(controls_frame, "Fluid Properties")
        rho_f_spin = QtWidgets.QDoubleSpinBox(fluid_frame)
        rho_f_spin.setDecimals(3)
        rho_f_spin.setMinimum(0.80)
        rho_f_spin.setMaximum(1.20)
        rho_f_spin.setSingleStep(0.01)
        rho_f_spin.setValue(1.00)
        rho_f_spin.setStyleSheet(field_style)
        self.ui.spinPhiRhof = rho_f_spin
        fluid_layout.addWidget(build_field_row(fluid_frame, "Fluid Density (g/cc)", rho_f_spin, "Base fluid density used to convert RHOB into porosity."))
        controls_layout.addWidget(fluid_frame)

        correction_frame, correction_layout = build_section(controls_frame, "Corrections")
        correction_row = QtWidgets.QWidget(correction_frame)
        correction_row_layout = QtWidgets.QVBoxLayout(correction_row)
        correction_row_layout.setContentsMargins(0, 0, 0, 0)
        correction_row_layout.setSpacing(8)

        vcl_toggle_row = QtWidgets.QHBoxLayout()
        vcl_label = QtWidgets.QLabel("Vcl Correction", correction_row)
        vcl_label.setStyleSheet("color:#355C7D;font-weight:700;")
        vcl_toggle = QtWidgets.QCheckBox("Apply shale correction", correction_row)
        vcl_toggle.setChecked(True)
        vcl_toggle.setStyleSheet("color:#274B72;font-weight:600;")
        vcl_toggle_row.addWidget(vcl_label)
        vcl_toggle_row.addStretch(1)
        vcl_toggle_row.addWidget(vcl_toggle)
        correction_row_layout.addLayout(vcl_toggle_row)
        self.ui.checkPhiVclCorr = vcl_toggle

        out_name = QtWidgets.QLineEdit(correction_row)
        out_name.setText("PHIE")
        out_name.setStyleSheet(field_style)
        self.ui.linePhiOutName = out_name
        correction_row_layout.addWidget(build_field_row(correction_row, "Output Curve", out_name, "Name of the output porosity curve written back into the selected well."))
        correction_layout.addWidget(correction_row)
        controls_layout.addWidget(correction_frame)

        hint = QtWidgets.QLabel(
            "Density-neutron porosity is the default preview. Switch methods to compare alternative porosity estimates before export.",
            controls_frame,
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("background:#F8FBFE;border:1px solid #D7E2EE;border-radius:10px;padding:10px;color:#5C718A;font-size:12px;")
        controls_layout.addWidget(hint)
        controls_layout.addStretch(1)

        action_row = QtWidgets.QHBoxLayout()
        action_row.setSpacing(10)
        calc_btn = QtWidgets.QPushButton("Run Interpretation", controls_frame)
        calc_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        calc_btn.setMinimumHeight(42)
        calc_btn.setStyleSheet(
            "QPushButton { background:#2B6CB0; color:#FFFFFF; border:none; border-radius:10px; font-size:13px; font-weight:800; }"
            "QPushButton:hover { background:#245C96; }"
        )
        reset_btn = QtWidgets.QPushButton("Reset", controls_frame)
        reset_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        reset_btn.setMinimumHeight(42)
        reset_btn.setStyleSheet(
            "QPushButton { background:#EEF4FA; color:#355C7D; border:1px solid #C9D7E6; border-radius:10px; font-size:13px; font-weight:800; }"
            "QPushButton:hover { background:#E2EDF7; }"
        )
        action_row.addWidget(calc_btn)
        action_row.addWidget(reset_btn)
        controls_layout.addLayout(action_row)
        self.ui.btnCalcPhi = calc_btn
        self.ui.btnResetPhi = reset_btn

        right_panel = QtWidgets.QVBoxLayout()
        right_panel.setSpacing(14)

        kpi_frame = QtWidgets.QFrame(content)
        kpi_frame.setStyleSheet(panel_style)
        kpi_layout = QtWidgets.QVBoxLayout(kpi_frame)
        kpi_layout.setContentsMargins(14, 14, 14, 14)
        kpi_layout.setSpacing(10)
        kpi_header = QtWidgets.QHBoxLayout()
        kpi_title = QtWidgets.QLabel("Porosity Summary", kpi_frame)
        kpi_title.setStyleSheet("font-size:16px;font-weight:900;color:#24466B;")
        kpi_header.addWidget(kpi_title)
        kpi_header.addStretch(1)
        kpi_header.addWidget(build_info_button(kpi_frame, "These values follow the active well and depth filter."))
        kpi_layout.addLayout(kpi_header)
        kpi_cards = QtWidgets.QHBoxLayout()
        kpi_cards.setSpacing(10)
        self._porosity_kpi_labels = {}
        for title, key, value, accent in (
            ("Average Porosity", "avg", "--", "#1F4E79"),
            ("Max Porosity", "max", "--", "#0F8B8D"),
            ("Min Porosity", "min", "--", "#D97706"),
            ("Net Reservoir Thickness", "thickness", "--", "#2B6CB0"),
        ):
            card, value_label = build_card(kpi_frame, title, value, accent)
            self._porosity_kpi_labels[key] = value_label
            kpi_cards.addWidget(card)
        kpi_layout.addLayout(kpi_cards)
        right_panel.addWidget(kpi_frame, 0)

        body_row = QtWidgets.QHBoxLayout()
        body_row.setSpacing(14)

        plot_frame = QtWidgets.QFrame(content)
        plot_frame.setStyleSheet(panel_style)
        plot_layout = QtWidgets.QVBoxLayout(plot_frame)
        plot_layout.setContentsMargins(14, 14, 14, 14)
        plot_layout.setSpacing(10)

        tabs_header = QtWidgets.QHBoxLayout()
        tabs_title = QtWidgets.QLabel("Log View", plot_frame)
        tabs_title.setStyleSheet("font-size:16px;font-weight:900;color:#24466B;")
        tabs_header.addWidget(tabs_title)
        tabs_header.addStretch(1)
        tabs_header.addWidget(build_info_button(plot_frame, "Use the tabs to inspect log view, crossplot, and histogram previews."))
        plot_layout.addLayout(tabs_header)

        tab_widget = QtWidgets.QTabWidget(plot_frame)
        tab_widget.setStyleSheet(tab_style)
        tab_widget.setDocumentMode(True)
        self.ui.tabPhiLogView = QtWidgets.QWidget(tab_widget)
        self.ui.tabPhiCrossplot = QtWidgets.QWidget(tab_widget)
        self.ui.tabPhiHistogram = QtWidgets.QWidget(tab_widget)
        tab_widget.addTab(self.ui.tabPhiLogView, "Log View")
        tab_widget.addTab(self.ui.tabPhiCrossplot, "Crossplot")
        tab_widget.addTab(self.ui.tabPhiHistogram, "Histogram")

        for page_name, page_widget in (
            ("log", self.ui.tabPhiLogView),
            ("crossplot", self.ui.tabPhiCrossplot),
            ("histogram", self.ui.tabPhiHistogram),
        ):
            page_layout = QtWidgets.QVBoxLayout(page_widget)
            page_layout.setContentsMargins(0, 0, 0, 0)
            page_layout.setSpacing(0)
            host = QtWidgets.QFrame(page_widget)
            host.setStyleSheet(soft_panel_style)
            host.setMinimumHeight(340)
            host_layout = QtWidgets.QVBoxLayout(host)
            host_layout.setContentsMargins(10, 10, 10, 10)
            host_layout.setSpacing(0)
            page_layout.addWidget(host)
            if page_name == "log":
                self._porosity_log_host = host
            elif page_name == "crossplot":
                self._porosity_crossplot_host = host
            else:
                self._porosity_hist_host = host

        plot_layout.addWidget(tab_widget, 1)
        self.ui.framePhiPlotTabs = tab_widget

        quality_frame, quality_layout = build_section(
            content,
            "Data Quality",
            "Indicator cards summarize the active log coverage and missing curve handling for the current well.",
        )
        quality_frame.setMinimumWidth(260)
        self._porosity_quality_labels = {}
        for title, key, icon_pixmap in (
            ("RHOB", "rhob", QtWidgets.QStyle.SP_DialogApplyButton),
            ("NPHI", "nphi", QtWidgets.QStyle.SP_MessageBoxWarning),
        ):
            row = QtWidgets.QFrame(quality_frame)
            row.setStyleSheet("QFrame { background:#F8FBFE; border:1px solid #D7E2EE; border-radius:10px; }")
            row_layout = QtWidgets.QHBoxLayout(row)
            row_layout.setContentsMargins(10, 10, 10, 10)
            row_layout.setSpacing(10)
            icon_label = QtWidgets.QLabel(row)
            icon_label.setPixmap(self.ui.style().standardIcon(icon_pixmap).pixmap(16, 16))
            text_box = QtWidgets.QVBoxLayout()
            label = QtWidgets.QLabel(title, row)
            label.setStyleSheet("font-size:12px;font-weight:900;color:#355C7D;")
            value = QtWidgets.QLabel("--", row)
            value.setWordWrap(True)
            value.setStyleSheet("font-size:12px;color:#5C718A;")
            text_box.addWidget(label)
            text_box.addWidget(value)
            row_layout.addWidget(icon_label, 0)
            row_layout.addLayout(text_box, 1)
            quality_layout.addWidget(row)
            self._porosity_quality_labels[key] = value
        quality_note = QtWidgets.QLabel("Missing curves are highlighted so you can see whether interpolation or fallback logic is being used.", quality_frame)
        quality_note.setWordWrap(True)
        quality_note.setStyleSheet("color:#5C718A;font-size:12px;")
        quality_layout.addWidget(quality_note)

        body_row.addWidget(plot_frame, 1)
        body_row.addWidget(quality_frame, 0)
        right_panel.addLayout(body_row, 1)

        activity_frame, activity_layout = build_section(content, "Activity Log", "Recent porosity workflow events are kept in a compact desktop-style feed.")
        activity_list = QtWidgets.QListWidget(activity_frame)
        activity_list.setAlternatingRowColors(True)
        activity_list.setStyleSheet(
            "QListWidget { background:#F8FBFE; border:1px solid #D7E2EE; border-radius:10px; padding:6px; }"
            "QListWidget::item { padding:8px 6px; }"
        )
        activity_layout.addWidget(activity_list)
        self._porosity_activity_list = activity_list
        right_panel.addWidget(activity_frame, 0)

        workspace_row.addWidget(controls_frame, 0)
        workspace_row.addLayout(right_panel, 1)
        content_layout.addLayout(workspace_row, 1)

        content_layout.addStretch(1)
        scroll_area.setWidget(content)
        layout.addWidget(scroll_area)

        self.ui.comboPhiMethod.currentTextChanged.connect(lambda *_: self._sync_porosity_method_cards())
        self.ui.comboPhiWell.currentTextChanged.connect(lambda *_: self.refresh_porosity_workspace())
        self.ui.refresh_porosity_tab = self.refresh_porosity_workspace

        self._populate_porosity_wells()
        self._sync_porosity_method_cards()
        if not self._porosity_activity_items:
            self._porosity_activity_items = ["LAS loaded", "Porosity calculated", "Crossplot generated"]
        self.ui._porosity_workspace_built = True
        self.refresh_porosity_workspace()

    def refresh_porosity_workspace(self) -> None:
        if not getattr(self.ui, "_porosity_workspace_built", False):
            return

        self._populate_porosity_wells()
        self._sync_porosity_method_cards()

        well = self.data._get_current_well()
        if well is None:
            self._set_porosity_kpis(None, None)
            self._set_porosity_quality(None)
            self._show_porosity_placeholder(self._porosity_log_host, "Log View", "Load a well to preview the porosity track layout.")
            self._show_porosity_placeholder(self._porosity_crossplot_host, "Crossplot", "Density vs neutron scatter will appear here once data is available.")
            self._show_porosity_placeholder(self._porosity_hist_host, "Histogram", "PHIE distribution will appear here once porosity is calculated.")
            self._refresh_porosity_activity_log()
            return

        df = getattr(well, "data", None)
        if df is None or getattr(df, "empty", True):
            self._set_porosity_kpis(None, None)
            self._set_porosity_quality(None)
            self._show_porosity_placeholder(self._porosity_log_host, "Log View", "The active well does not have usable log data yet.")
            self._show_porosity_placeholder(self._porosity_crossplot_host, "Crossplot", "No data available for density-neutron crossplot preview.")
            self._show_porosity_placeholder(self._porosity_hist_host, "Histogram", "No porosity samples available for histogram preview.")
            self._refresh_porosity_activity_log()
            return

        visible = self.data._filtered_dataframe(well)
        if visible is None or getattr(visible, "empty", True):
            visible = df.copy()

        depth_col = self.data._depth_column(visible) or self.data._depth_column(df)
        phi_series, phi_label = self._porosity_preview_series(visible)

        self._set_porosity_kpis(visible, phi_series)
        self._set_porosity_quality(visible)
        self._render_porosity_log_view(visible, depth_col, phi_series, phi_label)
        self._render_porosity_crossplot(visible, depth_col)
        self._render_porosity_histogram(visible, depth_col, phi_series, phi_label)
        self._refresh_porosity_activity_log()

    def _populate_porosity_wells(self) -> None:
        combo = getattr(self.ui, "comboPhiWell", None)
        if combo is None:
            return

        current_text = combo.currentText().strip()
        combo.blockSignals(True)
        combo.clear()
        wells = sorted(getattr(self.data, "_wells", {}).keys())
        if wells:
            combo.addItems(wells)
            target = current_text if current_text in wells else getattr(self.data, "_current_well", None)
            if target in wells:
                combo.setCurrentText(target)
            elif combo.count():
                combo.setCurrentIndex(0)
        else:
            combo.addItem("No wells loaded")
        combo.blockSignals(False)

    def _select_porosity_method(self, method_text: str) -> None:
        combo = getattr(self.ui, "comboPhiMethod", None)
        if combo is not None:
            index = combo.findText(method_text)
            if index >= 0:
                combo.setCurrentIndex(index)
        self._sync_porosity_method_cards()

    def _sync_porosity_method_cards(self) -> None:
        combo = getattr(self.ui, "comboPhiMethod", None)
        if combo is None:
            return

        current_text = combo.currentText().strip()
        for method_text, button in self._porosity_method_buttons.items():
            selected = method_text == current_text
            button.blockSignals(True)
            button.setChecked(selected)
            button.blockSignals(False)
            if selected:
                button.setStyleSheet(
                    "QPushButton { background:#EAF2FF; border:1px solid #2B6CB0; border-radius:12px; color:#1F4E79; font-weight:800; padding:10px 12px; text-align:left; }"
                )
            else:
                button.setStyleSheet(
                    "QPushButton { background:#FFFFFF; border:1px solid #D7E2EE; border-radius:12px; color:#355C7D; font-weight:700; padding:10px 12px; text-align:left; }"
                    "QPushButton:hover { border-color:#9BB8D9; background:#F8FBFE; }"
                )

    def _porosity_preview_series(self, df):
        import pandas as pd

        output_name = self._line_text("linePhiOutName") or "PHIE"
        candidates = [output_name, "PHIE", "PHIT", "PHI"]
        for candidate in candidates:
            if candidate in df.columns:
                series = pd.to_numeric(df[candidate], errors="coerce")
                return series, candidate

        method = self._combo_text("comboPhiMethod")
        rho_ma = self._spin_value(("spinPhiRhoma",), 2.65) or 2.65
        rho_f = self._spin_value(("spinPhiRhof",), 1.0) or 1.0

        if method == "Neutron (PHIN)" and "NPHI" in df.columns:
            series = pd.to_numeric(df["NPHI"], errors="coerce").clip(0.0, 1.0)
            return series, "NPHI"
        if method == "Sonic (DT)" and "DT" in df.columns:
            import numpy as np

            dt = pd.to_numeric(df["DT"], errors="coerce").to_numpy(dtype=float)
            values = np.clip((dt - 55.5) / (189.0 - 55.5 + 1e-9), 0.0, 1.0)
            return pd.Series(values, index=df.index), "DT"
        if "NPHI" in df.columns and "RHOB" in df.columns:
            values = porosity.compute_phi_combo(df["NPHI"].values, df["RHOB"].values, rho_ma=rho_ma, rho_f=rho_f)
            return pd.Series(values, index=df.index), "Density-Neutron"
        if "RHOB" in df.columns:
            values = porosity.compute_phi_from_density(df["RHOB"].values, rho_ma=rho_ma, rho_f=rho_f)
            return pd.Series(values, index=df.index), "Density"
        if "NPHI" in df.columns:
            series = pd.to_numeric(df["NPHI"], errors="coerce").clip(0.0, 1.0)
            return series, "NPHI"

        return pd.Series(dtype=float), ""

    def _set_porosity_kpis(self, df, phi_series) -> None:
        import numpy as np
        import pandas as pd

        if df is None or phi_series is None or getattr(phi_series, "empty", True):
            for key in self._porosity_kpi_labels:
                self._porosity_kpi_labels[key].setText("--")
            return

        valid_phi = pd.to_numeric(phi_series, errors="coerce").dropna()
        if valid_phi.empty:
            for key in self._porosity_kpi_labels:
                self._porosity_kpi_labels[key].setText("--")
            return

        depth_col = self.data._depth_column(df)
        if depth_col is not None and depth_col in df.columns:
            depth = pd.to_numeric(df[depth_col], errors="coerce")
        else:
            depth = pd.Series(np.arange(len(df), dtype=float), index=df.index)

        phi_mask = pd.to_numeric(phi_series, errors="coerce") >= 0.10
        thickness = self._estimate_thickness(depth.to_numpy(dtype=float), phi_mask.fillna(False).to_numpy(dtype=bool))

        self._porosity_kpi_labels["avg"].setText(f"{valid_phi.mean() * 100.0:.1f}%")
        self._porosity_kpi_labels["max"].setText(f"{valid_phi.max() * 100.0:.1f}%")
        self._porosity_kpi_labels["min"].setText(f"{valid_phi.min() * 100.0:.1f}%")
        self._porosity_kpi_labels["thickness"].setText(f"{thickness:.1f} m")

    def _set_porosity_quality(self, df) -> None:
        import pandas as pd

        if df is None or getattr(df, "empty", True):
            if "rhob" in self._porosity_quality_labels:
                self._porosity_quality_labels["rhob"].setText("No well loaded")
            if "nphi" in self._porosity_quality_labels:
                self._porosity_quality_labels["nphi"].setText("No well loaded")
            return

        rhob_ok = "RHOB" in df.columns and pd.to_numeric(df["RHOB"], errors="coerce").dropna().size > 0
        nphi_present = "NPHI" in df.columns and pd.to_numeric(df["NPHI"], errors="coerce").dropna().size > 0

        rhob_message = "Available" if rhob_ok else "Missing"
        nphi_message = "Available" if nphi_present else "Missing (interpolated)"

        if "rhob" in self._porosity_quality_labels:
            self._porosity_quality_labels["rhob"].setText(rhob_message)
        if "nphi" in self._porosity_quality_labels:
            self._porosity_quality_labels["nphi"].setText(nphi_message)

    def _show_porosity_placeholder(self, host, title: str, message: str) -> None:
        if host is None:
            return

        layout = host.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(host)
            layout.setContentsMargins(0, 0, 0, 0)

        self._clear_layout(layout)
        label = QtWidgets.QLabel(f"{title}\n\n{message}", host)
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet(
            "background:#F8FBFE;border:1px dashed #C9D7E6;border-radius:10px;padding:18px;color:#6C7E90;font-size:12px;"
        )
        layout.addWidget(label, 1)

    def _refresh_porosity_activity_log(self) -> None:
        if self._porosity_activity_list is None:
            return

        if not self._porosity_activity_items:
            self._porosity_activity_items = ["LAS loaded", "Porosity calculated", "Crossplot generated"]

        self._porosity_activity_list.clear()
        for message in self._porosity_activity_items[-8:]:
            self._porosity_activity_list.addItem(message)

    def _append_porosity_activity(self, message: str) -> None:
        text = message.strip()
        if not text:
            return
        self._porosity_activity_items.append(text)
        self._porosity_activity_items = self._porosity_activity_items[-8:]
        self._refresh_porosity_activity_log()

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _render_porosity_log_view(self, df, depth_col: str | None, phi_series, phi_label: str) -> None:
        import numpy as np
        import pandas as pd

        if depth_col is None or depth_col not in df.columns:
            self._show_porosity_placeholder(self._porosity_log_host, "Log View", "A depth curve is required to render the multi-track porosity preview.")
            return

        depth = pd.to_numeric(df[depth_col], errors="coerce").to_numpy(dtype=float)
        gr_col = self._pick_gr_curve_name(df)
        gr = pd.to_numeric(df[gr_col], errors="coerce").to_numpy(dtype=float) if gr_col and gr_col in df.columns else None
        rhob = pd.to_numeric(df["RHOB"], errors="coerce").to_numpy(dtype=float) if "RHOB" in df.columns else None
        nphi = pd.to_numeric(df["NPHI"], errors="coerce").to_numpy(dtype=float) if "NPHI" in df.columns else None
        phi = pd.to_numeric(phi_series, errors="coerce").to_numpy(dtype=float) if phi_series is not None else np.array([])

        mask = np.isfinite(depth)
        if gr is not None:
            mask &= np.isfinite(gr)
        if rhob is not None:
            mask &= np.isfinite(rhob)
        if nphi is not None:
            mask &= np.isfinite(nphi)
        if phi.size:
            mask &= np.isfinite(phi)

        if not np.any(mask):
            self._show_porosity_placeholder(self._porosity_log_host, "Log View", "The current selection does not contain enough valid samples to draw the track preview.")
            return

        depth = depth[mask]
        if gr is not None:
            gr = gr[mask]
        if rhob is not None:
            rhob = rhob[mask]
        if nphi is not None:
            nphi = nphi[mask]
        if phi.size:
            phi = phi[mask]

        try:
            from matplotlib.figure import Figure
        except Exception:
            self._show_porosity_placeholder(self._porosity_log_host, "Log View", "Matplotlib is not available in the current environment.")
            return

        fig = Figure(figsize=(9.2, 6.2), dpi=100, constrained_layout=True)
        fig.patch.set_facecolor("white")
        axes = fig.subplots(1, 3, sharey=True)
        if not isinstance(axes, (list, tuple, np.ndarray)):
            axes = [axes]

        ax_gr, ax_rho, ax_phi = axes

        if gr is not None:
            ax_gr.plot(gr, depth, color="#E97A16", linewidth=1.1)
            ax_gr.fill_betweenx(depth, gr.min(), gr, color="#FDE7C8", alpha=0.6)
        else:
            ax_gr.text(0.5, 0.5, "GR unavailable", transform=ax_gr.transAxes, ha="center", va="center", color="#7B8FA6")
        ax_gr.set_title("Track 1  Gamma Ray", fontsize=10, color="#24466B")
        ax_gr.set_xlabel("GR", fontsize=9)
        ax_gr.grid(True, linestyle="--", alpha=0.18)

        if rhob is not None:
            ax_rho.plot(rhob, depth, color="#2563EB", linewidth=1.1)
            ax_rho.set_xlabel("RHOB", fontsize=9, color="#2563EB")
            ax_rho.tick_params(axis="x", colors="#2563EB")
            ax_rho.grid(True, linestyle="--", alpha=0.18)
            twin = ax_rho.twiny()
            if nphi is not None:
                twin.plot(nphi, depth, color="#F97316", linewidth=1.0)
                twin.set_xlabel("NPHI", fontsize=9, color="#F97316")
                twin.tick_params(axis="x", colors="#F97316")
        else:
            ax_rho.text(0.5, 0.5, "Density-Neutron overlay", transform=ax_rho.transAxes, ha="center", va="center", color="#7B8FA6")
        ax_rho.set_title("Track 2  Density / Neutron", fontsize=10, color="#24466B")

        if phi.size:
            ax_phi.plot(phi * 100.0, depth, color="#0F8B8D", linewidth=1.2)
            ax_phi.fill_betweenx(depth, 0, phi * 100.0, where=phi >= 0.10, color="#B7ECEA", alpha=0.6)
            ax_phi.set_xlabel("PHIE %", fontsize=9, color="#0F8B8D")
            ax_phi.tick_params(axis="x", colors="#0F8B8D")
            ax_phi.grid(True, linestyle="--", alpha=0.18)
        else:
            ax_phi.text(0.5, 0.5, "Effective porosity preview", transform=ax_phi.transAxes, ha="center", va="center", color="#7B8FA6")
        ax_phi.set_title(f"Track 3  Effective Porosity ({phi_label or 'PHIE'})", fontsize=10, color="#24466B")

        for axis in axes:
            axis.invert_yaxis()
            axis.set_ylabel(depth_col, fontsize=9, color="#24466B")

        self._render_figure_to_host(self._porosity_log_host, fig)

    def _render_porosity_crossplot(self, df, depth_col: str | None) -> None:
        import pandas as pd

        if "RHOB" not in df.columns or "NPHI" not in df.columns:
            self._show_porosity_placeholder(self._porosity_crossplot_host, "Crossplot", "Density vs neutron scatter requires both RHOB and NPHI curves.")
            return

        phi_series, _ = self._porosity_preview_series(df)
        if phi_series is None or getattr(phi_series, "empty", True):
            self._show_porosity_placeholder(self._porosity_crossplot_host, "Crossplot", "Porosity values are needed before the density-neutron scatter can be drawn.")
            return

        rhob = pd.to_numeric(df["RHOB"], errors="coerce")
        nphi = pd.to_numeric(df["NPHI"], errors="coerce")
        phi = pd.to_numeric(phi_series, errors="coerce")

        mask = rhob.notna() & nphi.notna() & phi.notna()
        if not mask.any():
            self._show_porosity_placeholder(self._porosity_crossplot_host, "Crossplot", "No valid RHOB / NPHI samples were found for the preview.")
            return

        try:
            from matplotlib.figure import Figure
        except Exception:
            self._show_porosity_placeholder(self._porosity_crossplot_host, "Crossplot", "Matplotlib is not available in the current environment.")
            return

        fig = Figure(figsize=(7.4, 6.0), dpi=100, constrained_layout=True)
        fig.patch.set_facecolor("white")
        ax = fig.add_subplot(1, 1, 1)
        scatter = ax.scatter(
            nphi[mask] * 100.0,
            rhob[mask],
            c=phi[mask] * 100.0,
            cmap="viridis",
            s=16,
            alpha=0.86,
            edgecolors="none",
        )
        ax.set_title("Density vs Neutron Scatter", fontsize=11, color="#24466B")
        ax.set_xlabel("NPHI %", fontsize=9)
        ax.set_ylabel("RHOB", fontsize=9)
        ax.grid(True, linestyle="--", alpha=0.18)
        ax.tick_params(labelsize=8)
        fig.colorbar(scatter, ax=ax, shrink=0.82, label="PHIE %")
        self._render_figure_to_host(self._porosity_crossplot_host, fig)

    def _render_porosity_histogram(self, df, depth_col: str | None, phi_series, phi_label: str) -> None:
        import pandas as pd

        if phi_series is None or getattr(phi_series, "empty", True):
            self._show_porosity_placeholder(self._porosity_hist_host, "Histogram", "Porosity samples are required to build the distribution preview.")
            return

        phi = pd.to_numeric(phi_series, errors="coerce").dropna()
        if phi.empty:
            self._show_porosity_placeholder(self._porosity_hist_host, "Histogram", "No porosity samples were found for the current interval.")
            return

        try:
            from matplotlib.figure import Figure
        except Exception:
            self._show_porosity_placeholder(self._porosity_hist_host, "Histogram", "Matplotlib is not available in the current environment.")
            return

        fig = Figure(figsize=(7.4, 5.8), dpi=100, constrained_layout=True)
        fig.patch.set_facecolor("white")
        ax = fig.add_subplot(1, 1, 1)
        ax.hist(phi * 100.0, bins=24, color="#2B6CB0", alpha=0.86, edgecolor="#1F4E79")
        ax.set_title(f"Porosity Distribution ({phi_label or 'PHIE'})", fontsize=11, color="#24466B")
        ax.set_xlabel("Porosity %", fontsize=9)
        ax.set_ylabel("Count", fontsize=9)
        ax.grid(True, axis="y", linestyle="--", alpha=0.18)
        ax.tick_params(labelsize=8)
        self._render_figure_to_host(self._porosity_hist_host, fig)

    def _build_vsh_workspace(self) -> None:
        if getattr(self.ui, "_vsh_workspace_built", False):
            return

        self._vsh_track_host = getattr(self.ui, "vshTrackCanvas", None)
        self._vsh_hist_host = getattr(self.ui, "vshHistCanvas", None)
        self._vsh_box_host = getattr(self.ui, "vshBoxCanvas", None)

        # Fallback for malformed .ui: create a dedicated track canvas host if missing.
        if self._vsh_track_host is None:
            track_frame = getattr(self.ui, "frameVshTrack", None)
            if track_frame is not None:
                track_layout = track_frame.layout()
                if track_layout is None:
                    track_layout = QtWidgets.QVBoxLayout(track_frame)
                    track_layout.setContentsMargins(8, 8, 8, 8)
                    track_layout.setSpacing(6)
                self._vsh_track_host = QtWidgets.QWidget(track_frame)
                self._vsh_track_host.setObjectName("vshTrackCanvas")
                track_layout.addWidget(self._vsh_track_host, 1)
                self.ui.vshTrackCanvas = self._vsh_track_host

        for host in (self._vsh_track_host, self._vsh_hist_host, self._vsh_box_host):
            if host is None:
                continue
            layout = host.layout()
            if layout is None:
                layout = QtWidgets.QVBoxLayout(host)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

        method_combo = getattr(self.ui, "comboVclMethod", None)
        if method_combo is not None:
            self.ui.vshMethodComboBox = method_combo
            self._configure_vsh_method_selector(method_combo)

        self.ui.runVshBtn = getattr(self.ui, "btnCalcVsh", None)
        send_btn = getattr(self.ui, "btnUseVshWorkflow", None)
        self.ui.sendToWorkflowBtn = send_btn
        if send_btn is not None and hasattr(send_btn, "clicked"):
            send_btn.clicked.connect(self._send_vsh_to_workflow)

        self.ui.grCleanSpinBox = getattr(self.ui, "spinVclGRmin", None)
        self.ui.grShaleSpinBox = getattr(self.ui, "spinVclGRmax", None)

        well = self.data._get_current_well()
        df = getattr(well, "data", None) if well is not None else None
        if df is not None:
            self._sync_gr_curve_line(df)

        self.ui._vsh_workspace_built = True

    def _update_vsh_kpis(self, gr_clean, gr_shale, method: str, stats: dict) -> None:
        self._set_label_text("grCleanLabel", self._format_value(gr_clean, "Depth"))
        self._set_label_text("grShaleLabel", self._format_value(gr_shale, "Depth"))
        self._set_label_text("methodLabel", method)
        self._set_label_text("vshMeanLabel", f"{stats['mean']:.3f}")
        self._set_label_text("vshRangeLabel", f"{stats['min']:.3f}-{stats['max']:.3f}")
        self._set_label_text("shalePercentLabel", f"{stats['shale_percent']:.1f}%")

    def _plot_vsh_track(self, df, gr_curve: str, method_columns: list[tuple[str, str]]) -> None:
        import pandas as pd
        from matplotlib.figure import Figure

        depth_col = self.data._depth_column(df)
        if depth_col is None:
            return

        depth = pd.to_numeric(df[depth_col], errors="coerce").to_numpy(dtype=float)
        gr = pd.to_numeric(df.get(gr_curve), errors="coerce").to_numpy(dtype=float) if gr_curve in df.columns else None

        method_arrays: list[tuple[str, np.ndarray]] = []
        mask = np.isfinite(depth)
        for method_name, col_name in method_columns:
            vsh_values = pd.to_numeric(df.get(col_name), errors="coerce").to_numpy(dtype=float)
            method_arrays.append((method_name, vsh_values))
            mask &= np.isfinite(vsh_values)

        if not np.any(mask):
            return
        depth = depth[mask]
        method_arrays = [(name, vals[mask]) for name, vals in method_arrays]
        if gr is not None:
            gr = gr[mask]

        n_methods = len(method_arrays)
        fig = Figure(figsize=(max(6.2, 3.0 * n_methods), 8.8), dpi=100, constrained_layout=True)
        axes = fig.subplots(1, n_methods, sharey=True)
        if n_methods == 1:
            axes = [axes]

        for idx, (ax, (method_name, vsh_vals)) in enumerate(zip(axes, method_arrays)):
            ax.plot(vsh_vals, depth, color="#1F2937", linewidth=1.2)
            ax.fill_betweenx(depth, 0, vsh_vals, where=(vsh_vals < 0.3), color="#16A34A", alpha=0.25)
            ax.fill_betweenx(depth, 0, vsh_vals, where=((vsh_vals >= 0.3) & (vsh_vals <= 0.5)), color="#EAB308", alpha=0.25)
            ax.fill_betweenx(depth, 0, vsh_vals, where=(vsh_vals > 0.5), color="#DC2626", alpha=0.25)
            ax.set_xlim(0, 1)
            ax.set_ylim(np.nanmax(depth), np.nanmin(depth))
            ax.set_xlabel("Vsh", fontsize=9)
            if idx == 0:
                ax.set_ylabel(depth_col, fontsize=9)
            ax.set_title(f"Vsh Track - {method_name}", fontsize=10)
            ax.grid(True, linestyle="--", alpha=0.2)

            if gr is not None and idx == 0:
                ax2 = ax.twiny()
                ax2.plot(gr, depth, color="#0EA5E9", linewidth=0.8, alpha=0.55)
                ax2.set_xlabel(gr_curve, fontsize=8)

        self._render_figure_to_host(self._vsh_track_host, fig)

    def _plot_vsh_distribution(self, df, method_columns: list[tuple[str, str]]) -> None:
        import pandas as pd
        from matplotlib.figure import Figure

        method_values: list[tuple[str, np.ndarray]] = []
        for method_name, col_name in method_columns:
            vals = pd.to_numeric(df.get(col_name), errors="coerce").dropna().to_numpy(dtype=float)
            if vals.size:
                method_values.append((method_name, vals))

        if not method_values:
            return

        n_methods = len(method_values)
        hist_fig = Figure(figsize=(4.8, max(3.4, 2.2 * n_methods)), dpi=100, constrained_layout=True)
        hist_axes = hist_fig.subplots(n_methods, 1)
        if n_methods == 1:
            hist_axes = [hist_axes]
        for ax, (method_name, values) in zip(hist_axes, method_values):
            ax.hist(values, bins=24, color="#3B82F6", alpha=0.8, edgecolor="#1D4ED8")
            ax.set_title(f"Vsh Histogram - {method_name}", fontsize=9)
            ax.set_xlabel("Vsh")
            ax.set_ylabel("Count")
            ax.grid(True, linestyle="--", alpha=0.2)

        box_fig = Figure(figsize=(4.8, max(3.4, 2.2 * n_methods)), dpi=100, constrained_layout=True)
        box_axes = box_fig.subplots(n_methods, 1)
        if n_methods == 1:
            box_axes = [box_axes]
        for ax, (method_name, values) in zip(box_axes, method_values):
            ax.boxplot(values, vert=False, patch_artist=True, boxprops={"facecolor": "#93C5FD", "edgecolor": "#1D4ED8"})
            ax.set_title(f"Vsh Boxplot - {method_name}", fontsize=9)
            ax.set_xlabel("Vsh")
            ax.grid(True, axis="x", linestyle="--", alpha=0.2)

        self._render_figure_to_host(self._vsh_hist_host, hist_fig)
        self._render_figure_to_host(self._vsh_box_host, box_fig)

    def _clear_vsh_distribution_hosts(self) -> None:
        for host in (self._vsh_hist_host, self._vsh_box_host):
            if host is None:
                continue
            layout = host.layout()
            if layout is None:
                continue
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()

    def _configure_vsh_method_selector(self, combo: QtWidgets.QComboBox) -> None:
        if combo is None:
            return

        combo.setEditable(True)
        if combo.lineEdit() is not None:
            combo.lineEdit().setReadOnly(True)
            combo.lineEdit().setPlaceholderText("Select one or more methods")

        model = combo.model()
        if model is None:
            return

        for i in range(combo.count()):
            item = model.item(i) if hasattr(model, "item") else None
            if item is None:
                continue
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setData(QtCore.Qt.Unchecked, QtCore.Qt.CheckStateRole)

        self._set_checked_vsh_methods([combo.itemText(0)] if combo.count() else [])
        model.dataChanged.connect(lambda *_: self._refresh_vsh_method_combo_text())
        self._refresh_vsh_method_combo_text()

    def _selected_vsh_methods(self) -> list[str]:
        combo = getattr(self.ui, "vshMethodComboBox", None)
        if combo is None:
            text = self._combo_text("comboVclMethod")
            return [text] if text else ["Linear"]

        selected: list[str] = []
        model = combo.model()
        if model is not None and hasattr(model, "item"):
            for i in range(combo.count()):
                item = model.item(i)
                if item is None:
                    continue
                state = item.data(QtCore.Qt.CheckStateRole)
                if state == QtCore.Qt.Checked:
                    selected.append(combo.itemText(i))

        if selected:
            return selected

        fallback = combo.currentText().strip()
        return [fallback] if fallback else ["Linear"]

    def _set_checked_vsh_methods(self, methods: list[str]) -> None:
        combo = getattr(self.ui, "vshMethodComboBox", None)
        if combo is None:
            return
        model = combo.model()
        if model is None or not hasattr(model, "item"):
            return

        selected = {m.strip() for m in methods if m and m.strip()}
        for i in range(combo.count()):
            item = model.item(i)
            if item is None:
                continue
            name = combo.itemText(i)
            state = QtCore.Qt.Checked if name in selected else QtCore.Qt.Unchecked
            item.setData(state, QtCore.Qt.CheckStateRole)
        self._refresh_vsh_method_combo_text()

    def _refresh_vsh_method_combo_text(self) -> None:
        combo = getattr(self.ui, "vshMethodComboBox", None)
        if combo is None or combo.lineEdit() is None:
            return

        methods = self._selected_vsh_methods()
        combo.lineEdit().setText(", ".join(methods))

    def _slugify_method(self, method_name: str) -> str:
        slug = "".join(ch if ch.isalnum() else "_" for ch in str(method_name).upper())
        while "__" in slug:
            slug = slug.replace("__", "_")
        return slug.strip("_") or "LINEAR"

    def _render_figure_to_host(self, host, fig) -> None:
        if host is None:
            return
        try:
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas  # type: ignore
        except Exception:
            return

        layout = host.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(host)
            layout.setContentsMargins(0, 0, 0, 0)

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        canvas = FigureCanvas(fig)
        layout.addWidget(canvas, 1)
        canvas.draw_idle()

    def _send_vsh_to_workflow(self):
        well = self.data._get_current_well()
        if well is None:
            return
        df = getattr(well, "data", None)
        if df is None or "VSH" not in df.columns:
            QtWidgets.QMessageBox.information(self.ui, "Vsh Workflow", "Run Vsh first, then send to interpretation.")
            return
        QtWidgets.QMessageBox.information(
            self.ui,
            "Vsh Workflow",
            "VSH is available for Porosity, Sw, and Net Pay workflows.",
        )
        tab_widget = getattr(self.ui, "centralTabWidget", None)
        por_tab = getattr(self.ui, "tabPorosity", None)
        if tab_widget is not None and por_tab is not None:
            idx = tab_widget.indexOf(por_tab)
            if idx >= 0:
                tab_widget.setCurrentIndex(idx)

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

    def _line_float(self, name: str, default):
        text = self._line_text(name)
        if not text:
            return default
        try:
            return float(text)
        except ValueError:
            return default

    def _sync_gr_curve_line(self, df) -> None:
        line_widget = getattr(self.ui, "gRCurveLineEdit", None)
        if line_widget is None or not hasattr(line_widget, "setText"):
            return

        current = self._line_text("gRCurveLineEdit")
        if current and current in getattr(df, "columns", []):
            return

        curve_name = self._pick_gr_curve_name(df)
        if curve_name:
            line_widget.setText(curve_name)

    def _pick_gr_curve_name(self, df) -> str:
        columns = [str(c) for c in getattr(df, "columns", [])]
        if not columns:
            return ""

        upper = {c.upper(): c for c in columns}
        if "GR" in upper:
            return upper["GR"]

        for candidate in ("GAMMARAY", "GAMMA_RAY", "GR_API"):
            if candidate in upper:
                return upper[candidate]

        for col in columns:
            c = col.upper()
            if "GR" in c or "GAMMA" in c:
                return col

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

    def _format_value(self, value, column_name: str) -> str:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return "" if value is None else str(value)
        if column_name == "Depth":
            return f"{numeric:.2f}"
        if column_name in {"Vsh", "PHI", "Sw"}:
            return f"{numeric:.3f}"
        return f"{numeric:.0f}"

    def _set_label_text(self, name: str, text: str) -> None:
        widget = getattr(self.ui, name, None)
        if widget is not None and hasattr(widget, "setText"):
            widget.setText(text)
