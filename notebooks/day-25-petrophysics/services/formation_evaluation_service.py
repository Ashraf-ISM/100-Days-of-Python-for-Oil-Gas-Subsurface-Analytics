"""Formation evaluation workspace helpers."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from PyQt5 import QtCore, QtWidgets

from calculations import net_pay, permeability, porosity, saturation, vshale


class FormationEvaluationService:
    def __init__(self, ui: QtWidgets.QMainWindow, data_service=None):
        self.ui = ui
        self.data = data_service
        self._plot_hosts: dict[str, QtWidgets.QWidget] = {}
        self._crossplot_host: QtWidgets.QWidget | None = None
        self._computed_definitions: dict[str, str] = {}
        self._computed_visibility: dict[str, bool] = {}
        self._last_result: dict | None = None

        tab_views = getattr(self.ui, "tabFEViews", None)
        if tab_views is not None:
            tab_views.setCurrentIndex(0)

        self._build_computed_logs_workspace()
        self._build_crossplot_workspace()
        self._wire_sensitivity_controls()

    def run_evaluation(self, *_args):
        result = self._build_result()
        if result is None:
            self.reset_evaluation()
            return

        self._last_result = result
        self._update_summary(result)
        self._fill_pay_table(result)
        self._render_tracks(result)
        self._update_secondary_placeholders(result)
        self._refresh_computed_log_manager(result)
        self._refresh_crossplot_curve_options()
        self._update_crossplot()

    def reset_evaluation(self):
        self._last_result = None
        self._set_label("lblFENetIntervalValue", "--")
        self._set_label("lblFEAvgPhiValue", "--")
        self._set_label("lblFEAvgSwValue", "--")
        self._set_label(
            "lblFEComputedPlaceholder",
            "Computed log cards will appear here for VSH, PHIT, SW, PERM and NET_PAY after running the evaluation.",
        )
        self._set_label(
            "lblFECrossplotPlaceholder",
            "Crossplot workspace reserved for phi-Vsh-Sw overlays and pay-zone diagnostics.",
        )

        table = getattr(self.ui, "tableFEPaySummary", None)
        if table is not None:
            table.clearContents()
            table.setRowCount(0)

        self._show_placeholders()
        self._clear_computed_log_manager()
        self._clear_crossplot_canvas("Run formation evaluation to build crossplots.")

    def _build_computed_logs_workspace(self) -> None:
        page = getattr(self.ui, "tabFEComputedLogs", None)
        if page is None:
            return
        layout = page.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(page)

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        manager_frame = QtWidgets.QFrame(page)
        manager_frame.setStyleSheet("background:#FFFFFF;border:1px solid #D7E2EE;border-radius:8px;")
        manager_layout = QtWidgets.QVBoxLayout(manager_frame)
        manager_layout.setContentsMargins(10, 10, 10, 10)
        manager_layout.setSpacing(8)

        title = QtWidgets.QLabel("Computed Log Management", manager_frame)
        title.setStyleSheet("font-size:14px;font-weight:700;color:#274B72;")
        manager_layout.addWidget(title)

        button_row = QtWidgets.QHBoxLayout()
        self.btn_fe_refresh_logs = QtWidgets.QPushButton("Refresh", manager_frame)
        self.btn_fe_rename_log = QtWidgets.QPushButton("Rename", manager_frame)
        self.btn_fe_delete_log = QtWidgets.QPushButton("Delete", manager_frame)
        self.btn_fe_add_tracks = QtWidgets.QPushButton("Add To Tracks", manager_frame)
        self.btn_fe_export_logs = QtWidgets.QPushButton("Export CSV", manager_frame)
        self.btn_fe_save_project = QtWidgets.QPushButton("Save Into Project", manager_frame)
        for button in (
            self.btn_fe_refresh_logs,
            self.btn_fe_rename_log,
            self.btn_fe_delete_log,
            self.btn_fe_add_tracks,
            self.btn_fe_export_logs,
            self.btn_fe_save_project,
        ):
            button_row.addWidget(button)
        button_row.addStretch(1)
        manager_layout.addLayout(button_row)

        rename_row = QtWidgets.QHBoxLayout()
        self.line_fe_rename_from = QtWidgets.QLineEdit(manager_frame)
        self.line_fe_rename_to = QtWidgets.QLineEdit(manager_frame)
        self.line_fe_rename_from.setPlaceholderText("Current log name")
        self.line_fe_rename_to.setPlaceholderText("New log name")
        rename_row.addWidget(self.line_fe_rename_from)
        rename_row.addWidget(self.line_fe_rename_to)
        manager_layout.addLayout(rename_row)

        self.table_fe_computed_logs = QtWidgets.QTableWidget(manager_frame)
        self.table_fe_computed_logs.setColumnCount(5)
        self.table_fe_computed_logs.setHorizontalHeaderLabels(["Visible", "Log", "Source", "Min", "Max"])
        self.table_fe_computed_logs.setAlternatingRowColors(True)
        self.table_fe_computed_logs.horizontalHeader().setStretchLastSection(True)
        manager_layout.addWidget(self.table_fe_computed_logs, 1)

        compare_frame = QtWidgets.QFrame(page)
        compare_frame.setStyleSheet("background:#FFFFFF;border:1px solid #D7E2EE;border-radius:8px;")
        compare_layout = QtWidgets.QVBoxLayout(compare_frame)
        compare_layout.setContentsMargins(10, 10, 10, 10)
        compare_layout.setSpacing(8)
        compare_title = QtWidgets.QLabel("Method Comparison & Sensitivity", compare_frame)
        compare_title.setStyleSheet("font-size:14px;font-weight:700;color:#274B72;")
        compare_layout.addWidget(compare_title)

        self.lbl_fe_method_summary = QtWidgets.QLabel(
            "Vsh comparison: Linear/Larionov/Clavier | Sw comparison: Archie/Simandoux",
            compare_frame,
        )
        self.lbl_fe_method_summary.setWordWrap(True)
        self.lbl_fe_method_summary.setStyleSheet("color:#5C718A;font-size:12px;")
        compare_layout.addWidget(self.lbl_fe_method_summary)

        self.check_fe_live_sensitivity = QtWidgets.QCheckBox("Live sensitivity update", compare_frame)
        self.check_fe_live_sensitivity.setChecked(True)
        compare_layout.addWidget(self.check_fe_live_sensitivity)

        custom_frame = QtWidgets.QFrame(page)
        custom_frame.setStyleSheet("background:#FFFFFF;border:1px solid #D7E2EE;border-radius:8px;")
        custom_layout = QtWidgets.QVBoxLayout(custom_frame)
        custom_layout.setContentsMargins(10, 10, 10, 10)
        custom_layout.setSpacing(8)

        custom_title = QtWidgets.QLabel("Custom Log Builder", custom_frame)
        custom_title.setStyleSheet("font-size:14px;font-weight:700;color:#274B72;")
        custom_layout.addWidget(custom_title)

        self.line_fe_custom_name = QtWidgets.QLineEdit(custom_frame)
        self.line_fe_custom_name.setPlaceholderText("Output log name (example: PHIE_CORR)")
        self.line_fe_custom_expr = QtWidgets.QLineEdit(custom_frame)
        self.line_fe_custom_expr.setPlaceholderText("Expression (example: PHI*(1-VSH_LINEAR))")
        self.btn_fe_build_custom = QtWidgets.QPushButton("Build Custom Log", custom_frame)
        self.lbl_fe_custom_hint = QtWidgets.QLabel(
            "Available variables include existing curves and computed logs (VSH_LINEAR, VSH_LARIONOV, VSH_CLAVIER, SW_ARCHIE, SW_SIMANDOUX, PHI).",
            custom_frame,
        )
        self.lbl_fe_custom_hint.setWordWrap(True)
        self.lbl_fe_custom_hint.setStyleSheet("color:#5C718A;font-size:11px;")

        custom_layout.addWidget(self.line_fe_custom_name)
        custom_layout.addWidget(self.line_fe_custom_expr)
        custom_layout.addWidget(self.btn_fe_build_custom)
        custom_layout.addWidget(self.lbl_fe_custom_hint)

        self.table_fe_preview = QtWidgets.QTableWidget(custom_frame)
        self.table_fe_preview.setColumnCount(5)
        self.table_fe_preview.setHorizontalHeaderLabels(["Depth", "VSH", "PHI", "SW", "Flag"])
        self.table_fe_preview.setAlternatingRowColors(True)
        self.table_fe_preview.horizontalHeader().setStretchLastSection(True)
        custom_layout.addWidget(self.table_fe_preview)

        layout.addWidget(manager_frame, 2)
        layout.addWidget(compare_frame, 1)
        layout.addWidget(custom_frame, 2)

        self.btn_fe_refresh_logs.clicked.connect(self._refresh_computed_log_manager)
        self.btn_fe_rename_log.clicked.connect(self._rename_selected_log)
        self.btn_fe_delete_log.clicked.connect(self._delete_selected_log)
        self.btn_fe_add_tracks.clicked.connect(self._add_selected_logs_to_tracks)
        self.btn_fe_export_logs.clicked.connect(self._export_computed_logs)
        self.btn_fe_save_project.clicked.connect(self._mark_project_modified)
        self.btn_fe_build_custom.clicked.connect(self._build_custom_log)

    def _build_crossplot_workspace(self) -> None:
        page = getattr(self.ui, "tabFECrossplots", None)
        if page is None:
            return
        layout = page.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(page)

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        controls_frame = QtWidgets.QFrame(page)
        controls_frame.setStyleSheet("background:#FFFFFF;border:1px solid #D7E2EE;border-radius:8px;")
        controls_layout = QtWidgets.QGridLayout(controls_frame)
        controls_layout.setContentsMargins(10, 10, 10, 10)
        controls_layout.setHorizontalSpacing(8)
        controls_layout.setVerticalSpacing(6)

        self.combo_fe_x = QtWidgets.QComboBox(controls_frame)
        self.combo_fe_y = QtWidgets.QComboBox(controls_frame)
        self.combo_fe_color = QtWidgets.QComboBox(controls_frame)
        self.combo_fe_style = QtWidgets.QComboBox(controls_frame)
        self.combo_fe_style.addItems(["Scatter", "Hexbin"])
        self.check_fe_trendline = QtWidgets.QCheckBox("Trendline", controls_frame)
        self.check_fe_trendline.setChecked(True)
        self.btn_fe_crossplot_update = QtWidgets.QPushButton("Update Crossplot", controls_frame)

        controls_layout.addWidget(QtWidgets.QLabel("X", controls_frame), 0, 0)
        controls_layout.addWidget(self.combo_fe_x, 0, 1)
        controls_layout.addWidget(QtWidgets.QLabel("Y", controls_frame), 0, 2)
        controls_layout.addWidget(self.combo_fe_y, 0, 3)
        controls_layout.addWidget(QtWidgets.QLabel("Color", controls_frame), 1, 0)
        controls_layout.addWidget(self.combo_fe_color, 1, 1)
        controls_layout.addWidget(QtWidgets.QLabel("Style", controls_frame), 1, 2)
        controls_layout.addWidget(self.combo_fe_style, 1, 3)
        controls_layout.addWidget(self.check_fe_trendline, 0, 4)
        controls_layout.addWidget(self.btn_fe_crossplot_update, 1, 4)

        stats_row = QtWidgets.QHBoxLayout()
        self.lbl_fe_crossplot_stats = QtWidgets.QLabel("R²: -- | N: -- | slope: --")
        self.lbl_fe_crossplot_stats.setStyleSheet("color:#5C718A;font-size:12px;")
        stats_row.addWidget(self.lbl_fe_crossplot_stats)
        stats_row.addStretch(1)

        canvas_frame = QtWidgets.QFrame(page)
        canvas_frame.setStyleSheet("background:#FFFFFF;border:1px solid #D7E2EE;border-radius:8px;")
        canvas_layout = QtWidgets.QVBoxLayout(canvas_frame)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setSpacing(0)

        self.frame_fe_crossplot_canvas = canvas_frame
        layout.addWidget(controls_frame)
        layout.addLayout(stats_row)
        layout.addWidget(canvas_frame, 1)

        self.btn_fe_crossplot_update.clicked.connect(self._update_crossplot)
        self.combo_fe_x.currentTextChanged.connect(lambda _text: self._on_live_crossplot())
        self.combo_fe_y.currentTextChanged.connect(lambda _text: self._on_live_crossplot())
        self.combo_fe_color.currentTextChanged.connect(lambda _text: self._on_live_crossplot())
        self.combo_fe_style.currentTextChanged.connect(lambda _text: self._on_live_crossplot())
        self.check_fe_trendline.toggled.connect(lambda _checked: self._on_live_crossplot())

    def _wire_sensitivity_controls(self) -> None:
        for name in (
            "spinFEGRMin",
            "spinFEGRMax",
            "spinFERhoMa",
            "spinFERhoF",
            "spinFEArchieA",
            "spinFEArchieM",
            "spinFEArchieN",
            "spinFERw",
            "spinFEFrom",
            "spinFETo",
        ):
            widget = getattr(self.ui, name, None)
            if widget is not None and hasattr(widget, "valueChanged"):
                widget.valueChanged.connect(self._on_sensitivity_changed)
        for name in ("comboFEDepthPreset", "comboFEDepthUnit", "vshTypeComboBox"):
            widget = getattr(self.ui, name, None)
            if widget is not None and hasattr(widget, "currentTextChanged"):
                widget.currentTextChanged.connect(lambda _text: self._on_sensitivity_changed())

    def _on_sensitivity_changed(self, *_args) -> None:
        live = getattr(self, "check_fe_live_sensitivity", None)
        if live is None or not live.isChecked():
            return
        if self._last_result is not None:
            self.run_evaluation()

    def _on_live_crossplot(self) -> None:
        if self._last_result is not None:
            self._update_crossplot()

    def _build_result(self):
        well = self.data._get_current_well() if self.data is not None else None
        df = getattr(well, "data", None) if well is not None else None
        if df is None or getattr(df, "empty", True):
            return None

        use_vsh = self._is_checked("checkFEVsh", True)
        use_gr = self._is_checked("checkFEGR", True) and use_vsh
        use_rhob = self._is_checked("checkFERHOB", True)
        use_nphi = self._is_checked("checkFENPHI", True)
        use_rt = self._is_checked("checkFERT", True)

        depth_label, depth_series = self._depth_series(df)
        visible_mask = depth_series.notna()
        visible_mask &= self._depth_mask(depth_series, well)
        if not visible_mask.any():
            QtWidgets.QMessageBox.information(self.ui, "Formation Evaluation", "No samples found in the selected depth range.")
            return None

        gr_name_for_view = self._first_available_curve(df, ("GR", "SGR", "GAMMA"))
        gr_name = gr_name_for_view if use_gr else None
        rhob_name = self._first_available_curve(df, ("RHOB", "RHOZ", "DEN")) if use_rhob else None
        nphi_name = self._first_available_curve(df, ("NPHI", "NEU", "PHIN")) if use_nphi else None
        rt_name = self._first_available_curve(df, ("RT", "LLD", "ILD", "RESD", "RDEP")) if use_rt else None

        if use_vsh and gr_name is None:
            QtWidgets.QMessageBox.warning(self.ui, "Formation Evaluation", "A gamma ray curve is required to run formation evaluation.")
            return None
        if rhob_name is None and nphi_name is None:
            QtWidgets.QMessageBox.warning(self.ui, "Formation Evaluation", "A density and/or neutron curve is required to estimate porosity.")
            return None
        if rt_name is None:
            QtWidgets.QMessageBox.warning(self.ui, "Formation Evaluation", "A resistivity curve (RT/LLD/ILD) is required to estimate water saturation.")
            return None

        if gr_name_for_view is not None:
            gr = pd.to_numeric(df[gr_name_for_view], errors="coerce")
        else:
            gr = pd.Series(np.nan, index=df.index)
        rhob = pd.to_numeric(df[rhob_name], errors="coerce") if rhob_name is not None else pd.Series(np.nan, index=df.index)
        nphi = pd.to_numeric(df[nphi_name], errors="coerce") if nphi_name is not None else pd.Series(np.nan, index=df.index)
        rt = pd.to_numeric(df[rt_name], errors="coerce")

        gr_min = self._spin_value("spinFEGRMin", 50.0)
        gr_max = self._spin_value("spinFEGRMax", 120.0)
        rho_ma = self._spin_value("spinFERhoMa", 2.65)
        rho_f = self._spin_value("spinFERhoF", 1.0)
        archie_a = self._spin_value("spinFEArchieA", 1.0)
        archie_m = self._spin_value("spinFEArchieM", 2.0)
        archie_n = self._spin_value("spinFEArchieN", 2.0)
        rw = self._spin_value("spinFERw", 0.05)
        vsh_model = self._combo_text("vshTypeComboBox", "Linear")

        model_alias = {
            "linear": "linear",
            "larionov": "larionov_tertiary",
            "clavier": "clavier",
        }

        vsh_linear = pd.Series(
            vshale.compute_vsh_gr(gr.to_numpy(dtype=float), gr_min=gr_min, gr_max=gr_max, model="linear"),
            index=df.index,
        )
        vsh_larionov = pd.Series(
            vshale.compute_vsh_gr(
                gr.to_numpy(dtype=float),
                gr_min=gr_min,
                gr_max=gr_max,
                model="larionov_tertiary",
            ),
            index=df.index,
        )
        vsh_clavier = pd.Series(
            vshale.compute_vsh_gr(gr.to_numpy(dtype=float), gr_min=gr_min, gr_max=gr_max, model="clavier"),
            index=df.index,
        )

        vsh_key = model_alias.get(vsh_model.lower(), "linear")
        if use_vsh:
            if vsh_key == "larionov_tertiary":
                vsh = vsh_larionov
            elif vsh_key == "clavier":
                vsh = vsh_clavier
            else:
                vsh = vsh_linear
        else:
            vsh = pd.Series(0.0, index=df.index)
        if nphi_name is not None and rhob_name is not None:
            phi = pd.Series(
                porosity.compute_phi_combo(
                    nphi.to_numpy(dtype=float),
                    rhob.to_numpy(dtype=float),
                    rho_ma=rho_ma,
                    rho_f=rho_f,
                ),
                index=df.index,
            )
        else:
            phi = pd.Series(
                porosity.compute_phi_from_density(
                    rhob.to_numpy(dtype=float),
                    rho_ma=rho_ma,
                    rho_f=rho_f,
                ),
                index=df.index,
            )

        sw = pd.Series(
            saturation.compute_sw_archie(
                phi.to_numpy(dtype=float),
                rt.to_numpy(dtype=float),
                rw=rw,
                a=archie_a,
                m=archie_m,
                n=archie_n,
            ),
            index=df.index,
        )

        # Simple Simandoux-style approximation for comparison workflow.
        simandoux_term = (vsh * 0.5) + ((archie_a * rw) / (rt * (np.power(np.clip(phi, 1e-6, 1.0), archie_m)) + 1e-9))
        sw_simandoux = pd.Series(np.clip(np.sqrt(np.clip(simandoux_term, 0.0, None)), 0.0, 1.0), index=df.index)

        perm = pd.Series(permeability.compute_perm_timur(phi.to_numpy(dtype=float), sw.to_numpy(dtype=float)), index=df.index)
        pay_flag = pd.Series(
            net_pay.compute_net_pay(
                vsh.to_numpy(dtype=float),
                phi.to_numpy(dtype=float),
                sw.to_numpy(dtype=float),
                perm.to_numpy(dtype=float),
                vsh_cut=0.40 if use_vsh else 1.0,
                phi_cut=0.08,
                sw_cut=0.65,
                perm_cut=0.10,
            ),
            index=df.index,
        )

        result = pd.DataFrame(
            {
                "depth": depth_series,
                "GR": gr,
                "VSH_LINEAR": vsh_linear,
                "VSH_LARIONOV": vsh_larionov,
                "VSH_CLAVIER": vsh_clavier,
                "VSH": vsh,
                "PHI": phi,
                "SW": sw,
                "SW_ARCHIE": sw,
                "SW_SIMANDOUX": sw_simandoux,
                "PERM": perm,
                "NET_PAY": pay_flag,
            }
        )
        result = result.loc[visible_mask].copy()
        result = result.replace([np.inf, -np.inf], np.nan).dropna(subset=["depth"])
        if result.empty:
            return None

        # Persist computed logs on the active well dataframe so other tabs can reuse them.
        self._store_computed_logs(df, result)

        return {
            "depth_label": depth_label,
            "data": result.sort_values("depth"),
            "gr_name": gr_name_for_view or "GR",
            "rhob_name": rhob_name or "",
            "nphi_name": nphi_name or "",
            "rt_name": rt_name,
            "vsh_model": vsh_model,
            "use_vsh": use_vsh,
        }

    def _update_summary(self, result) -> None:
        data = result["data"]
        pay_rows = data.loc[data["NET_PAY"] == 1]

        step = self._depth_step(data["depth"])
        net_thickness = float(pay_rows.shape[0]) * step
        avg_phi = float(pay_rows["PHI"].mean()) if not pay_rows.empty else float(data["PHI"].mean())
        avg_sw = float(pay_rows["SW"].mean()) if not pay_rows.empty else float(data["SW"].mean())

        self._set_label("lblFENetIntervalValue", f"{net_thickness:.1f}")
        self._set_label("lblFEAvgPhiValue", f"{avg_phi:.2f}")
        self._set_label("lblFEAvgSwValue", f"{avg_sw:.2f}")

    def _fill_pay_table(self, result) -> None:
        table = getattr(self.ui, "tableFEPaySummary", None)
        if table is None:
            return

        data = result["data"]
        pay_rows = data.loc[data["NET_PAY"] == 1]
        if pay_rows.empty:
            preview = data.nsmallest(min(12, len(data)), "SW")
        else:
            sample_size = min(18, len(pay_rows))
            sample_indices = np.linspace(0, len(pay_rows) - 1, sample_size, dtype=int)
            preview = pay_rows.iloc[np.unique(sample_indices)]

        rows: list[tuple[str, str, str, str, str]] = []
        for _, row in preview.iterrows():
            rows.append(
                (
                    self._fmt_number(row["depth"], 2),
                    self._fmt_number(row["VSH"], 2),
                    self._fmt_number(row["PHI"], 2),
                    self._fmt_number(row["SW"], 2),
                    "Pay Zone" if int(row["NET_PAY"]) == 1 else "Review",
                )
            )

        table.clearContents()
        table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for col_index, value in enumerate(row):
                item = QtWidgets.QTableWidgetItem(value)
                table.setItem(row_index, col_index, item)
        table.resizeColumnsToContents()

    def _render_tracks(self, result) -> None:
        try:
            from matplotlib.figure import Figure
        except Exception:
            return

        data = result["data"]
        depth = data["depth"]
        pay_flag = data["NET_PAY"]

        track_specs = (
            (
                "frameFEGammaTrack",
                "lblFEGammaPlaceholder",
                f"{result['gr_name']} Track",
                data["GR"],
                "#3E4C59",
            ),
            (
                "frameFEVshTrack",
                "lblFEVshPlaceholder",
                "VSH Track",
                data["VSH"],
                "#2CA58D",
            ),
            (
                "frameFEPorosityTrack",
                "lblFEPorosityPlaceholder",
                "Porosity Track",
                data["PHI"],
                "#2B6CB0",
            ),
            (
                "frameFESwTrack",
                "lblFESwPlaceholder",
                "Water Saturation Track",
                data["SW"],
                "#2563EB",
            ),
        )

        for frame_name, placeholder_name, title, values, color in track_specs:
            fig = Figure(figsize=(2.1, 6.0), tight_layout=True)
            ax = fig.add_subplot(111)
            ax.set_facecolor("#FBFCFE")
            ax.plot(values, depth, color=color, linewidth=1.1)
            if pay_flag.any():
                x0, x1 = self._value_bounds(values)
                ax.fill_betweenx(
                    depth,
                    x0,
                    x1,
                    where=pay_flag.to_numpy(dtype=bool),
                    color="#DFF3E8",
                    alpha=0.9,
                )
            ax.set_title(title, fontsize=9.5, fontweight="bold", color="#24466B")
            ax.grid(color="#DFE8F1", linewidth=0.7)
            ax.tick_params(labelsize=7)
            ax.invert_yaxis()
            self._render_figure(frame_name, placeholder_name, fig)

        pay_fig = Figure(figsize=(8.0, 2.3), tight_layout=True)
        pay_ax = pay_fig.add_subplot(111)
        pay_ax.set_facecolor("#FBFCFE")
        pay_ax.plot(depth, pay_flag, color="#2B6CB0", linewidth=1.2)
        pay_ax.fill_between(depth, 0, pay_flag, color="#90CDF4", alpha=0.8, step="mid")
        pay_ax.set_ylim(-0.05, 1.05)
        pay_ax.set_title("Net Pay Flag", fontsize=10, fontweight="bold", color="#24466B")
        pay_ax.set_xlabel(result["depth_label"], fontsize=8.5, color="#24466B")
        pay_ax.set_yticks([0, 1])
        pay_ax.set_yticklabels(["No", "Pay"])
        pay_ax.grid(color="#E5EDF5", linewidth=0.7)
        pay_ax.tick_params(labelsize=8)
        self._render_figure("frameFEPayChart", "lblFEPayChartPlaceholder", pay_fig)

    def _update_secondary_placeholders(self, result) -> None:
        data = result["data"]
        vsh_suffix = (
            f" ({result.get('vsh_model', 'Linear')})"
            if result.get("use_vsh", True)
            else " (disabled)"
        )
        self._set_label(
            "lblFEComputedPlaceholder",
            (
                f"Computed logs ready: VSH{vsh_suffix} {data['VSH'].mean():.2f} avg, "
                f"PHI {data['PHI'].mean():.2f} avg, "
                f"SW {data['SW'].mean():.2f} avg, "
                f"PERM {data['PERM'].median():.1f} median."
            ),
        )
        self._set_label(
            "lblFECrossplotPlaceholder",
            (
                "Crossplot diagnostics can be added next. "
                f"Current inputs: {result['gr_name']}, {result['rhob_name'] or 'density'}, "
                f"{result['nphi_name'] or 'neutron'} and {result['rt_name']}."
            ),
        )

    def _store_computed_logs(self, df, result_df: pd.DataFrame) -> None:
        index_match = result_df.index
        columns_to_store = {
            "VSH": "VSH selected model",
            "VSH_LINEAR": "VSH linear",
            "VSH_LARIONOV": "VSH Larionov",
            "VSH_CLAVIER": "VSH Clavier",
            "PHI": "Porosity",
            "SW": "Water saturation",
            "SW_ARCHIE": "SW Archie",
            "SW_SIMANDOUX": "SW Simandoux",
            "PERM": "Permeability",
            "NET_PAY": "Net pay flag",
        }

        for name, source in columns_to_store.items():
            if name not in result_df.columns:
                continue
            if name not in df.columns:
                df[name] = np.nan
            df.loc[index_match, name] = result_df[name].to_numpy()
            self._computed_definitions[name] = source
            self._computed_visibility.setdefault(name, True)

    def _refresh_computed_log_manager(self, result: dict | None = None) -> None:
        if result is None:
            result = self._last_result
        table = getattr(self, "table_fe_computed_logs", None)
        if table is None:
            return

        well = self.data._get_current_well() if self.data is not None else None
        df = getattr(well, "data", None) if well is not None else None
        if df is None:
            self._clear_computed_log_manager()
            return

        computed_logs = [name for name in df.columns if name in self._computed_definitions or name in {"VSH", "PHI", "SW", "PERM", "NET_PAY"}]
        if not computed_logs:
            self._clear_computed_log_manager()
            return

        table.blockSignals(True)
        try:
            table.itemChanged.disconnect(self._on_computed_table_item_changed)
        except Exception:
            pass
        table.setRowCount(len(computed_logs))
        for row_index, log_name in enumerate(computed_logs):
            visible = self._computed_visibility.get(log_name, True)
            check_item = QtWidgets.QTableWidgetItem()
            check_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsSelectable)
            check_item.setCheckState(QtCore.Qt.Checked if visible else QtCore.Qt.Unchecked)
            table.setItem(row_index, 0, check_item)

            table.setItem(row_index, 1, QtWidgets.QTableWidgetItem(log_name))
            source_text = self._computed_definitions.get(log_name, "Computed")
            table.setItem(row_index, 2, QtWidgets.QTableWidgetItem(source_text))

            series = pd.to_numeric(df[log_name], errors="coerce")
            min_val = "--" if series.dropna().empty else f"{float(series.min()):.3f}"
            max_val = "--" if series.dropna().empty else f"{float(series.max()):.3f}"
            table.setItem(row_index, 3, QtWidgets.QTableWidgetItem(min_val))
            table.setItem(row_index, 4, QtWidgets.QTableWidgetItem(max_val))

        table.blockSignals(False)
        table.resizeColumnsToContents()
        table.itemChanged.connect(self._on_computed_table_item_changed)

        if result is not None:
            self._update_preview_table(result["data"])
            self.lbl_fe_method_summary.setText(
                (
                    f"Vsh avg: linear {result['data']['VSH_LINEAR'].mean():.2f}, "
                    f"larionov {result['data']['VSH_LARIONOV'].mean():.2f}, "
                    f"clavier {result['data']['VSH_CLAVIER'].mean():.2f} | "
                    f"Sw avg: archie {result['data']['SW_ARCHIE'].mean():.2f}, "
                    f"simandoux {result['data']['SW_SIMANDOUX'].mean():.2f}"
                )
            )

    def _clear_computed_log_manager(self) -> None:
        table = getattr(self, "table_fe_computed_logs", None)
        if table is not None:
            table.blockSignals(True)
            table.clearContents()
            table.setRowCount(0)
            table.blockSignals(False)
        preview = getattr(self, "table_fe_preview", None)
        if preview is not None:
            preview.clearContents()
            preview.setRowCount(0)

    def _on_computed_table_item_changed(self, item: QtWidgets.QTableWidgetItem) -> None:
        if item.column() != 0:
            return
        table = self.table_fe_computed_logs
        name_item = table.item(item.row(), 1)
        if name_item is None:
            return
        log_name = name_item.text().strip()
        self._computed_visibility[log_name] = item.checkState() == QtCore.Qt.Checked
        if self._last_result is not None:
            self._render_tracks(self._last_result)

    def _selected_computed_logs(self) -> list[str]:
        table = getattr(self, "table_fe_computed_logs", None)
        if table is None:
            return []
        rows = table.selectionModel().selectedRows()
        selected = []
        for idx in rows:
            item = table.item(idx.row(), 1)
            if item is not None:
                selected.append(item.text().strip())
        return selected

    def _rename_selected_log(self) -> None:
        well = self.data._get_current_well() if self.data is not None else None
        df = getattr(well, "data", None) if well is not None else None
        if df is None:
            return

        old_name = self.line_fe_rename_from.text().strip()
        new_name = self.line_fe_rename_to.text().strip()
        if not old_name:
            selected = self._selected_computed_logs()
            old_name = selected[0] if selected else ""
        if not old_name or old_name not in df.columns:
            QtWidgets.QMessageBox.information(self.ui, "Computed Logs", "Select a valid log to rename.")
            return
        if not new_name:
            QtWidgets.QMessageBox.information(self.ui, "Computed Logs", "Enter a new log name.")
            return
        if new_name in df.columns:
            QtWidgets.QMessageBox.warning(self.ui, "Computed Logs", "A log with this name already exists.")
            return

        df.rename(columns={old_name: new_name}, inplace=True)
        if old_name in self._computed_definitions:
            self._computed_definitions[new_name] = self._computed_definitions.pop(old_name)
        if old_name in self._computed_visibility:
            self._computed_visibility[new_name] = self._computed_visibility.pop(old_name)

        self._mark_project_modified()
        self._refresh_computed_log_manager()
        self._refresh_crossplot_curve_options()

    def _delete_selected_log(self) -> None:
        well = self.data._get_current_well() if self.data is not None else None
        df = getattr(well, "data", None) if well is not None else None
        if df is None:
            return

        selected = self._selected_computed_logs()
        if not selected:
            QtWidgets.QMessageBox.information(self.ui, "Computed Logs", "Select at least one computed log to delete.")
            return
        protected = {"DEPTH", "DEPT", "MD"}
        drop_logs = [name for name in selected if name not in protected]
        if not drop_logs:
            return

        df.drop(columns=[name for name in drop_logs if name in df.columns], inplace=True, errors="ignore")
        for name in drop_logs:
            self._computed_definitions.pop(name, None)
            self._computed_visibility.pop(name, None)

        self._mark_project_modified()
        self._refresh_computed_log_manager()
        self._refresh_crossplot_curve_options()

    def _add_selected_logs_to_tracks(self) -> None:
        selected = self._selected_computed_logs()
        if not selected:
            QtWidgets.QMessageBox.information(self.ui, "Computed Logs", "Select one or more logs first.")
            return

        for combo_name in ("multitrackcomboBox", "triplecombotrack1", "triplecombotrack2", "triplecombotrack3"):
            combo = getattr(self.ui, combo_name, None)
            if combo is None:
                continue
            model = combo.model()
            if model is None:
                continue
            for i in range(model.rowCount()):
                item = getattr(model, "item", lambda _index: None)(i)
                if item is None:
                    continue
                if item.text() in selected and hasattr(item, "setCheckState"):
                    item.setCheckState(QtCore.Qt.Checked)

        QtWidgets.QMessageBox.information(self.ui, "Computed Logs", "Selected logs were added to track selections.")

    def _export_computed_logs(self) -> None:
        well = self.data._get_current_well() if self.data is not None else None
        df = getattr(well, "data", None) if well is not None else None
        if df is None:
            return

        selected = self._selected_computed_logs()
        if not selected:
            selected = [name for name in df.columns if name in self._computed_definitions]
        if not selected:
            QtWidgets.QMessageBox.information(self.ui, "Computed Logs", "No computed logs available to export.")
            return

        depth_col = "DEPTH" if "DEPTH" in df.columns else ("DEPT" if "DEPT" in df.columns else None)
        export_cols = ([depth_col] if depth_col else []) + [name for name in selected if name in df.columns]

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.ui,
            "Export Computed Logs",
            "computed_logs.csv",
            "CSV Files (*.csv)",
        )
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path = f"{path}.csv"

        df[export_cols].to_csv(path, index=False)
        QtWidgets.QMessageBox.information(self.ui, "Computed Logs", f"Computed logs exported:\n{path}")

    def _build_custom_log(self) -> None:
        well = self.data._get_current_well() if self.data is not None else None
        df = getattr(well, "data", None) if well is not None else None
        if df is None:
            return

        out_name = self.line_fe_custom_name.text().strip()
        expression = self.line_fe_custom_expr.text().strip()
        if not out_name or not expression:
            QtWidgets.QMessageBox.information(self.ui, "Custom Log", "Enter output name and expression.")
            return

        try:
            eval_locals = {col: pd.to_numeric(df[col], errors="coerce") for col in df.columns}
            eval_locals.update({"np": np, "pd": pd})
            value = eval(expression, {"__builtins__": {}}, eval_locals)
            if np.isscalar(value):
                df[out_name] = float(value)
            else:
                series = pd.Series(value, index=df.index)
                df[out_name] = pd.to_numeric(series, errors="coerce")
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self.ui, "Custom Log", f"Failed to build custom log:\n{exc}")
            return

        self._computed_definitions[out_name] = f"Custom: {expression}"
        self._computed_visibility[out_name] = True
        self._mark_project_modified()
        self._refresh_computed_log_manager()
        self._refresh_crossplot_curve_options()

    def _update_preview_table(self, data: pd.DataFrame) -> None:
        table = getattr(self, "table_fe_preview", None)
        if table is None:
            return
        preview = data[["depth", "VSH", "PHI", "SW", "NET_PAY"]].head(30)
        table.setRowCount(len(preview))
        for row_index, (_, row) in enumerate(preview.iterrows()):
            values = (
                self._fmt_number(row["depth"], 2),
                self._fmt_number(row["VSH"], 3),
                self._fmt_number(row["PHI"], 3),
                self._fmt_number(row["SW"], 3),
                "Pay" if int(row["NET_PAY"]) == 1 else "No",
            )
            for col_index, value in enumerate(values):
                table.setItem(row_index, col_index, QtWidgets.QTableWidgetItem(value))
        table.resizeColumnsToContents()

    def _refresh_crossplot_curve_options(self) -> None:
        well = self.data._get_current_well() if self.data is not None else None
        df = getattr(well, "data", None) if well is not None else None
        if df is None:
            return

        numeric_cols = [name for name in df.columns if pd.api.types.is_numeric_dtype(df[name])]
        for combo in (getattr(self, "combo_fe_x", None), getattr(self, "combo_fe_y", None), getattr(self, "combo_fe_color", None)):
            if combo is None:
                continue
            current = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            if combo is getattr(self, "combo_fe_color", None):
                combo.addItem("None")
                combo.addItem("Depth")
            combo.addItems(numeric_cols)
            if current:
                idx = combo.findText(current)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            combo.blockSignals(False)

    def _update_crossplot(self) -> None:
        well = self.data._get_current_well() if self.data is not None else None
        df = getattr(well, "data", None) if well is not None else None
        if df is None:
            self._clear_crossplot_canvas("Load data first.")
            return

        x_name = self.combo_fe_x.currentText().strip()
        y_name = self.combo_fe_y.currentText().strip()
        color_name = self.combo_fe_color.currentText().strip()
        if not x_name or not y_name or x_name not in df.columns or y_name not in df.columns:
            self._clear_crossplot_canvas("Select valid X and Y curves.")
            return

        depth_label, depth_series = self._depth_series(df)
        mask = self._depth_mask(depth_series, well)
        x = pd.to_numeric(df[x_name], errors="coerce")
        y = pd.to_numeric(df[y_name], errors="coerce")
        valid = mask & x.notna() & y.notna()
        if not valid.any():
            self._clear_crossplot_canvas("No samples in selected depth filter.")
            return

        plot_df = pd.DataFrame({"x": x[valid], "y": y[valid], "depth": depth_series[valid]})
        cmap_values = None
        if color_name and color_name != "None" and color_name in df.columns:
            color_series = pd.to_numeric(df[color_name], errors="coerce")[valid]
            plot_df = plot_df.loc[color_series.notna()]
            cmap_values = color_series.loc[color_series.notna()]
        elif color_name == "Depth":
            cmap_values = plot_df["depth"]

        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas  # type: ignore
            from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar  # type: ignore
        except Exception:
            return

        fig, ax = plt.subplots(figsize=(8.4, 5.1), constrained_layout=True)
        if self.combo_fe_style.currentText() == "Hexbin":
            hb = ax.hexbin(plot_df["x"], plot_df["y"], gridsize=35, cmap="viridis", mincnt=1)
            fig.colorbar(hb, ax=ax, label="Density")
        else:
            if cmap_values is not None:
                sc = ax.scatter(plot_df["x"], plot_df["y"], c=cmap_values, s=14, cmap="viridis", alpha=0.85)
                fig.colorbar(sc, ax=ax, label=color_name if color_name != "None" else "Value")
            else:
                ax.scatter(plot_df["x"], plot_df["y"], s=14, color="#2B6CB0", alpha=0.8)

        slope = intercept = r2 = np.nan
        if self.check_fe_trendline.isChecked() and len(plot_df) >= 3:
            slope, intercept = np.polyfit(plot_df["x"], plot_df["y"], 1)
            x_fit = np.linspace(float(plot_df["x"].min()), float(plot_df["x"].max()), 100)
            y_fit = slope * x_fit + intercept
            ax.plot(x_fit, y_fit, color="#D97706", linewidth=1.8)
            residual = plot_df["y"] - (slope * plot_df["x"] + intercept)
            ss_res = float(np.sum(residual ** 2))
            ss_tot = float(np.sum((plot_df["y"] - plot_df["y"].mean()) ** 2))
            r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else np.nan

        ax.set_title(f"Crossplot: {x_name} vs {y_name}", fontsize=12, fontweight="600")
        ax.set_xlabel(x_name)
        ax.set_ylabel(y_name)
        ax.grid(alpha=0.2)

        stats_text = f"R²: {self._fmt_number(r2, 3)} | N: {len(plot_df)} | slope: {self._fmt_number(slope, 4)}"
        self.lbl_fe_crossplot_stats.setText(stats_text)
        self._render_crossplot_canvas(fig, FigureCanvas, NavigationToolbar)

    def _render_crossplot_canvas(self, fig, canvas_cls, toolbar_cls) -> None:
        frame = getattr(self, "frame_fe_crossplot_canvas", None)
        if frame is None:
            return

        layout = frame.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(frame)
            layout.setContentsMargins(0, 0, 0, 0)

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        canvas = canvas_cls(fig)
        toolbar = toolbar_cls(canvas, frame)
        toolbar.setStyleSheet("QToolBar { background:#F7FAFD; border:0; border-bottom:1px solid #D5E1EC; }")
        layout.addWidget(toolbar)
        layout.addWidget(canvas, 1)
        canvas.draw_idle()

    def _clear_crossplot_canvas(self, message: str) -> None:
        frame = getattr(self, "frame_fe_crossplot_canvas", None)
        if frame is None:
            return
        layout = frame.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(frame)
            layout.setContentsMargins(12, 12, 12, 12)

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        label = QtWidgets.QLabel(message, frame)
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setStyleSheet("color:#7B8FA6;font-size:13px;border:1px dashed #C8D7E8;border-radius:8px;background:#FFFFFF;padding:18px;")
        layout.addWidget(label)

    def _mark_project_modified(self) -> None:
        project_service = getattr(self.ui, "_project_service", None)
        if project_service is not None and hasattr(project_service, "mark_modified"):
            project_service.mark_modified()
        if self.data is not None:
            self.data._refresh_views()

    def _render_figure(self, frame_name: str, placeholder_name: str, fig) -> None:
        try:
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas  # type: ignore
        except Exception:
            return

        host = self._ensure_plot_host(frame_name, placeholder_name)
        if host is None or host.layout() is None:
            return

        while host.layout().count():
            item = host.layout().takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        canvas = FigureCanvas(fig)
        canvas.setStyleSheet("background:#FFFFFF;border:0;")
        host.layout().addWidget(canvas)
        canvas.draw_idle()

    def _ensure_plot_host(self, frame_name: str, placeholder_name: str) -> QtWidgets.QWidget | None:
        frame = getattr(self.ui, frame_name, None)
        if frame is None or frame.layout() is None:
            return None

        placeholder = getattr(self.ui, placeholder_name, None)
        if placeholder is not None:
            placeholder.hide()

        host = self._plot_hosts.get(frame_name)
        if host is None:
            host = QtWidgets.QWidget(frame)
            host_layout = QtWidgets.QVBoxLayout(host)
            host_layout.setContentsMargins(0, 0, 0, 0)
            host_layout.setSpacing(0)
            frame.layout().addWidget(host, 1)
            self._plot_hosts[frame_name] = host
        host.show()
        return host

    def _show_placeholders(self) -> None:
        for frame_name, placeholder_name in (
            ("frameFEGammaTrack", "lblFEGammaPlaceholder"),
            ("frameFEVshTrack", "lblFEVshPlaceholder"),
            ("frameFEPorosityTrack", "lblFEPorosityPlaceholder"),
            ("frameFESwTrack", "lblFESwPlaceholder"),
            ("frameFEPayChart", "lblFEPayChartPlaceholder"),
        ):
            placeholder = getattr(self.ui, placeholder_name, None)
            if placeholder is not None:
                placeholder.show()
            host = self._plot_hosts.get(frame_name)
            if host is None or host.layout() is None:
                continue
            while host.layout().count():
                item = host.layout().takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()
            host.hide()

    @staticmethod
    def _depth_series(df) -> tuple[str, pd.Series]:
        if "DEPTH" in df.columns:
            return "DEPTH", pd.to_numeric(df["DEPTH"], errors="coerce")
        if "DEPT" in df.columns:
            return "DEPT", pd.to_numeric(df["DEPT"], errors="coerce")
        depth_label = getattr(df.index, "name", None) or "Depth"
        return depth_label, pd.Series(pd.to_numeric(df.index, errors="coerce"), index=df.index)

    @staticmethod
    def _first_available_curve(df, names: tuple[str, ...]) -> str | None:
        columns_upper = {str(column).upper(): str(column) for column in df.columns}
        for name in names:
            if name.upper() in columns_upper:
                return columns_upper[name.upper()]
        return None

    @staticmethod
    def _value_bounds(series: pd.Series) -> tuple[float, float]:
        finite = series.replace([np.inf, -np.inf], np.nan).dropna()
        if finite.empty:
            return 0.0, 1.0
        low = float(finite.min())
        high = float(finite.max())
        if math.isclose(low, high):
            pad = 1.0 if high == 0 else abs(high) * 0.1
            return low - pad, high + pad
        return low, high

    @staticmethod
    def _depth_step(depth: pd.Series) -> float:
        diffs = depth.diff().abs().replace(0, np.nan).dropna()
        if diffs.empty:
            return 0.0
        return float(diffs.median())

    def _spin_value(self, name: str, default=None):
        widget = getattr(self.ui, name, None)
        if widget is None:
            return default
        getter = getattr(widget, "value", None)
        if callable(getter):
            return getter()
        return default

    def _combo_text(self, name: str, default: str = "") -> str:
        widget = getattr(self.ui, name, None)
        if widget is None:
            return default
        getter = getattr(widget, "currentText", None)
        if callable(getter):
            text = str(getter()).strip()
            return text or default
        return default

    def _is_checked(self, name: str, default: bool = True) -> bool:
        widget = getattr(self.ui, name, None)
        if widget is None:
            return default
        getter = getattr(widget, "isChecked", None)
        if callable(getter):
            return bool(getter())
        return default

    def _depth_mask(self, depth_series: pd.Series, well) -> pd.Series:
        mask = pd.Series(True, index=depth_series.index)
        depth_controls = depth_series.copy()

        selected_unit = self._combo_text("comboFEDepthUnit", "m").lower()
        data_unit = self._infer_depth_unit(well)
        if selected_unit.startswith("ft") and data_unit.startswith("m"):
            depth_controls = depth_series * 3.28084
        elif selected_unit.startswith("m") and data_unit.startswith("ft"):
            depth_controls = depth_series / 3.28084

        preset = self._combo_text("comboFEDepthPreset", "Custom").lower()
        start_depth = self._spin_value("spinFEFrom")
        end_depth = self._spin_value("spinFETo")

        if "full" in preset:
            start_depth = None
            end_depth = None
        elif "reservoir" in preset:
            finite = depth_controls.dropna()
            if not finite.empty:
                start_depth = float(finite.quantile(0.25))
                end_depth = float(finite.quantile(0.75))
                for name, value in (("spinFEFrom", start_depth), ("spinFETo", end_depth)):
                    spin = getattr(self.ui, name, None)
                    if spin is not None:
                        spin.blockSignals(True)
                        spin.setValue(value)
                        spin.blockSignals(False)

        if start_depth not in (None, 0):
            mask &= depth_controls >= float(start_depth)
        if end_depth not in (None, 0):
            mask &= depth_controls <= float(end_depth)
        return mask

    @staticmethod
    def _infer_depth_unit(well) -> str:
        header = getattr(well, "header", {}) or {}
        well_header = header.get("WELL", {}) if isinstance(header, dict) else {}
        if not isinstance(well_header, dict):
            return "m"
        for key in ("STRT", "STOP", "STEP", "DEPT", "DEPTH"):
            value = well_header.get(key)
            if not isinstance(value, dict):
                continue
            unit = str(value.get("unit", "")).strip().lower()
            if "ft" in unit:
                return "ft"
            if unit in {"m", "meter", "meters", "metre", "metres"}:
                return "m"
        return "m"

    def _set_label(self, name: str, value: str) -> None:
        label = getattr(self.ui, name, None)
        if label is not None:
            label.setText(value)

    @staticmethod
    def _fmt_number(value, decimals: int) -> str:
        try:
            return f"{float(value):.{decimals}f}"
        except Exception:
            return "--"
