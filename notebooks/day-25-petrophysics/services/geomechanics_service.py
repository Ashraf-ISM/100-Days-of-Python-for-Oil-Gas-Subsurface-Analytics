"""Geomechanics workflow: compute, visualize, and interpret rock mechanics logs."""
from __future__ import annotations

import numpy as np
from PyQt5 import QtCore, QtWidgets


class GeomechanicsService:
    def __init__(self, ui: QtWidgets.QMainWindow, data_service):
        self.ui = ui
        self.data = data_service
        self._geo_plot_host = None
        self._geo_summary_labels: dict[str, QtWidgets.QLabel] = {}
        self._build_geo_workspace()

    def run_geomechanics(self):
        well = self.data._get_current_well()
        if not well:
            return
        df = getattr(well, "data", None)
        if df is None:
            return

        dt_curve = self._combo_text("comboGeoDT") or "DT"
        dts_curve = self._combo_text("comboGeoDTS") or "DTS"
        rhob_curve = self._combo_text("comboGeoRHOB") or "RHOB"

        missing = [c for c in (dt_curve, dts_curve, rhob_curve) if c not in df.columns]
        if missing:
            QtWidgets.QMessageBox.warning(
                self.ui,
                "Geomechanics",
                f"Required curves missing: {', '.join(missing)}",
            )
            return

        calib = self._spin_value(("spinGeoCalib",), 1.0) or 1.0
        dt = np.asarray(df[dt_curve].values, dtype=float)
        dts = np.asarray(df[dts_curve].values, dtype=float)
        rhob = np.asarray(df[rhob_curve].values, dtype=float)

        # Unit assumptions: DT/DTS in us/ft, RHOB in g/cc.
        vp = 0.3048e6 / np.clip(dt, 1e-6, None)
        vs = 0.3048e6 / np.clip(dts, 1e-6, None)
        rho = np.clip(rhob, 0.5, None) * 1000.0

        denom = np.clip((vp ** 2 - vs ** 2), 1e-9, None)
        young_pa = rho * (vs ** 2) * ((3.0 * vp ** 2) - (4.0 * vs ** 2)) / denom
        young_gpa = np.clip(young_pa / 1e9, 0.0, None) * calib

        nu = (vp ** 2 - 2.0 * vs ** 2) / (2.0 * denom)
        nu = np.clip(nu, 0.0, 0.49)

        vp_kms = vp / 1000.0
        ucs = 0.77 * np.power(np.clip(vp_kms * 1000.0, 1e-6, None), 1.93)
        ucs = np.clip(ucs * calib, 0.0, None)

        bi = self._compute_brittleness(young_gpa, nu)

        if self._is_checked("checkGeoE", default=True):
            df["E"] = young_gpa
        if self._is_checked("checkGeoPR", default=True):
            df["NU"] = nu
        if self._is_checked("checkGeoUCS", default=True):
            df["UCS"] = ucs
        if self._is_checked("checkGeoBI", default=True):
            df["BI"] = bi

        depth_col = self.data._depth_column(df)
        if depth_col is None:
            depth = np.arange(len(df), dtype=float)
            depth_label = "Sample"
        else:
            depth = np.asarray(df[depth_col].values, dtype=float)
            depth_label = depth_col

        selected_tracks = self._selected_tracks(df)
        self._plot_geomech(depth, depth_label, selected_tracks)
        self._update_summary(young_gpa, nu, bi)
        self._update_interpretation(bi)

        self.data._refresh_views()

    def export_geomech_csv(self):
        well = self.data._get_current_well()
        if well is None:
            return
        df = getattr(well, "data", None)
        if df is None:
            return

        required = ["E", "NU", "UCS", "BI"]
        available = [c for c in required if c in df.columns]
        if not available:
            QtWidgets.QMessageBox.information(self.ui, "Geomechanics", "Run geomechanics first.")
            return

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.ui,
            "Export Geomechanics CSV",
            f"{getattr(well, 'name', 'well')}_geomechanics.csv",
            "CSV Files (*.csv)",
        )
        if not path:
            return

        cols = [self.data._depth_column(df)] if self.data._depth_column(df) else []
        cols.extend(available)
        export_df = df[[c for c in cols if c in df.columns]].copy()
        export_df.to_csv(path, index=False)
        QtWidgets.QMessageBox.information(self.ui, "Geomechanics", f"Exported to:\n{path}")

    def send_to_crossplot(self):
        tab_widget = getattr(self.ui, "centralTabWidget", None)
        target = getattr(self.ui, "tabWellPlots", None)
        if tab_widget is not None and target is not None:
            idx = tab_widget.indexOf(target)
            if idx >= 0:
                tab_widget.setCurrentIndex(idx)

    def _build_geo_workspace(self) -> None:
        tab = getattr(self.ui, "tabGeomechanics", None)
        if tab is None or getattr(self.ui, "_geo_workspace_built", False):
            return

        existing_layout = tab.layout()
        if existing_layout is None:
            existing_layout = QtWidgets.QVBoxLayout(tab)

        keep_names = {
            "groupGeoParams",
            "comboGeoWell",
            "comboGeoDT",
            "comboGeoDTS",
            "comboGeoRHOB",
            "checkGeoUCS",
            "checkGeoE",
            "checkGeoPR",
            "checkGeoBI",
            "frameGeoCanvas",
        }
        preserved = {}
        while existing_layout.count():
            item = existing_layout.takeAt(0)
            widget = item.widget()
            if widget is None:
                continue
            name = widget.objectName()
            if name in keep_names:
                widget.setParent(None)
                preserved[name] = widget
            else:
                widget.setParent(None)
                widget.deleteLater()

        if isinstance(existing_layout, QtWidgets.QVBoxLayout):
            main_layout = existing_layout
        else:
            container = QtWidgets.QWidget(tab)
            main_layout = QtWidgets.QVBoxLayout(container)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(8)
            existing_layout.addWidget(container)

        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        top_split = QtWidgets.QHBoxLayout()
        top_split.setSpacing(8)

        params_group = preserved.get("groupGeoParams")
        if params_group is None:
            params_group = QtWidgets.QGroupBox("Rock Mechanical Parameters", tab)
            params_group.setLayout(QtWidgets.QFormLayout())

        form = params_group.layout()
        if not isinstance(form, QtWidgets.QFormLayout):
            new_form = QtWidgets.QFormLayout(params_group)
            params_group.setLayout(new_form)
            form = new_form

        self._ensure_geo_param_row(form, "DT Unit:", "lblGeoDTUnit", "us/ft")
        self._ensure_geo_param_row(form, "DTS Unit:", "lblGeoDTSUnit", "us/ft")
        self._ensure_geo_param_row(form, "RHOB Unit:", "lblGeoRHOBUnit", "g/cc")
        self._ensure_geo_spin_row(form, "Matrix Density:", "spinGeoMatrix", 2.65, 1.0, 4.0, " g/cc")
        self._ensure_geo_spin_row(form, "Fluid Density:", "spinGeoFluid", 1.00, 0.1, 2.0, " g/cc")
        self._ensure_geo_spin_row(form, "Calibration:", "spinGeoCalib", 1.00, 0.5, 2.0, "")

        run_btn = getattr(self.ui, "runGeoBtn", None)
        if run_btn is None:
            run_btn = QtWidgets.QPushButton("Run Geomechanics", params_group)
            run_btn.setObjectName("runGeoBtn")
            run_btn.setStyleSheet("background:#2B6CB0;color:#FFFFFF;font-weight:700;")
            form.addRow(run_btn)
            self.ui.runGeoBtn = run_btn

        export_btn = getattr(self.ui, "btnGeoExport", None)
        if export_btn is None:
            export_btn = QtWidgets.QPushButton("Export Geomech CSV", params_group)
            export_btn.setObjectName("btnGeoExport")
            form.addRow(export_btn)
            self.ui.btnGeoExport = export_btn

        send_btn = getattr(self.ui, "btnGeoSendCrossplot", None)
        if send_btn is None:
            send_btn = QtWidgets.QPushButton("Send To Crossplot", params_group)
            send_btn.setObjectName("btnGeoSendCrossplot")
            form.addRow(send_btn)
            self.ui.btnGeoSendCrossplot = send_btn

        top_split.addWidget(params_group, 1)

        canvas_frame = preserved.get("frameGeoCanvas")
        if canvas_frame is None:
            canvas_frame = QtWidgets.QFrame(tab)
            canvas_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
            canvas_frame.setLayout(QtWidgets.QVBoxLayout())

        canvas_layout = canvas_frame.layout()
        if canvas_layout is None:
            canvas_layout = QtWidgets.QVBoxLayout(canvas_frame)

        # Remove placeholder widgets and create plotting host.
        while canvas_layout.count():
            item = canvas_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        self._geo_plot_host = QtWidgets.QWidget(canvas_frame)
        self._geo_plot_host.setLayout(QtWidgets.QVBoxLayout())
        self._geo_plot_host.layout().setContentsMargins(0, 0, 0, 0)
        canvas_layout.addWidget(self._geo_plot_host)
        top_split.addWidget(canvas_frame, 3)

        main_layout.addLayout(top_split, 3)

        summary_frame = QtWidgets.QFrame(tab)
        summary_frame.setStyleSheet("QFrame { background:#F8FBFE; border:1px solid #D7E2EE; border-radius:10px; }")
        summary_layout = QtWidgets.QHBoxLayout(summary_frame)
        summary_layout.setContentsMargins(10, 8, 10, 8)
        summary_layout.setSpacing(10)

        for title, key in (
            ("Avg Young's Modulus (GPa)", "e_avg"),
            ("Avg Poisson's Ratio", "nu_avg"),
            ("Avg Brittleness", "bi_avg"),
            ("Formation Class", "class"),
        ):
            card = QtWidgets.QFrame(summary_frame)
            card.setStyleSheet("QFrame { background:#FFFFFF; border:1px solid #D7E2EE; border-radius:8px; }")
            card_layout = QtWidgets.QVBoxLayout(card)
            card_layout.setContentsMargins(8, 6, 8, 6)
            lbl_t = QtWidgets.QLabel(title, card)
            lbl_t.setStyleSheet("font-size:10px;color:#5C718A;font-weight:600;")
            lbl_v = QtWidgets.QLabel("--", card)
            lbl_v.setStyleSheet("font-size:16px;color:#1F4E79;font-weight:800;")
            lbl_v.setAlignment(QtCore.Qt.AlignCenter)
            card_layout.addWidget(lbl_t)
            card_layout.addWidget(lbl_v)
            summary_layout.addWidget(card)
            self._geo_summary_labels[key] = lbl_v

        main_layout.addWidget(summary_frame)

        interp = getattr(self.ui, "geoInterpretationText", None)
        if interp is None:
            interp = QtWidgets.QTextEdit(tab)
            interp.setObjectName("geoInterpretationText")
            interp.setReadOnly(True)
            interp.setMinimumHeight(84)
            interp.setPlaceholderText("Geomechanics interpretation appears here after computation.")
            self.ui.geoInterpretationText = interp
        main_layout.addWidget(interp, 1)

        run_btn.clicked.connect(self.run_geomechanics)
        export_btn.clicked.connect(self.export_geomech_csv)
        send_btn.clicked.connect(self.send_to_crossplot)

        self.ui._geo_workspace_built = True

    def _ensure_geo_param_row(self, form: QtWidgets.QFormLayout, label_text: str, object_name: str, value_text: str) -> None:
        widget = getattr(self.ui, object_name, None)
        if widget is None:
            widget = QtWidgets.QLabel(value_text)
            widget.setObjectName(object_name)
            setattr(self.ui, object_name, widget)
            form.addRow(label_text, widget)

    def _ensure_geo_spin_row(
        self,
        form: QtWidgets.QFormLayout,
        label_text: str,
        object_name: str,
        default: float,
        minimum: float,
        maximum: float,
        suffix: str,
    ) -> None:
        spin = getattr(self.ui, object_name, None)
        if spin is None:
            spin = QtWidgets.QDoubleSpinBox()
            spin.setObjectName(object_name)
            spin.setDecimals(3)
            spin.setRange(minimum, maximum)
            spin.setValue(default)
            spin.setSuffix(suffix)
            setattr(self.ui, object_name, spin)
            form.addRow(label_text, spin)

    def _compute_brittleness(self, young_gpa: np.ndarray, nu: np.ndarray) -> np.ndarray:
        e_norm = self._minmax_norm(young_gpa)
        nu_norm = self._minmax_norm(nu)
        return np.clip((e_norm + (1.0 - nu_norm)) / 2.0, 0.0, 1.0)

    def _minmax_norm(self, values: np.ndarray) -> np.ndarray:
        arr = np.asarray(values, dtype=float)
        out = np.full(arr.shape, np.nan, dtype=float)
        finite_mask = np.isfinite(arr)
        if not np.any(finite_mask):
            return np.nan_to_num(out, nan=0.0)

        finite_vals = arr[finite_mask]
        vmin = float(np.min(finite_vals))
        vmax = float(np.max(finite_vals))
        span = vmax - vmin
        if span <= 1e-12:
            out[finite_mask] = 0.5
        else:
            out[finite_mask] = (finite_vals - vmin) / span
        return np.nan_to_num(out, nan=0.0)

    def _selected_tracks(self, df) -> list[tuple[str, str, np.ndarray]]:
        tracks: list[tuple[str, str, np.ndarray]] = []
        if self._is_checked("checkGeoE", default=True) and "E" in df.columns:
            tracks.append(("Young's Modulus", "E", np.asarray(df["E"].values, dtype=float)))
        if self._is_checked("checkGeoPR", default=True) and "NU" in df.columns:
            tracks.append(("Poisson's Ratio", "NU", np.asarray(df["NU"].values, dtype=float)))
        if self._is_checked("checkGeoUCS", default=True) and "UCS" in df.columns:
            tracks.append(("UCS", "UCS", np.asarray(df["UCS"].values, dtype=float)))
        if self._is_checked("checkGeoBI", default=True) and "BI" in df.columns:
            tracks.append(("Brittleness", "BI", np.asarray(df["BI"].values, dtype=float)))
        return tracks

    def _plot_geomech(self, depth: np.ndarray, depth_label: str, tracks: list[tuple[str, str, np.ndarray]]) -> None:
        if self._geo_plot_host is None or not tracks:
            return

        from matplotlib.figure import Figure

        mask = np.isfinite(depth)
        for _, _, values in tracks:
            mask &= np.isfinite(values)
        if not np.any(mask):
            return

        d = depth[mask]
        plot_tracks = [(title, name, values[mask]) for title, name, values in tracks]

        fig = Figure(figsize=(max(6.5, 2.8 * len(plot_tracks)), 8.6), dpi=100, constrained_layout=True)
        axes = fig.subplots(1, len(plot_tracks), sharey=True)
        if len(plot_tracks) == 1:
            axes = [axes]

        for idx, (ax, (title, name, values)) in enumerate(zip(axes, plot_tracks)):
            ax.plot(values, d, color="#1F4E79", linewidth=1.0)
            if name == "BI":
                ax.fill_betweenx(d, 0, values, where=(values > 0.6), color="red", alpha=0.3)
                ax.fill_betweenx(d, 0, values, where=((values >= 0.3) & (values <= 0.6)), color="gold", alpha=0.2)
                ax.fill_betweenx(d, 0, values, where=(values < 0.3), color="#3B82F6", alpha=0.2)
                ax.set_xlim(0.0, 1.0)
            ax.set_title(title, fontsize=10)
            ax.set_xlabel(name, fontsize=9)
            if idx == 0:
                ax.set_ylabel(depth_label, fontsize=9)
            ax.grid(True, linestyle="--", alpha=0.2)
            ax.set_ylim(np.nanmax(d), np.nanmin(d))

        self._render_figure_to_host(self._geo_plot_host, fig)

    def _update_summary(self, young_gpa: np.ndarray, nu: np.ndarray, bi: np.ndarray) -> None:
        e_avg = float(np.nanmean(young_gpa)) if np.isfinite(young_gpa).any() else 0.0
        nu_avg = float(np.nanmean(nu)) if np.isfinite(nu).any() else 0.0
        bi_avg = float(np.nanmean(bi)) if np.isfinite(bi).any() else 0.0

        if bi_avg > 0.6:
            klass = "Brittle Formation"
        elif bi_avg < 0.3:
            klass = "Ductile Formation"
        else:
            klass = "Moderate Brittleness"

        self._set_summary("e_avg", f"{e_avg:.2f}")
        self._set_summary("nu_avg", f"{nu_avg:.3f}")
        self._set_summary("bi_avg", f"{bi_avg:.3f}")
        self._set_summary("class", klass)

    def _update_interpretation(self, bi: np.ndarray) -> None:
        text_widget = getattr(self.ui, "geoInterpretationText", None)
        if text_widget is None:
            return

        bi_avg = float(np.nanmean(bi)) if np.isfinite(bi).any() else 0.0
        if bi_avg > 0.6:
            text = (
                "Formation is brittle and favorable for hydraulic fracturing. "
                "High BI zones should be prioritized for stimulation intervals."
            )
        elif bi_avg < 0.3:
            text = (
                "Formation is ductile and less favorable for fracture propagation. "
                "Consider alternative completion strategy or higher treatment energy."
            )
        else:
            text = (
                "Formation brittleness is moderate. "
                "Fracability is interval-dependent and should be optimized with stress data."
            )
        text_widget.setPlainText(text)

    def _set_summary(self, key: str, text: str) -> None:
        label = self._geo_summary_labels.get(key)
        if label is not None:
            label.setText(text)

    def _combo_text(self, name: str) -> str:
        combo = getattr(self.ui, name, None)
        if combo is None:
            return ""
        return combo.currentText().strip()

    def _spin_value(self, names: tuple[str, ...], default):
        for name in names:
            widget = getattr(self.ui, name, None)
            if widget is None:
                continue
            getter = getattr(widget, "value", None)
            if callable(getter):
                return getter()
        return default

    def _is_checked(self, name: str, default: bool = False) -> bool:
        widget = getattr(self.ui, name, None)
        if widget is None or not hasattr(widget, "isChecked"):
            return default
        return bool(widget.isChecked())

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
