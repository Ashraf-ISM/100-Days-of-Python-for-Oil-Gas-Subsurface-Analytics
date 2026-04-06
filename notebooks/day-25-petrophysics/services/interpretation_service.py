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
