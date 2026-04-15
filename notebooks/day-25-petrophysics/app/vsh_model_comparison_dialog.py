from __future__ import annotations

from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets, uic

from calculations import vshale

UI_PATH = Path(__file__).resolve().parent.parent / "ui" / "vsh_model_comparison.ui"

class VshModelComparisonDialog(QtWidgets.QDialog):
    MODEL_SPECS = (
        {"label": "Linear", "model": "linear", "color": "#2DD4BF"},
        {"label": "Larionov Tertiary", "model": "larionov tertiary", "color": "#2563EB"},
        {"label": "Larionov Older", "model": "larionov older", "color": "#7C3AED"},
        {"label": "Clavier", "model": "clavier", "color": "#1F2937"},
        {"label": "Steiber", "model": "steiber", "color": "#F59E0B"},
    )

    def __init__(self, parent: QtWidgets.QWidget | None, data_service):
        super().__init__(parent)
        uic.loadUi(str(UI_PATH), self)
        
        self.data_service = data_service
        self._well = None
        self._full_df = None
        self._visible_df = None
        self._gr_curve = "GR"
        self._latest_payload = None

        self._model_checks: dict[str, QtWidgets.QCheckBox] = {
            "Linear": self.chkLinear,
            "Larionov Tertiary": self.chkLarionovTertiary,
            "Larionov Older": self.chkLarionovOlder,
            "Clavier": self.chkClavier,
            "Steiber": self.chkSteiber,
        }

        self.btnSelectAll.clicked.connect(self._select_all_models)
        self.btnGenerate.clicked.connect(self.generate_comparison)
        self.btnExport.clicked.connect(self._export_figure)
        self.btnClose.clicked.connect(self.accept)

        self._show_placeholder(self._theory_host, "Theoretical Model Curves", "Click Generate Comparison to compare model responses.")
        self._show_placeholder(self._well_host, "Well Log Comparison", "Well-based comparison will appear here once a comparison is generated.")
        self._update_legend([])

    def set_context(self, well, gr_curve: str, gr_clean: float, gr_shale: float) -> None:
        self._well = well
        self._full_df = getattr(well, "data", None) if well is not None else None
        self._visible_df = self.data_service._filtered_dataframe(well) if well is not None else None
        if self._visible_df is None or getattr(self._visible_df, "empty", True):
            self._visible_df = self._full_df
        self._gr_curve = gr_curve or "GR"

        well_name = getattr(well, "name", "Unknown Well")
        if hasattr(self, 'lblWellValue'):
            self.lblWellValue.setText(well_name)
        if hasattr(self, 'lblCurveValue'):
            self.lblCurveValue.setText(self._gr_curve)
        self.spinGrClean.setValue(float(gr_clean))
        self.spinGrShale.setValue(float(gr_shale))
        self._set_status("Ready - comparison initialized.", "#E8F7EE", "#2F855A")
        self.generate_comparison()

    def generate_comparison(self) -> None:
        payload = self._build_payload()
        self._latest_payload = payload
        if not payload or payload.get("error"):
            message = payload.get("error", "Unable to prepare comparison.") if payload else "Unable to prepare comparison."
            self._show_placeholder(self._theory_host, "Theoretical Model Curves", message)
            self._show_placeholder(self._well_host, "Well Log Comparison", message)
            self._update_legend([])
            self._set_insight_label(self.lblModelsValue, "0")
            self._set_insight_label(self.lblSamplesValue, "--")
            self._set_insight_label(self.lblSpreadValue, "--")
            self._set_insight_label(self.lblWindowValue, "--")
            self.txtInsight.setText("Comparison is unavailable until a valid well, GR curve, and model set are provided.")
            self._set_status(message, "#FFF4E5", "#C27803")
            return

        self._render_figure(self._theory_host, self._create_theoretical_figure(payload))
        self._render_figure(self._well_host, self._create_well_figure(payload))
        self._update_legend(payload["models"])
        self._update_insights(payload)
        self._set_status("Ready - comparison generated.", "#E8F7EE", "#2F855A")

    def _set_insight_label(self, widget: QtWidgets.QLabel, text: str) -> None:
        widget.setText(text)

    def _select_all_models(self) -> None:
        for checkbox in self._model_checks.values():
            checkbox.setChecked(True)

    def _selected_models(self) -> list[dict]:
        return [spec for spec in self.MODEL_SPECS if self._model_checks[spec["label"]].isChecked()]

    def _build_payload(self):
        import numpy as np
        import pandas as pd

        if self._well is None or self._full_df is None:
            return {"error": "Load a well before opening the Vsh model comparison dialog."}

        if self.spinGrShale.value() <= self.spinGrClean.value():
            return {"error": "GR Shale must be greater than GR Clean to compare Vsh models."}

        selected_models = self._selected_models()
        if not selected_models:
            return {"error": "Select at least one Vsh model to generate the comparison."}

        df = self._visible_df if self._visible_df is not None and not getattr(self._visible_df, "empty", True) else self._full_df
        if df is None or getattr(df, "empty", True):
            return {"error": "No well data is available for comparison."}

        if self._gr_curve not in df.columns:
            return {"error": f"GR curve '{self._gr_curve}' is not available in the current well."}

        depth_col = self.data_service._depth_column(df)
        if depth_col is not None and depth_col in df.columns:
            depth = pd.to_numeric(df[depth_col], errors="coerce").to_numpy(dtype=float)
            depth_label = str(depth_col)
        else:
            depth = np.arange(len(df), dtype=float)
            depth_label = "Index"

        gr = pd.to_numeric(df[self._gr_curve], errors="coerce").to_numpy(dtype=float)
        model_results = []
        mask = np.isfinite(depth) & np.isfinite(gr)
        gr_clean = float(self.spinGrClean.value())
        gr_shale = float(self.spinGrShale.value())

        for spec in selected_models:
            values = vshale.compute_vsh_gr(gr, gr_min=gr_clean, gr_max=gr_shale, model=spec["model"])
            model_results.append({**spec, "values": values})
            mask &= np.isfinite(values)

        if not np.any(mask):
            return {"error": "The current interval does not contain enough valid GR samples for model comparison."}

        depth = depth[mask]
        gr = gr[mask]
        for item in model_results:
            item["values"] = item["values"][mask]

        vsh_stack = np.vstack([item["values"] for item in model_results])
        theoretical_gr = np.linspace(gr_clean, gr_shale, 240)
        theoretical_curves = []
        for item in model_results:
            theoretical_curves.append(
                {
                    "label": item["label"],
                    "color": item["color"],
                    "values": vshale.compute_vsh_gr(
                        theoretical_gr,
                        gr_min=gr_clean,
                        gr_max=gr_shale,
                        model=item["model"],
                    ),
                }
            )

        model_means = {item["label"]: float(np.nanmean(item["values"])) for item in model_results}
        dominant_model = max(model_means.items(), key=lambda entry: entry[1])[0]
        spread = float(np.nanmean(np.nanmax(vsh_stack, axis=0) - np.nanmin(vsh_stack, axis=0)))
        depth_low = float(np.nanmin(depth))
        depth_high = float(np.nanmax(depth))

        return {
            "well_name": getattr(self._well, "name", "Well"),
            "gr_curve": self._gr_curve,
            "gr_clean": gr_clean,
            "gr_shale": gr_shale,
            "depth_label": depth_label,
            "depth": depth,
            "depth_low": depth_low,
            "depth_high": depth_high,
            "gr": gr,
            "models": model_results,
            "theoretical_gr": theoretical_gr,
            "theoretical_curves": theoretical_curves,
            "sample_count": int(mask.sum()),
            "spread": spread,
            "dominant_model": dominant_model,
        }

    def _create_theoretical_figure(self, payload):
        from matplotlib.figure import Figure

        fig = Figure(figsize=(7.2, 6.0), dpi=100, constrained_layout=True)
        ax = fig.add_subplot(1, 1, 1)

        ax.set_facecolor("#FFFFFF")
        for item in payload["theoretical_curves"]:
            ax.plot(payload["theoretical_gr"], item["values"], color=item["color"], linewidth=2.1, label=item["label"])

        ax.axvline(payload["gr_clean"], color="#FB923C", linestyle="--", linewidth=1.3)
        ax.axvline(payload["gr_shale"], color="#EF4444", linestyle="--", linewidth=1.3)
        ax.text(payload["gr_clean"], 1.02, f"Sand Line\n{payload['gr_clean']:.2f} API", color="#FB923C", fontsize=8, ha="center")
        ax.text(payload["gr_shale"], 1.02, f"Shale Line\n{payload['gr_shale']:.2f} API", color="#EF4444", fontsize=8, ha="center")
        ax.set_ylim(0.0, 1.06)
        margin = max(10.0, (payload["gr_shale"] - payload["gr_clean"]) * 0.12)
        ax.set_xlim(payload["gr_clean"] - margin, payload["gr_shale"] + margin)
        ax.set_title("Vsh vs Gamma Ray - Model Comparison", fontsize=11, color="#1F3653")
        ax.set_xlabel("Gamma Ray (API)", fontsize=9)
        ax.set_ylabel("Vsh (Fraction)", fontsize=9)
        ax.grid(True, linestyle="--", alpha=0.2)
        ax.tick_params(axis="both", labelsize=8)
        ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.18), ncol=3, fontsize=8, frameon=False)
        fig.patch.set_facecolor("white")
        return fig

    def _create_well_figure(self, payload):
        from matplotlib.figure import Figure

        fig = Figure(figsize=(9.4, 6.0), dpi=100, constrained_layout=True)
        ax_gr, ax_vsh = fig.subplots(1, 2, sharey=True, gridspec_kw={"width_ratios": [1.0, 1.35]})

        ax_gr.plot(payload["gr"], payload["depth"], color="#2EB67D", linewidth=1.0)
        ax_gr.axvline(payload["gr_clean"], color="#FB923C", linestyle="--", linewidth=1.1)
        ax_gr.axvline(payload["gr_shale"], color="#EF4444", linestyle="--", linewidth=1.1)
        ax_gr.set_title("GR (API)", fontsize=10, color="#1F3653")
        ax_gr.set_xlabel("GR (API)", fontsize=9)
        ax_gr.set_ylabel(payload["depth_label"], fontsize=9)
        ax_gr.xaxis.set_label_position("top")
        ax_gr.xaxis.tick_top()
        ax_gr.grid(True, linestyle="--", alpha=0.16)
        ax_gr.tick_params(axis="both", labelsize=8)

        ax_vsh.axvspan(0.0, 0.5, color="#E7F7EE", alpha=0.95)
        ax_vsh.axvspan(0.5, 1.0, color="#FCE8E8", alpha=0.95)
        for item in payload["models"]:
            ax_vsh.plot(item["values"], payload["depth"], color=item["color"], linewidth=1.15)
        ax_vsh.set_xlim(0.0, 1.0)
        ax_vsh.set_title("Vsh - All Models", fontsize=10, color="#1F3653")
        ax_vsh.set_xlabel("Vsh", fontsize=9)
        ax_vsh.xaxis.set_label_position("top")
        ax_vsh.xaxis.tick_top()
        ax_vsh.grid(True, linestyle="--", alpha=0.16)
        ax_vsh.tick_params(axis="both", labelsize=8)

        ax_gr.set_ylim(payload["depth_high"], payload["depth_low"])
        fig.patch.set_facecolor("white")
        return fig

    def _render_figure(self, host, fig) -> None:
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

        layout = host.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(host)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
        self._clear_layout(layout)
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas, 1)
        canvas.draw_idle()

    def _show_placeholder(self, host, title: str, message: str) -> None:
        layout = host.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(host)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
        self._clear_layout(layout)
        label = QtWidgets.QLabel(f"{title}\n\n{message}", host)
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet(
            "background:#F8FBFE;border:1px dashed #C9D7E6;border-radius:10px;padding:20px;color:#6C7E90;font-size:12px;"
        )
        layout.addWidget(label, 1)

    def _update_legend(self, models: list[dict]) -> None:
        if self._legend_layout is None:
            return
        self._clear_layout(self._legend_layout)
        if not models:
            empty = QtWidgets.QLabel("No models selected.", self)
            empty.setStyleSheet("font-size:11px;color:#6C7E90;")
            self._legend_layout.addWidget(empty)
            self._legend_layout.addStretch(1)
            return

        for item in models:
            row = QtWidgets.QHBoxLayout()
            swatch = QtWidgets.QLabel(self)
            swatch.setFixedSize(14, 14)
            swatch.setStyleSheet(f"background:{item['color']};border-radius:7px;")
            text = QtWidgets.QLabel(item["label"], self)
            text.setStyleSheet("font-size:11px;color:#42566C;font-weight:700;")
            row.addWidget(swatch)
            row.addWidget(text)
            row.addStretch(1)
            self._legend_layout.addLayout(row)
        self._legend_layout.addStretch(1)

    def _update_insights(self, payload) -> None:
        self._set_insight_label(self.lblCleanValue, f"{payload['gr_clean']:.2f} API")
        self._set_insight_label(self.lblShaleValue, f"{payload['gr_shale']:.2f} API")
        self._set_insight_label(self.lblModelsValue, str(len(payload["models"])))
        self._set_insight_label(self.lblSamplesValue, f"{payload['sample_count']:,}")
        self._set_insight_label(self.lblSpreadValue, f"{payload['spread']:.3f}")
        self._set_insight_label(self.lblWindowValue, f"{payload['depth_low']:.0f} - {payload['depth_high']:.0f}")
        self.lblDepthBadge.setText(f"Depth: {payload['depth_low']:.0f} - {payload['depth_high']:.0f}")

        if payload["spread"] >= 0.14:
            sensitivity = "high"
            risk_note = "Model selection can materially impact pay interpretation."
        elif payload["spread"] >= 0.08:
            sensitivity = "moderate"
            risk_note = "Model choice matters in several intervals."
        else:
            sensitivity = "low"
            risk_note = "Most models are tracking closely over this interval."

        self.txtInsight.setText(
            f"{payload['dominant_model']} gives the highest average Vsh across the selected interval. "
            f"Overall model sensitivity is {sensitivity}; {risk_note}"
        )

    def _set_status(self, text: str, background: str, foreground: str) -> None:
        self.lblStatusBadge.setText(text)
        self.lblStatusBadge.setStyleSheet(
            f"background:{background};color:{foreground};border:1px solid #D7E2EE;border-radius:16px;padding:8px 12px;font-weight:700;"
        )

    def _export_figure(self) -> None:
        if not self._latest_payload or self._latest_payload.get("error"):
            QtWidgets.QMessageBox.information(self, "Export Figure", "Generate a comparison before exporting a figure.")
            return

        well_name = str(getattr(self._well, "name", "well")).replace(" ", "_")
        default_path = Path.home() / f"{well_name}_vsh_model_comparison.png"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export Vsh Comparison",
            str(default_path),
            "PNG Image (*.png);;PDF Document (*.pdf);;SVG Vector (*.svg)",
        )
        if not path:
            return

        from matplotlib.figure import Figure

        fig = Figure(figsize=(15.5, 7.6), dpi=150, constrained_layout=True)
        subfig_left, subfig_right = fig.subfigures(1, 2, wspace=0.04)

        ax_left = subfig_left.subplots(1, 1)
        ax_right_gr, ax_right_vsh = subfig_right.subplots(1, 2, sharey=True, gridspec_kw={"width_ratios": [1.0, 1.35]})
        self._draw_export_theoretical(ax_left, self._latest_payload)
        self._draw_export_well(ax_right_gr, ax_right_vsh, self._latest_payload)
        fig.suptitle(
            f"Vsh Model Comparison - {self._latest_payload['well_name']} ({self._latest_payload['gr_curve']})",
            fontsize=14,
            color="#1F3653",
            fontweight="bold",
        )
        fig.savefig(path, bbox_inches="tight")
        QtWidgets.QMessageBox.information(self, "Export Figure", f"Figure exported successfully:\n{path}")

    def _draw_export_theoretical(self, ax, payload) -> None:
        ax.set_facecolor("#FFFFFF")
        for item in payload["theoretical_curves"]:
            ax.plot(payload["theoretical_gr"], item["values"], color=item["color"], linewidth=2.1, label=item["label"])
        ax.axvline(payload["gr_clean"], color="#FB923C", linestyle="--", linewidth=1.3)
        ax.axvline(payload["gr_shale"], color="#EF4444", linestyle="--", linewidth=1.3)
        margin = max(10.0, (payload["gr_shale"] - payload["gr_clean"]) * 0.12)
        ax.set_xlim(payload["gr_clean"] - margin, payload["gr_shale"] + margin)
        ax.set_ylim(0.0, 1.04)
        ax.set_title("Theoretical Model Curves", fontsize=11, color="#1F3653")
        ax.set_xlabel("Gamma Ray (API)", fontsize=9)
        ax.set_ylabel("Vsh (Fraction)", fontsize=9)
        ax.grid(True, linestyle="--", alpha=0.2)
        ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.18), ncol=3, fontsize=8, frameon=False)

    def _draw_export_well(self, ax_gr, ax_vsh, payload) -> None:
        ax_gr.plot(payload["gr"], payload["depth"], color="#2EB67D", linewidth=1.0)
        ax_gr.axvline(payload["gr_clean"], color="#FB923C", linestyle="--", linewidth=1.1)
        ax_gr.axvline(payload["gr_shale"], color="#EF4444", linestyle="--", linewidth=1.1)
        ax_gr.set_title("Gamma Ray", fontsize=11, color="#1F3653")
        ax_gr.set_xlabel("GR (API)", fontsize=9)
        ax_gr.set_ylabel(payload["depth_label"], fontsize=9)
        ax_gr.xaxis.set_label_position("top")
        ax_gr.xaxis.tick_top()
        ax_gr.grid(True, linestyle="--", alpha=0.16)

        ax_vsh.axvspan(0.0, 0.5, color="#E7F7EE", alpha=0.95)
        ax_vsh.axvspan(0.5, 1.0, color="#FCE8E8", alpha=0.95)
        for item in payload["models"]:
            ax_vsh.plot(item["values"], payload["depth"], color=item["color"], linewidth=1.15, label=item["label"])
        ax_vsh.set_xlim(0.0, 1.0)
        ax_vsh.set_title("Vsh - All Models", fontsize=11, color="#1F3653")
        ax_vsh.set_xlabel("Vsh", fontsize=9)
        ax_vsh.xaxis.set_label_position("top")
        ax_vsh.xaxis.tick_top()
        ax_vsh.grid(True, linestyle="--", alpha=0.16)
        ax_gr.set_ylim(payload["depth_high"], payload["depth_low"])
        ax_vsh.legend(loc="lower center", bbox_to_anchor=(0.5, -0.18), ncol=3, fontsize=8, frameon=False)

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)
