"""Interpretation workflow connected to data."""
from __future__ import annotations

import numpy as np
from PyQt5 import QtCore, QtWidgets

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

    def compute_vsh(self):
        self.run_vsh_workflow()

    def run_vsh_workflow(self):
        well = self.data._get_current_well()
        if not well:
            return
        df = getattr(well, "data", None)
        if df is None:
            return

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
