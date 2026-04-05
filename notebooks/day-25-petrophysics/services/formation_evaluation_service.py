"""Formation evaluation workspace helpers."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from PyQt5 import QtWidgets

from calculations import net_pay, permeability, porosity, saturation, vshale


class FormationEvaluationService:
    def __init__(self, ui: QtWidgets.QMainWindow, data_service=None):
        self.ui = ui
        self.data = data_service
        self._plot_hosts: dict[str, QtWidgets.QWidget] = {}
        tab_views = getattr(self.ui, "tabFEViews", None)
        if tab_views is not None:
            tab_views.setCurrentIndex(0)

    def run_evaluation(self, *_args):
        result = self._build_result()
        if result is None:
            self.reset_evaluation()
            return

        self._update_summary(result)
        self._fill_pay_table(result)
        self._render_tracks(result)
        self._update_secondary_placeholders(result)

    def reset_evaluation(self):
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

        if use_vsh:
            vsh = pd.Series(
                vshale.compute_vsh_gr(
                    gr.to_numpy(dtype=float),
                    gr_min=gr_min,
                    gr_max=gr_max,
                    model=vsh_model,
                ),
                index=df.index,
            )
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
                "VSH": vsh,
                "PHI": phi,
                "SW": sw,
                "PERM": perm,
                "NET_PAY": pay_flag,
            }
        )
        result = result.loc[visible_mask].copy()
        result = result.replace([np.inf, -np.inf], np.nan).dropna(subset=["depth"])
        if result.empty:
            return None

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
