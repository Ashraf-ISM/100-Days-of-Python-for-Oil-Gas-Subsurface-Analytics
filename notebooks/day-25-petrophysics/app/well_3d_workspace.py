from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PyQt5 import QtCore, QtWidgets

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent


@dataclass
class PickResult:
    well_name: str
    index: int
    md: float
    tvd: float
    x: float
    y: float
    values: dict[str, float | None]


class Well3DWorkspaceController(QtCore.QObject):
    def __init__(self, window: QtWidgets.QMainWindow, page: QtWidgets.QWidget):
        super().__init__(page)
        self.window = window
        self.page = page
        self.figure = None
        self.axes = None
        self.canvas = None
        self._plot_host = None
        self._event_ids: list[int] = []
        self._pick_points: dict[str, Any] = {}
        self._scene_cache: dict[str, pd.DataFrame] = {}
        self._selected_names: list[str] = []
        self._projection_label = "Perspective"
        self._signals_connected = False
        self._measure_anchor: PickResult | None = None
        self._animation_timer = QtCore.QTimer(self)
        self._animation_timer.timeout.connect(self._advance_animation)

        self._build_plot_host()
        self._configure_ui_defaults()
        self.connect_signals()
        self.refresh()

    def connect_signals(self) -> None:
        if self._signals_connected:
            return
        self._signals_connected = True

        self._connect_button("btnSelectAllWells", self._select_all_wells)
        self._connect_button("btnClearWells", self._clear_well_selection)
        self._connect_button("btnRenderUpdate", self.refresh)
        self._connect_button("btnResetView", self.reset_view)
        self._connect_button("btnFitAll", self.refresh)
        self._connect_button("btnClipPlane", self._toggle_clip_plane)
        self._connect_button("btnExport3D", self.export_view)
        self._connect_button("btnScreenshot", self.export_screenshot)
        self._connect_button("btnAnimPlay", self.start_animation)
        self._connect_button("btnAnimStop", self.stop_animation)

        self._connect_button("btnViewPerspective", lambda: self._apply_view_preset("perspective"))
        self._connect_button("btnViewTop", lambda: self._apply_view_preset("top"))
        self._connect_button("btnViewFront", lambda: self._apply_view_preset("front"))
        self._connect_button("btnViewSide", lambda: self._apply_view_preset("side"))
        self._connect_button("btnViewIso", lambda: self._apply_view_preset("iso"))

        list_wells = self._widget("listWells")
        if list_wells is not None:
            list_wells.itemSelectionChanged.connect(self._on_well_selection_changed)

        refresh_combo_names = (
            "cmbOverlayCurve",
            "cmbTrajStyle",
            "cmbTrajColorBy",
            "cmbCmapProperty",
            "cmbColormap",
            "cmbCrossSection",
            "cmbAnimSpeed",
        )
        for name in refresh_combo_names:
            self._connect_signal(name, "currentTextChanged", lambda _value, self=self: self.refresh())

        refresh_check_names = (
            "chkShowTrajectory",
            "chkShowDeviation",
            "chkShowWellHead",
            "chkShowTD",
            "chkShowLogRibbon",
            "chkShowFormationTops",
            "chkShowPerforations",
            "chkShowCasing",
            "chkShowFormationPlanes",
            "chkShowPayZones",
            "chkShowReferenceGrid",
            "chkShowAxes",
            "chkShowDepthScale",
            "chkShowCompass",
            "rdoBgDark",
            "rdoBgLight",
            "rdoBgGradient",
            "chkShowWellNames",
            "chkShowDepthLabels",
            "chkShowFormationLabels",
            "chkShowValueLabels",
            "chkInvertCmap",
            "chkLogScale",
            "chkShowColorbar",
            "chkShadows",
            "chkSSAO",
        )
        for name in refresh_check_names:
            self._connect_signal(name, "toggled", lambda _checked, self=self: self.refresh())

        self._connect_signal("sliderDepthMin", "valueChanged", self._on_depth_slider_changed)
        self._connect_signal("sliderDepthMax", "valueChanged", self._on_depth_slider_changed)
        self._connect_signal("sliderVExag", "valueChanged", self._on_simple_refresh_slider)
        self._connect_signal("sliderCrossSection", "valueChanged", self._on_simple_refresh_slider)
        self._connect_signal("sliderTrajRadius", "valueChanged", self._on_simple_refresh_slider)
        self._connect_signal("sliderOpacity", "valueChanged", self._on_simple_refresh_slider)
        self._connect_signal("sliderAmbient", "valueChanged", self._on_simple_refresh_slider)
        self._connect_signal("sliderDiffuse", "valueChanged", self._on_simple_refresh_slider)
        self._connect_signal("sliderSpecular", "valueChanged", self._on_simple_refresh_slider)
        self._connect_signal("sliderFOV", "valueChanged", self._on_simple_refresh_slider)

        self._connect_signal("sliderAzimuth", "valueChanged", self._on_camera_slider_changed)
        self._connect_signal("sliderElevation", "valueChanged", self._on_camera_slider_changed)
        self._connect_signal("sliderZoom", "valueChanged", self._on_camera_slider_changed)

        self._connect_signal("spinCmapMin", "valueChanged", lambda _value: self.refresh())
        self._connect_signal("spinCmapMax", "valueChanged", lambda _value: self.refresh())
        self._connect_button("btnAutoRange", self.auto_range_from_data)

        mode_buttons = QtWidgets.QButtonGroup(self)
        mode_buttons.setExclusive(True)
        for name in ("btnModeRotate", "btnModePan", "btnModeZoom", "btnModePick", "btnModeMeasure"):
            button = self._widget(name)
            if button is not None:
                mode_buttons.addButton(button)
                button.clicked.connect(self._update_mode_status)

        rotate_button = self._widget("btnModeRotate")
        if rotate_button is not None:
            rotate_button.setChecked(True)

    def refresh(self) -> None:
        wells = self._wells()
        well_names = sorted(wells.keys())
        self._populate_well_list(well_names)
        self._update_slider_labels()
        self._update_status_renderer()

        if not well_names:
            self.stop_animation()
            self._scene_cache = {}
            self._render_message("No wells loaded yet.\nImport a well to render the 3D workspace.")
            self._set_status("3D Well Visualization  |  No wells loaded")
            self._set_text("lblStatusWells", "Wells: 0 / 0")
            self._set_text("lblStatusTriangles", "Geometry: --")
            self._set_text("lblWellCountIndicator", "Wells Visible: 0 / 0")
            self._set_text("lblRenderInfo", "Awaiting imported well data")
            self._reset_pick_labels()
            return

        selected_names = self._selected_well_names()
        trajectories: dict[str, pd.DataFrame] = {}
        source_notes: list[str] = []
        valid_points = 0
        all_curves = self._numeric_curve_union([wells[name] for name in selected_names if name in wells])
        self._populate_curve_controls(all_curves)

        for name in selected_names:
            well = wells.get(name)
            if well is None:
                continue
            trajectory, note = self._build_trajectory(well)
            if trajectory is None or trajectory.empty:
                continue
            trajectory = self._attach_curve_columns(well, trajectory)
            trajectories[name] = trajectory
            valid_points += len(trajectory)
            source_notes.append(f"{name}: {note}")

        self._scene_cache = trajectories
        visible_count = len(trajectories)
        self._set_text("lblStatusWells", f"Wells: {visible_count} / {len(well_names)}")
        self._set_text("lblWellCountIndicator", f"Wells Visible: {visible_count} / {len(well_names)}")

        if not trajectories:
            self.stop_animation()
            self._render_message(
                "Loaded wells were found, but no usable trajectory columns could be derived.\n"
                "Expected depth or survey columns such as MD, TVD, X/Y, deviation, or azimuth."
            )
            self._set_status("3D Well Visualization  |  No valid trajectory data")
            self._set_text("lblStatusTriangles", "Geometry: 0")
            self._set_text("lblRenderInfo", "No trajectory could be derived from the selected wells")
            self._reset_pick_labels()
            return

        self._sync_depth_slider_ranges(trajectories)
        clipped = self._clip_trajectories(trajectories)
        if not clipped:
            self._render_message("The selected depth clip removes all visible trajectory samples.")
            self._set_status("3D Well Visualization  |  Depth clip hides all samples")
            self._set_text("lblStatusTriangles", "Geometry: 0")
            self._set_text("lblRenderInfo", "Adjust the depth range to show trajectory data")
            self._reset_pick_labels()
            return

        self._plot_scene(clipped)
        visible_samples = sum(len(df) for df in clipped.values())
        segment_count = max(visible_samples - len(clipped), 0)
        self._set_text("lblStatusTriangles", f"Geometry: {segment_count:,} segments")
        self._set_text("lblRenderInfo", f"Rendered {len(clipped)} well(s) | {visible_samples:,} visible samples")
        self._set_status(f"3D Well Visualization  |  Ready  |  {len(clipped)} well(s) rendered")
        self._set_text("lblPickedFormation", "--")
        self._set_text("lblPickedWell", selected_names[0] if selected_names else "--")
        self._set_text("lblStatusCamera", self._camera_status_text())
        self._set_text("lblViewportProjection", self._projection_label)
        if source_notes:
            self._set_text("lblPickedFormation", source_notes[0][:80])

    def reset_view(self) -> None:
        self.stop_animation()
        defaults = {
            "sliderDepthMin": 0,
            "sliderDepthMax": 5000,
            "sliderVExag": 1,
            "sliderCrossSection": 50,
            "sliderTrajRadius": 5,
            "sliderOpacity": 100,
            "sliderAzimuth": 45,
            "sliderElevation": 30,
            "sliderFOV": 60,
            "sliderZoom": 100,
            "sliderAmbient": 40,
            "sliderDiffuse": 70,
            "sliderSpecular": 25,
        }
        for name, value in defaults.items():
            widget = self._widget(name)
            if widget is not None and hasattr(widget, "setValue"):
                widget.blockSignals(True)
                widget.setValue(value)
                widget.blockSignals(False)

        for name, checked in (
            ("chkShowTrajectory", True),
            ("chkShowDeviation", True),
            ("chkShowWellHead", True),
            ("chkShowTD", True),
            ("chkShowLogRibbon", True),
            ("chkShowReferenceGrid", True),
            ("chkShowAxes", True),
            ("chkShowDepthScale", True),
            ("chkShowCompass", False),
            ("chkShowWellNames", True),
            ("chkShowDepthLabels", True),
            ("chkShowValueLabels", True),
            ("chkShowColorbar", True),
            ("rdoBgDark", True),
        ):
            widget = self._widget(name)
            if widget is not None and hasattr(widget, "setChecked"):
                widget.blockSignals(True)
                widget.setChecked(checked)
                widget.blockSignals(False)

        for name, text in (
            ("cmbTrajStyle", "Tube / Cylinder"),
            ("cmbTrajColorBy", "Well (Unique)"),
            ("cmbColormap", "Viridis"),
            ("cmbCrossSection", "None"),
            ("cmbAnimSpeed", "1x"),
        ):
            widget = self._widget(name)
            if widget is not None and hasattr(widget, "setCurrentText"):
                widget.blockSignals(True)
                idx = widget.findText(text)
                if idx >= 0:
                    widget.setCurrentIndex(idx)
                widget.blockSignals(False)

        self._apply_view_preset("perspective", refresh=False)
        self._update_slider_labels()
        self.refresh()

    def set_camera(self, elev: float, azim: float) -> None:
        elev_slider = self._widget("sliderElevation")
        azim_slider = self._widget("sliderAzimuth")
        if elev_slider is not None:
            elev_slider.setValue(int(round(elev)))
        if azim_slider is not None:
            azim_slider.setValue(int(round(azim)))
        self._apply_camera_to_canvas()

    def export_view(self) -> None:
        if self.figure is None:
            QtWidgets.QMessageBox.information(self.window, "3D Well Export", "No 3D figure is available yet.")
            return
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.window,
            "Export 3D Well Figure",
            str(ROOT_DIR / "outputs" / "3d_well_view.png"),
            "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;PDF Document (*.pdf)",
        )
        if not file_path:
            return
        self._save_figure(file_path)

    def export_screenshot(self) -> None:
        if self.figure is None:
            QtWidgets.QMessageBox.information(self.window, "3D Screenshot", "No 3D figure is available yet.")
            return
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.window,
            "Save 3D Screenshot",
            str(ROOT_DIR / "outputs" / "3d_well_screenshot.png"),
            "PNG Image (*.png)",
        )
        if not file_path:
            return
        self._save_figure(file_path)

    def start_animation(self) -> None:
        if not self._scene_cache:
            self.refresh()
        if not self._scene_cache:
            return
        speed_text = self._current_text("cmbAnimSpeed", "1x").lower().replace("x", "")
        try:
            speed = float(speed_text)
        except ValueError:
            speed = 1.0
        interval = max(40, int(220 / max(speed, 0.2)))
        self._animation_timer.start(interval)
        self._set_status("3D Well Visualization  |  Depth animation running")

    def stop_animation(self) -> None:
        self._animation_timer.stop()

    def auto_range_from_data(self) -> None:
        trajectories = self._scene_cache or {}
        if not trajectories:
            self.refresh()
            trajectories = self._scene_cache
        property_name = self._current_property_name()
        values: list[np.ndarray] = []
        for trajectory in trajectories.values():
            series = trajectory.get(property_name)
            if series is None:
                continue
            arr = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
            arr = arr[np.isfinite(arr)]
            if self._is_log_scale():
                arr = arr[arr > 0]
            if arr.size:
                values.append(arr)
        if not values:
            self._set_status(f"3D Well Visualization  |  No numeric '{property_name}' values available for auto range")
            return
        merged = np.concatenate(values)
        min_value = float(np.nanmin(merged))
        max_value = float(np.nanmax(merged))
        spin_min = self._widget("spinCmapMin")
        spin_max = self._widget("spinCmapMax")
        if spin_min is not None:
            spin_min.blockSignals(True)
            spin_min.setValue(min_value)
            spin_min.blockSignals(False)
        if spin_max is not None:
            spin_max.blockSignals(True)
            spin_max.setValue(max_value)
            spin_max.blockSignals(False)
        self.refresh()

    def _configure_ui_defaults(self) -> None:
        self._update_slider_labels()
        self._update_mode_status()
        self._apply_view_preset("perspective", refresh=False)
        self._set_text("lblStatusRenderer", "Renderer: Matplotlib 3D")
        self._reset_pick_labels()

    def _build_plot_host(self) -> None:
        gl_widget = self._widget("glWidget3D")
        if gl_widget is None:
            return
        parent = gl_widget.parentWidget()
        if parent is None:
            return
        layout = parent.layout()
        host = QtWidgets.QFrame(parent)
        host.setObjectName("frame3DPlotHost")
        host.setStyleSheet("background:#07101E;border:none;")
        host_layout = QtWidgets.QVBoxLayout(host)
        host_layout.setContentsMargins(0, 0, 0, 0)
        if layout is not None:
            layout.replaceWidget(gl_widget, host)
        gl_widget.hide()
        gl_widget.setParent(None)
        gl_widget.deleteLater()
        self._plot_host = host
        self.window.frame3DPlotHost = host

    def _widget(self, name: str):
        return self.page.findChild(QtCore.QObject, name)

    def _connect_button(self, name: str, handler) -> None:
        button = self._widget(name)
        if button is not None and hasattr(button, "clicked"):
            button.clicked.connect(handler)

    def _connect_signal(self, name: str, signal_name: str, handler) -> None:
        widget = self._widget(name)
        if widget is None:
            return
        signal = getattr(widget, signal_name, None)
        if signal is not None:
            signal.connect(handler)

    def _data_service(self):
        data_service = getattr(self.window, "_data_service", None)
        if data_service is None:
            controller = getattr(self.window, "controller", None)
            data_service = getattr(controller, "data", None) if controller is not None else None
        return data_service

    def _wells(self) -> dict[str, Any]:
        data_service = self._data_service()
        return getattr(data_service, "_wells", {}) or {}

    def _selected_well_names(self) -> list[str]:
        list_widget = self._widget("listWells")
        if list_widget is None:
            return self._selected_names[:]
        names = [item.text() for item in list_widget.selectedItems()]
        if names:
            self._selected_names = names
        return self._selected_names[:]

    def _populate_well_list(self, well_names: list[str]) -> None:
        list_widget = self._widget("listWells")
        if list_widget is None:
            return

        previous = self._selected_well_names()
        if not previous:
            data_service = self._data_service()
            current = getattr(data_service, "_current_well", None) if data_service is not None else None
            if current:
                previous = [current]
        if not previous and well_names:
            previous = [well_names[0]]

        blocker = QtCore.QSignalBlocker(list_widget)
        list_widget.clear()
        for name in well_names:
            item = QtWidgets.QListWidgetItem(name)
            list_widget.addItem(item)
            if name in previous:
                item.setSelected(True)
        del blocker
        self._selected_names = [name for name in previous if name in well_names] or (well_names[:1] if well_names else [])

    def _select_all_wells(self) -> None:
        list_widget = self._widget("listWells")
        if list_widget is None:
            return
        list_widget.selectAll()
        self._selected_names = [list_widget.item(i).text() for i in range(list_widget.count())]
        self.refresh()

    def _clear_well_selection(self) -> None:
        list_widget = self._widget("listWells")
        if list_widget is None:
            return
        list_widget.clearSelection()
        names = sorted(self._wells().keys())
        if names:
            list_widget.item(0).setSelected(True)
            self._selected_names = [names[0]]
        self.refresh()

    def _on_well_selection_changed(self) -> None:
        selected_names = self._selected_well_names()
        if not selected_names:
            return
        data_service = self._data_service()
        if data_service is not None and getattr(data_service, "_current_well", None) != selected_names[0]:
            data_service._current_well = selected_names[0]
        self.refresh()

    def _sync_depth_slider_ranges(self, trajectories: dict[str, pd.DataFrame]) -> None:
        min_tvd = min(float(df["tvd"].min()) for df in trajectories.values())
        max_tvd = max(float(df["tvd"].max()) for df in trajectories.values())
        slider_min = self._widget("sliderDepthMin")
        slider_max = self._widget("sliderDepthMax")
        if slider_min is None or slider_max is None:
            return
        lower_bound = int(np.floor(min_tvd))
        upper_bound = int(np.ceil(max_tvd))
        if upper_bound <= lower_bound:
            upper_bound = lower_bound + 1

        current_min = max(lower_bound, min(slider_min.value(), upper_bound))
        current_max = max(current_min + 1, min(slider_max.value(), upper_bound))
        for slider, value in ((slider_min, current_min), (slider_max, current_max)):
            slider.blockSignals(True)
            slider.setMinimum(lower_bound)
            slider.setMaximum(upper_bound)
            slider.setValue(value)
            slider.blockSignals(False)
        self._update_slider_labels()

    def _clip_trajectories(self, trajectories: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        depth_min = self._value("sliderDepthMin", 0)
        depth_max = self._value("sliderDepthMax", 5000)
        if depth_min > depth_max:
            depth_min, depth_max = depth_max, depth_min

        clipped: dict[str, pd.DataFrame] = {}
        for name, trajectory in trajectories.items():
            window = trajectory[(trajectory["tvd"] >= depth_min) & (trajectory["tvd"] <= depth_max)].copy()
            if not window.empty:
                clipped[name] = window.reset_index(drop=True)
        return clipped

    def _plot_scene(self, trajectories: dict[str, pd.DataFrame]) -> None:
        import matplotlib.pyplot as plt
        from matplotlib import colors
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

        bg_mode = self._background_mode()
        figure_face, axes_face, font_color, grid_color = self._background_palette(bg_mode)
        fig = plt.figure(figsize=(9.2, 6.1), constrained_layout=True)
        fig.patch.set_facecolor(figure_face)
        ax = fig.add_subplot(111, projection="3d")
        ax.set_facecolor(axes_face)

        projection_type = "persp" if bg_mode != "light" else "ortho"
        if self._current_text("cmbCrossSection", "None") != "None":
            projection_type = "ortho"
        try:
            ax.set_proj_type(projection_type)
        except Exception:
            pass

        alpha = max(0.2, min(self._value("sliderOpacity", 100) / 100.0, 1.0))
        vertical_exag = max(self._value("sliderVExag", 1), 1)
        style_text = self._current_text("cmbTrajStyle", "Tube / Cylinder")
        line_style, line_scale = self._line_style_from_ui(style_text)
        radius = max(1, self._value("sliderTrajRadius", 5))
        show_trajectory = self._is_checked("chkShowTrajectory", True)
        show_markers = self._is_checked("chkShowWellHead", True) or self._is_checked("chkShowTD", True)
        show_colorbar = self._is_checked("chkShowColorbar", True)
        show_deviation = self._is_checked("chkShowDeviation", True)
        show_labels = self._is_checked("chkShowWellNames", True)
        show_depth_labels = self._is_checked("chkShowDepthLabels", True)

        all_xyz = []
        colorbar_artist = None
        self._pick_points = {
            "x": np.array([], dtype=float),
            "y": np.array([], dtype=float),
            "z": np.array([], dtype=float),
            "meta": [],
        }

        for idx, (well_name, trajectory) in enumerate(trajectories.items()):
            x_vals = trajectory["x"].to_numpy(dtype=float)
            y_vals = trajectory["y"].to_numpy(dtype=float)
            z_vals = trajectory["tvd"].to_numpy(dtype=float) * vertical_exag
            all_xyz.append(np.column_stack([x_vals, y_vals, z_vals]))

            base_color = self._well_palette(idx)
            color_mode = self._current_text("cmbTrajColorBy", "Well (Unique)")
            cmap_name = self._matplotlib_cmap_name(self._current_text("cmbColormap", "Viridis"))
            color_values, norm, use_cmap = self._color_values_for_plot(trajectory, color_mode)

            if show_trajectory:
                if use_cmap and color_values is not None:
                    scatter = ax.scatter(
                        x_vals,
                        y_vals,
                        z_vals,
                        c=color_values,
                        cmap=cmap_name,
                        norm=norm,
                        s=max(12, radius * 10),
                        alpha=alpha,
                        edgecolors="none",
                    )
                    if show_colorbar and colorbar_artist is None:
                        colorbar_artist = scatter
                else:
                    ax.plot(
                        x_vals,
                        y_vals,
                        z_vals,
                        color=base_color,
                        linewidth=max(1.5, radius * 0.35 * line_scale),
                        linestyle=line_style,
                        alpha=alpha,
                    )

            if self._is_checked("chkShowLogRibbon", True):
                overlay_values = self._overlay_values(trajectory)
                if overlay_values is not None:
                    scatter = ax.scatter(
                        x_vals,
                        y_vals,
                        z_vals,
                        c=overlay_values,
                        cmap=cmap_name,
                        norm=self._build_norm(overlay_values),
                        s=max(16, radius * 7),
                        alpha=min(1.0, alpha + 0.08),
                        linewidths=0.15,
                        edgecolors="#F8FBFE",
                    )
                    if show_colorbar and colorbar_artist is None:
                        colorbar_artist = scatter

            if show_deviation and "deviation" in trajectory:
                deviation_values = trajectory["deviation"].to_numpy(dtype=float)
                ax.scatter(
                    x_vals,
                    y_vals,
                    z_vals,
                    c=deviation_values,
                    cmap="magma",
                    s=max(8, radius * 2),
                    alpha=min(0.55, alpha),
                    edgecolors="none",
                )

            if self._is_checked("chkShowWellHead", True):
                ax.scatter(x_vals[:1], y_vals[:1], z_vals[:1], color="#4FD1C5", s=60, depthshade=False)
            if self._is_checked("chkShowTD", True):
                ax.scatter(x_vals[-1:], y_vals[-1:], z_vals[-1:], color="#FF8A3D", s=60, depthshade=False)

            if show_labels:
                ax.text(x_vals[0], y_vals[0], z_vals[0], f" {well_name}", color=font_color, fontsize=8, weight="bold")
            if show_depth_labels:
                ax.text(x_vals[-1], y_vals[-1], z_vals[-1], f" TD {trajectory['md'].iloc[-1]:,.0f} m", color="#FFB26B", fontsize=8)

            self._append_pick_points(well_name, trajectory, z_vals)

        if colorbar_artist is not None and show_colorbar:
            colorbar = fig.colorbar(colorbar_artist, ax=ax, pad=0.05, shrink=0.82)
            colorbar.set_label(self._current_property_name(), color=font_color)
            colorbar.ax.yaxis.set_tick_params(color=font_color)
            plt.setp(colorbar.ax.get_yticklabels(), color=font_color)

        self._draw_cross_section(ax, trajectories, vertical_exag)
        self._style_axes(ax, font_color, grid_color)
        self._set_axis_limits(ax, all_xyz)
        self._apply_camera_to_axes(ax)

        ax.set_title("3D Well Visualization", fontsize=13, fontweight="bold", color=font_color, pad=16)
        ax.set_xlabel("X Offset (m)", color=font_color, labelpad=10)
        ax.set_ylabel("Y Offset (m)", color=font_color, labelpad=10)
        ax.set_zlabel(f"TVD x{vertical_exag:.0f} (m)", color=font_color, labelpad=12)

        self._disconnect_canvas_events()
        self._render_canvas(FigureCanvas(fig), fig, ax)

    def _render_canvas(self, canvas, fig, ax) -> None:
        if self._plot_host is None:
            return
        layout = self._plot_host.layout()
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        layout.addWidget(canvas, 1)
        self.figure = fig
        self.axes = ax
        self.canvas = canvas
        self._connect_canvas_events()
        canvas.draw_idle()

    def _render_message(self, text: str) -> None:
        if self._plot_host is None:
            return
        layout = self._plot_host.layout()
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        label = QtWidgets.QLabel(text, self._plot_host)
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet("color:#C9DDF2;font-size:12px;font-weight:600;padding:20px;")
        layout.addWidget(label, 1)
        self.figure = None
        self.axes = None
        self.canvas = None
        self._disconnect_canvas_events()

    def _connect_canvas_events(self) -> None:
        if self.canvas is None:
            return
        self._event_ids = [
            self.canvas.mpl_connect("motion_notify_event", self._on_canvas_motion),
            self.canvas.mpl_connect("button_press_event", self._on_canvas_click),
        ]

    def _disconnect_canvas_events(self) -> None:
        if self.canvas is None:
            self._event_ids = []
            return
        for cid in self._event_ids:
            try:
                self.canvas.mpl_disconnect(cid)
            except Exception:
                pass
        self._event_ids = []

    def _on_canvas_motion(self, event) -> None:
        pick = self._nearest_pick(event)
        if pick is None:
            self._set_text("lblCursorX", "X: --")
            self._set_text("lblCursorY", "Y: --")
            self._set_text("lblCursorTVD", "TVD (m): --")
            self._set_text("lblCursorMD", "MD (m): --")
            return
        self._set_text("lblCursorX", f"X: {pick.x:,.1f}")
        self._set_text("lblCursorY", f"Y: {pick.y:,.1f}")
        self._set_text("lblCursorTVD", f"TVD (m): {pick.tvd:,.1f}")
        self._set_text("lblCursorMD", f"MD (m): {pick.md:,.1f}")
        self._set_text("lblPickedWell", pick.well_name)

    def _on_canvas_click(self, event) -> None:
        pick = self._nearest_pick(event)
        if pick is None:
            return
        if self._is_checked("btnModeMeasure", False):
            if self._measure_anchor is None:
                self._measure_anchor = pick
                self._set_status(f"3D Well Visualization  |  Measure start fixed at {pick.well_name} MD {pick.md:,.1f} m")
                return
            dx = pick.x - self._measure_anchor.x
            dy = pick.y - self._measure_anchor.y
            dz = pick.tvd - self._measure_anchor.tvd
            distance = float(np.sqrt((dx ** 2) + (dy ** 2) + (dz ** 2)))
            self._set_status(f"3D Well Visualization  |  Measured distance: {distance:,.1f} m")
            self._measure_anchor = None
            return

        self._measure_anchor = None
        self._set_text("lblPickedWell", pick.well_name)
        self._set_text("lblPickWell", pick.well_name)
        self._set_text("lblPickMD", f"{pick.md:,.2f} m")
        self._set_text("lblPickTVD", f"{pick.tvd:,.2f} m")
        self._set_text("lblPickTVDSS", f"{-pick.tvd:,.2f} m")
        self._set_text("lblPickFormation", self._infer_formation_label(pick.tvd))

        mapping = {
            "GR": "lblPickGR",
            "RHOB": "lblPickRHOB",
            "NPHI": "lblPickNPHI",
            "VSHALE": "lblPickVsh",
            "PHIE": "lblPickPHIE",
            "SW": "lblPickSw",
            "PERMEABILITYK": "lblPickK",
            "NETPAYFLAG": "lblPickNetPay",
        }
        for key, label_name in mapping.items():
            value = pick.values.get(key)
            if value is None or not np.isfinite(value):
                continue
            suffix = self._value_suffix(label_name)
            self._set_text(label_name, f"{value:,.3f}{suffix}")
        self._set_text("lblPickedFormation", self._infer_formation_label(pick.tvd))
        self._set_status(f"3D Well Visualization  |  Picked {pick.well_name} at MD {pick.md:,.1f} m")

    def _nearest_pick(self, event) -> PickResult | None:
        if self.axes is None or not self._pick_points or event is None or event.inaxes != self.axes:
            return None
        xs = self._pick_points["x"]
        if xs.size == 0:
            return None

        from mpl_toolkits.mplot3d import proj3d

        x2, y2, _ = proj3d.proj_transform(self._pick_points["x"], self._pick_points["y"], self._pick_points["z"], self.axes.get_proj())
        points = self.axes.transData.transform(np.column_stack([x2, y2]))
        distances = np.hypot(points[:, 0] - event.x, points[:, 1] - event.y)
        index = int(np.argmin(distances))
        if float(distances[index]) > 32.0:
            return None
        meta = self._pick_points["meta"][index]
        return PickResult(
            well_name=meta["well_name"],
            index=meta["index"],
            md=meta["md"],
            tvd=meta["tvd"],
            x=meta["x"],
            y=meta["y"],
            values=meta["values"],
        )

    def _append_pick_points(self, well_name: str, trajectory: pd.DataFrame, z_vals: np.ndarray) -> None:
        step = max(1, len(trajectory) // 1500)
        sampled = trajectory.iloc[::step].reset_index(drop=True)
        sampled_z = z_vals[::step]
        self._pick_points["x"] = np.concatenate([self._pick_points["x"], sampled["x"].to_numpy(dtype=float)])
        self._pick_points["y"] = np.concatenate([self._pick_points["y"], sampled["y"].to_numpy(dtype=float)])
        self._pick_points["z"] = np.concatenate([self._pick_points["z"], sampled_z.astype(float)])

        property_keys = ("GR", "RHOB", "NPHI", "VSHALE", "PHIE", "SW", "PERMEABILITYK", "NETPAYFLAG")
        for row_idx, row in sampled.iterrows():
            values = {}
            for key in property_keys:
                values[key] = float(row[key]) if key in row and pd.notna(row[key]) else None
            self._pick_points["meta"].append(
                {
                    "well_name": well_name,
                    "index": row_idx,
                    "md": float(row["md"]),
                    "tvd": float(row["tvd"]),
                    "x": float(row["x"]),
                    "y": float(row["y"]),
                    "values": values,
                }
            )

    def _save_figure(self, file_path: str) -> None:
        if self.figure is None:
            return
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            self.figure.savefig(file_path, dpi=220, bbox_inches="tight", facecolor=self.figure.get_facecolor())
            QtWidgets.QMessageBox.information(self.window, "3D Well Export", f"Figure exported successfully:\n{file_path}")
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self.window, "3D Well Export", f"Failed to export figure:\n{exc}")

    def _apply_view_preset(self, preset: str, refresh: bool = True) -> None:
        presets = {
            "perspective": (45, 30, "Perspective"),
            "top": (0, 90, "Top"),
            "front": (0, 0, "Front"),
            "side": (90, 0, "Side"),
            "iso": (45, 35, "Isometric"),
        }
        azim, elev, label = presets.get(preset, presets["perspective"])
        self._projection_label = label
        self._set_view_buttons(preset)
        for name, value in (("sliderAzimuth", azim), ("sliderElevation", elev)):
            slider = self._widget(name)
            if slider is not None:
                slider.blockSignals(True)
                slider.setValue(int(value))
                slider.blockSignals(False)
        self._update_slider_labels()
        if refresh:
            self.refresh()

    def _set_view_buttons(self, active: str) -> None:
        mapping = {
            "perspective": "btnViewPerspective",
            "top": "btnViewTop",
            "front": "btnViewFront",
            "side": "btnViewSide",
            "iso": "btnViewIso",
        }
        for key, name in mapping.items():
            button = self._widget(name)
            if button is not None and hasattr(button, "setChecked"):
                button.blockSignals(True)
                button.setChecked(key == active)
                button.blockSignals(False)

    def _toggle_clip_plane(self) -> None:
        combo = self._widget("cmbCrossSection")
        if combo is None:
            return
        current = combo.currentText()
        target = "X-Plane" if current == "None" else "None"
        combo.setCurrentText(target)
        self.refresh()

    def _update_mode_status(self) -> None:
        for name, label in (
            ("btnModeRotate", "Rotate"),
            ("btnModePan", "Pan"),
            ("btnModeZoom", "Zoom"),
            ("btnModePick", "Pick"),
            ("btnModeMeasure", "Measure"),
        ):
            if self._is_checked(name, False):
                self._set_text("lblViewportProjection", f"{self._projection_label}  |  Mode: {label}")
                return
        self._set_text("lblViewportProjection", self._projection_label)

    def _on_depth_slider_changed(self, _value: int) -> None:
        slider_min = self._widget("sliderDepthMin")
        slider_max = self._widget("sliderDepthMax")
        if slider_min is None or slider_max is None:
            return
        if slider_min.value() > slider_max.value():
            sender = self.sender()
            if sender is slider_min:
                slider_max.blockSignals(True)
                slider_max.setValue(slider_min.value())
                slider_max.blockSignals(False)
            else:
                slider_min.blockSignals(True)
                slider_min.setValue(slider_max.value())
                slider_min.blockSignals(False)
        self._update_slider_labels()
        self.refresh()

    def _on_simple_refresh_slider(self, _value: int) -> None:
        self._update_slider_labels()
        self.refresh()

    def _on_camera_slider_changed(self, _value: int) -> None:
        self._update_slider_labels()
        self._apply_camera_to_canvas()

    def _apply_camera_to_canvas(self) -> None:
        if self.axes is None or self.canvas is None:
            self.refresh()
            return
        self._apply_camera_to_axes(self.axes)
        self._set_text("lblStatusCamera", self._camera_status_text())
        self.canvas.draw_idle()

    def _apply_camera_to_axes(self, ax) -> None:
        elev = self._value("sliderElevation", 30)
        azim = self._value("sliderAzimuth", 45)
        zoom = max(self._value("sliderZoom", 100) / 100.0, 0.1)
        ax.view_init(elev=elev, azim=azim)
        if hasattr(ax, "dist"):
            try:
                ax.dist = max(4.0, 10.0 / zoom)
            except Exception:
                pass
        self._set_text("lblStatusCamera", self._camera_status_text())

    def _set_axis_limits(self, ax, point_blocks: list[np.ndarray]) -> None:
        if not point_blocks:
            return
        stacked = np.vstack(point_blocks)
        mins = stacked.min(axis=0)
        maxs = stacked.max(axis=0)
        center = (mins + maxs) / 2.0
        span = float(np.max(maxs - mins))
        zoom = max(self._value("sliderZoom", 100) / 100.0, 0.1)
        half = max(span / max(zoom, 0.1) / 2.0, 1.0)
        ax.set_xlim(center[0] - half, center[0] + half)
        ax.set_ylim(center[1] - half, center[1] + half)
        ax.set_zlim(center[2] + half, center[2] - half)

    def _style_axes(self, ax, font_color: str, grid_color: str) -> None:
        show_grid = self._is_checked("chkShowReferenceGrid", True)
        show_axes = self._is_checked("chkShowAxes", True)
        show_depth_scale = self._is_checked("chkShowDepthScale", True)
        ax.grid(show_grid, alpha=0.25 if show_grid else 0.0)

        for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
            try:
                axis.label.set_color(font_color)
                axis.set_pane_color((0.12, 0.18, 0.28, 0.08))
                axis._axinfo["grid"]["color"] = grid_color
                axis._axinfo["tick"]["color"] = font_color
            except Exception:
                pass

        if not show_axes:
            ax.set_axis_off()
            return

        ax.tick_params(colors=font_color)
        if not show_depth_scale:
            ax.set_zticklabels([])

        if self._is_checked("chkShowCompass", False):
            ax.text2D(0.03, 0.96, "N", transform=ax.transAxes, color=font_color, fontsize=10, weight="bold")

    def _draw_cross_section(self, ax, trajectories: dict[str, pd.DataFrame], vertical_exag: float) -> None:
        cross_section = self._current_text("cmbCrossSection", "None")
        if cross_section == "None":
            self._set_text("lblCrossSectionVal", f"{self._value('sliderCrossSection', 50)}%")
            return

        stacked = np.vstack(
            [
                np.column_stack([df["x"].to_numpy(dtype=float), df["y"].to_numpy(dtype=float), df["tvd"].to_numpy(dtype=float) * vertical_exag])
                for df in trajectories.values()
            ]
        )
        mins = stacked.min(axis=0)
        maxs = stacked.max(axis=0)
        position = self._value("sliderCrossSection", 50) / 100.0
        self._set_text("lblCrossSectionVal", f"{int(position * 100)}%")

        resolution = 2
        if cross_section in {"X-Plane", "Custom"}:
            x_value = mins[0] + position * (maxs[0] - mins[0])
            y = np.linspace(mins[1], maxs[1], resolution)
            z = np.linspace(mins[2], maxs[2], resolution)
            yy, zz = np.meshgrid(y, z)
            xx = np.full_like(yy, x_value)
        elif cross_section == "Y-Plane":
            y_value = mins[1] + position * (maxs[1] - mins[1])
            x = np.linspace(mins[0], maxs[0], resolution)
            z = np.linspace(mins[2], maxs[2], resolution)
            xx, zz = np.meshgrid(x, z)
            yy = np.full_like(xx, y_value)
        else:
            z_value = mins[2] + position * (maxs[2] - mins[2])
            x = np.linspace(mins[0], maxs[0], resolution)
            y = np.linspace(mins[1], maxs[1], resolution)
            xx, yy = np.meshgrid(x, y)
            zz = np.full_like(xx, z_value)
        ax.plot_surface(xx, yy, zz, color="#7EC8E3", alpha=0.10, linewidth=0)

    def _color_values_for_plot(self, trajectory: pd.DataFrame, color_mode: str):
        from matplotlib import colors

        if color_mode == "Well (Unique)":
            return None, None, False
        if color_mode == "Formation Zone":
            bins = np.linspace(float(trajectory["tvd"].min()), float(trajectory["tvd"].max()), 5)
            return np.digitize(trajectory["tvd"].to_numpy(dtype=float), bins, right=True), colors.Normalize(vmin=0, vmax=4), True

        property_name = self._property_name_from_color_mode(color_mode)
        if property_name not in trajectory:
            return None, None, False
        values = pd.to_numeric(trajectory[property_name], errors="coerce").to_numpy(dtype=float)
        return values, self._build_norm(values), True

    def _overlay_values(self, trajectory: pd.DataFrame) -> np.ndarray | None:
        property_name = self._current_overlay_property_name()
        if property_name not in trajectory:
            return None
        values = pd.to_numeric(trajectory[property_name], errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(values).any():
            return None
        return values

    def _build_norm(self, values: np.ndarray):
        from matplotlib import colors

        spin_min = self._widget("spinCmapMin")
        spin_max = self._widget("spinCmapMax")
        finite = values[np.isfinite(values)]
        if finite.size == 0:
            return None
        vmin = float(spin_min.value()) if spin_min is not None else float(np.nanmin(finite))
        vmax = float(spin_max.value()) if spin_max is not None else float(np.nanmax(finite))
        if vmax <= vmin:
            vmax = vmin + 1e-9
        if self._is_log_scale():
            positive = finite[finite > 0]
            if positive.size:
                vmin = max(vmin, float(np.nanmin(positive)))
                vmax = max(vmax, vmin * 1.01)
                return colors.LogNorm(vmin=vmin, vmax=vmax)
        return colors.Normalize(vmin=vmin, vmax=vmax)

    def _attach_curve_columns(self, well, trajectory: pd.DataFrame) -> pd.DataFrame:
        df = getattr(well, "data", None)
        if df is None or getattr(df, "empty", True):
            return trajectory
        result = trajectory.copy()
        property_aliases = {
            "GR": ("GR", "GAMMA", "GAMMARAY"),
            "RHOB": ("RHOB", "RHOZ", "DEN", "DENSITY"),
            "NPHI": ("NPHI", "NPHI_LS", "NEUT", "NEUTRON"),
            "RT": ("RT", "ILD", "ILM", "LLD", "RDEP", "RESD"),
            "VSHALE": ("VSHALE", "VSH", "VSH"),
            "PHIE": ("PHIE", "PHI", "POR", "EFFECTIVEPOROSITY"),
            "SW": ("SW", "SATW", "WATERSATURATION"),
            "PERMEABILITYK": ("PERMEABILITY", "PERM", "K"),
            "NETPAYFLAG": ("NETPAY", "PAYFLAG", "PAY", "NETPAYFLAG"),
        }
        for target, aliases in property_aliases.items():
            series = self._interpolate_curve(df, aliases, result["md"].to_numpy(dtype=float))
            if series is not None:
                result[target] = series
        return result

    def _build_trajectory(self, well):
        df = getattr(well, "data", None)
        if df is None or getattr(df, "empty", True):
            return None, "No well data available"

        trajectory = pd.DataFrame()
        md_col = self._match_column(df, "MD", "DEPTH", "DEPT", "MEASUREDDEPTH")
        tvd_col = self._match_column(df, "TVD", "TVDSS", "TRUEVERTICALDEPTH")
        x_col = self._match_column(df, "X", "XCOORD", "XCOORDINATE", "EASTING", "UTMX")
        y_col = self._match_column(df, "Y", "YCOORD", "YCOORDINATE", "NORTHING", "UTMY")
        dev_col = self._match_column(df, "DEVIATION", "DEVI", "DEV", "INC", "INCLINATION")
        azi_col = self._match_column(df, "AZIMUTH", "AZI", "AZM")

        if md_col is not None:
            trajectory["md"] = pd.to_numeric(df[md_col], errors="coerce")
            notes = [f"MD from '{md_col}'"]
        else:
            trajectory["md"] = np.arange(len(df), dtype=float)
            notes = ["MD synthesized from sample index"]

        for key, column in (("tvd", tvd_col), ("x", x_col), ("y", y_col), ("deviation", dev_col), ("azimuth", azi_col)):
            if column is not None:
                trajectory[key] = pd.to_numeric(df[column], errors="coerce")

        trajectory = trajectory.dropna(subset=["md"]).sort_values("md").drop_duplicates("md").reset_index(drop=True)
        if trajectory.empty:
            return None, "No numeric depth values were found"

        delta_md = trajectory["md"].diff().fillna(0.0).clip(lower=0.0).to_numpy()
        if "tvd" in trajectory:
            trajectory["tvd"] = trajectory["tvd"].interpolate(limit_direction="both").bfill().ffill()
            trajectory["tvd"] = trajectory["tvd"] - float(trajectory["tvd"].iloc[0])
            notes.append(f"TVD from '{tvd_col}'")
        elif "deviation" in trajectory:
            deviation_rad = np.radians(trajectory["deviation"].fillna(0.0).to_numpy())
            trajectory["tvd"] = np.cumsum(delta_md * np.cos(deviation_rad))
            notes.append(f"TVD estimated from '{dev_col}'")
        else:
            trajectory["tvd"] = trajectory["md"] - float(trajectory["md"].iloc[0])
            notes.append("Vertical TVD assumption from measured depth")

        if "x" in trajectory and "y" in trajectory:
            trajectory["x"] = trajectory["x"].interpolate(limit_direction="both").bfill().ffill()
            trajectory["y"] = trajectory["y"].interpolate(limit_direction="both").bfill().ffill()
            trajectory["x"] = trajectory["x"] - float(trajectory["x"].iloc[0])
            trajectory["y"] = trajectory["y"] - float(trajectory["y"].iloc[0])
            notes.append(f"Plan view from '{x_col}' and '{y_col}'")
        elif "deviation" in trajectory and "azimuth" in trajectory:
            deviation_rad = np.radians(trajectory["deviation"].fillna(0.0).to_numpy())
            azimuth_rad = np.radians(trajectory["azimuth"].fillna(0.0).to_numpy())
            lateral_step = delta_md * np.sin(deviation_rad)
            trajectory["x"] = np.cumsum(lateral_step * np.sin(azimuth_rad))
            trajectory["y"] = np.cumsum(lateral_step * np.cos(azimuth_rad))
            notes.append(f"Lateral offsets estimated from '{dev_col}' and '{azi_col}'")
        else:
            trajectory["x"] = 0.0
            trajectory["y"] = 0.0
            notes.append("Vertical well path assumed")

        if "deviation" not in trajectory:
            dx = np.diff(trajectory["x"].to_numpy(dtype=float), prepend=float(trajectory["x"].iloc[0]))
            dy = np.diff(trajectory["y"].to_numpy(dtype=float), prepend=float(trajectory["y"].iloc[0]))
            dz = np.diff(trajectory["tvd"].to_numpy(dtype=float), prepend=float(trajectory["tvd"].iloc[0]))
            lateral = np.sqrt((dx ** 2) + (dy ** 2))
            vertical = np.maximum(np.abs(dz), 1e-9)
            trajectory["deviation"] = np.degrees(np.arctan2(lateral, vertical))
        else:
            trajectory["deviation"] = trajectory["deviation"].ffill().fillna(0.0)

        return trajectory, " | ".join(notes)

    def _match_column(self, df: pd.DataFrame, *aliases: str) -> str | None:
        lookup = {}
        for column in df.columns:
            lookup[self._normalize(str(column))] = column
        for alias in aliases:
            key = self._normalize(alias)
            if key in lookup:
                return lookup[key]
        for column in df.columns:
            normalized = self._normalize(str(column))
            if any(self._normalize(alias) in normalized for alias in aliases):
                return str(column)
        return None

    def _interpolate_curve(self, df: pd.DataFrame, aliases: tuple[str, ...], target_md: np.ndarray) -> np.ndarray | None:
        curve_col = self._match_column(df, *aliases)
        if curve_col is None:
            return None
        md_col = self._match_column(df, "MD", "DEPTH", "DEPT", "MEASUREDDEPTH")
        if md_col is None:
            source_md = np.arange(len(df), dtype=float)
        else:
            source_md = pd.to_numeric(df[md_col], errors="coerce").to_numpy(dtype=float)
        values = pd.to_numeric(df[curve_col], errors="coerce").to_numpy(dtype=float)
        mask = np.isfinite(source_md) & np.isfinite(values)
        if mask.sum() < 2:
            return None
        source_md = source_md[mask]
        values = values[mask]
        order = np.argsort(source_md)
        source_md = source_md[order]
        values = values[order]
        return np.interp(target_md, source_md, values, left=np.nan, right=np.nan)

    def _numeric_curve_union(self, wells: list[Any]) -> list[str]:
        names: set[str] = set()
        for well in wells:
            df = getattr(well, "data", None)
            if df is None:
                continue
            for column in df.columns:
                series = pd.to_numeric(df[column], errors="coerce")
                if series.notna().sum() > 1:
                    names.add(str(column))
        return sorted(names)

    def _populate_curve_controls(self, curve_names: list[str]) -> None:
        defaults = ["GR", "RHOB", "NPHI", "RT", "VSHALE", "PHIE", "SW", "PERMEABILITY", "NETPAYFLAG"]
        available = curve_names or defaults
        for widget_name in ("cmbOverlayCurve", "cmbCmapProperty"):
            combo = self._widget(widget_name)
            if combo is None:
                continue
            current = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(available)
            if current:
                idx = combo.findText(current)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            combo.blockSignals(False)

    def _property_name_from_color_mode(self, color_mode: str) -> str:
        mapping = {
            "Log Curve": self._current_property_name(),
            "Vshale": "VSHALE",
            "Porosity (PHIE)": "PHIE",
            "Water Sat. (Sw)": "SW",
            "Permeability (K)": "PERMEABILITYK",
            "Net Pay Flag": "NETPAYFLAG",
        }
        return mapping.get(color_mode, self._current_property_name())

    def _current_property_name(self) -> str:
        text = self._current_text("cmbCmapProperty", self._current_text("cmbOverlayCurve", "GR"))
        return self._property_token(text)

    def _current_overlay_property_name(self) -> str:
        text = self._current_text("cmbOverlayCurve", self._current_text("cmbCmapProperty", "GR"))
        return self._property_token(text)

    def _property_token(self, text: str) -> str:
        normalized = self._normalize(text)
        mapping = {
            "GR": "GR",
            "RHOB": "RHOB",
            "NPHI": "NPHI",
            "RTILD": "RT",
            "RT": "RT",
            "VSHALE": "VSHALE",
            "PHIE": "PHIE",
            "POROSITYPHIE": "PHIE",
            "WATERSATSW": "SW",
            "SW": "SW",
            "PERMEABILITYK": "PERMEABILITYK",
            "NETPAYFLAG": "NETPAYFLAG",
        }
        return mapping.get(normalized, normalized)

    def _infer_formation_label(self, tvd: float) -> str:
        if not np.isfinite(tvd):
            return "--"
        if tvd < 500:
            return "Shallow interval"
        if tvd < 1500:
            return "Intermediate interval"
        if tvd < 3000:
            return "Reservoir interval"
        return "Deep interval"

    def _line_style_from_ui(self, text: str) -> tuple[str, float]:
        if text == "Line":
            return "-", 1.0
        if text == "Ribbon":
            return "-", 1.6
        if text == "Dotted / Dashed":
            return "--", 0.9
        return "-", 1.35

    def _well_palette(self, index: int) -> str:
        palette = ["#4AA3DF", "#7E8BFF", "#4FD1C5", "#F5B661", "#FF6B6B", "#95D26A", "#9B7BFF"]
        return palette[index % len(palette)]

    def _matplotlib_cmap_name(self, text: str) -> str:
        mapping = {
            "Rainbow": "rainbow",
            "Jet": "jet",
            "Viridis": "viridis",
            "Plasma": "plasma",
            "Inferno": "inferno",
            "Hot": "hot",
            "RdYlGn": "RdYlGn",
            "Seismic": "seismic",
            "Petro (Custom)": "turbo",
        }
        cmap = mapping.get(text, "viridis")
        if self._is_checked("chkInvertCmap", False):
            return f"{cmap}_r"
        return cmap

    def _background_mode(self) -> str:
        if self._is_checked("rdoBgLight", False):
            return "light"
        if self._is_checked("rdoBgGradient", False):
            return "gradient"
        return "dark"

    def _background_palette(self, mode: str) -> tuple[str, str, str, str]:
        if mode == "light":
            return "#F8FBFE", "#FFFFFF", "#163B61", "#BFD2E2"
        if mode == "gradient":
            return "#0B1830", "#122742", "#D8E6F5", "#4A637A"
        return "#07101E", "#07101E", "#DCEBFA", "#385066"

    def _camera_status_text(self) -> str:
        return (
            f"{self._projection_label}  |  "
            f"Az: {self._value('sliderAzimuth', 45)}°  "
            f"El: {self._value('sliderElevation', 30)}°  |  "
            f"Zoom: {self._value('sliderZoom', 100)}%"
        )

    def _update_status_renderer(self) -> None:
        ambient = self._value("sliderAmbient", 40)
        diffuse = self._value("sliderDiffuse", 70)
        specular = self._value("sliderSpecular", 25)
        shadows = " + Shadows" if self._is_checked("chkShadows", False) else ""
        self._set_text("lblStatusRenderer", f"Renderer: Matplotlib 3D  |  Light {ambient}/{diffuse}/{specular}{shadows}")

    def _update_slider_labels(self) -> None:
        self._set_text("lblDepthMinVal", str(self._value("sliderDepthMin", 0)))
        self._set_text("lblDepthMaxVal", str(self._value("sliderDepthMax", 5000)))
        self._set_text("lblVExagVal", f"{self._value('sliderVExag', 1)}x")
        self._set_text("lblCrossSectionVal", f"{self._value('sliderCrossSection', 50)}%")
        self._set_text("lblTrajRadiusVal", str(self._value("sliderTrajRadius", 5)))
        self._set_text("lblOpacityVal", f"{self._value('sliderOpacity', 100)}%")
        self._set_text("lblAzimuthVal", f"{self._value('sliderAzimuth', 45)}°")
        self._set_text("lblElevationVal", f"{self._value('sliderElevation', 30)}°")
        self._set_text("lblFOVVal", f"{self._value('sliderFOV', 60)}°")
        self._set_text("lblZoomVal", f"{self._value('sliderZoom', 100)}%")
        self._set_text("lblAmbientVal", f"{self._value('sliderAmbient', 40)}%")
        self._set_text("lblDiffuseVal", f"{self._value('sliderDiffuse', 70)}%")
        self._set_text("lblSpecularVal", f"{self._value('sliderSpecular', 25)}%")
        self._set_text("lblStatusCamera", self._camera_status_text())

    def _advance_animation(self) -> None:
        slider = self._widget("sliderDepthMax")
        slider_min = self._widget("sliderDepthMin")
        if slider is None or slider_min is None:
            self.stop_animation()
            return
        step = max(1, int((slider.maximum() - slider.minimum()) / 60))
        next_value = slider.value() + step
        if next_value > slider.maximum():
            next_value = max(slider_min.value() + step, slider.minimum())
        slider.setValue(next_value)

    def _reset_pick_labels(self) -> None:
        for name, text in (
            ("lblPickWell", "--"),
            ("lblPickMD", "--"),
            ("lblPickTVD", "--"),
            ("lblPickTVDSS", "--"),
            ("lblPickFormation", "--"),
            ("lblPickGR", "--  API"),
            ("lblPickRHOB", "--  g/cc"),
            ("lblPickNPHI", "--  v/v"),
            ("lblPickVsh", "--  v/v"),
            ("lblPickPHIE", "--  v/v"),
            ("lblPickSw", "--  v/v"),
            ("lblPickK", "--  mD"),
            ("lblPickNetPay", "--"),
            ("lblCursorX", "X: --"),
            ("lblCursorY", "Y: --"),
            ("lblCursorTVD", "TVD (m): --"),
            ("lblCursorMD", "MD (m): --"),
            ("lblPickedWell", "--"),
            ("lblPickedFormation", "--"),
        ):
            self._set_text(name, text)

    def _set_status(self, text: str) -> None:
        self._set_text("lblStatus3D", text)

    def _set_text(self, name: str, text: str) -> None:
        widget = self._widget(name)
        if widget is not None and hasattr(widget, "setText"):
            widget.setText(text)

    def _current_text(self, name: str, default: str = "") -> str:
        widget = self._widget(name)
        if widget is not None and hasattr(widget, "currentText"):
            return str(widget.currentText())
        return default

    def _value(self, name: str, default: int = 0) -> int:
        widget = self._widget(name)
        if widget is not None and hasattr(widget, "value"):
            return int(widget.value())
        return default

    def _is_checked(self, name: str, default: bool) -> bool:
        widget = self._widget(name)
        if widget is not None and hasattr(widget, "isChecked"):
            return bool(widget.isChecked())
        return default

    def _is_log_scale(self) -> bool:
        return self._is_checked("chkLogScale", False)

    def _value_suffix(self, label_name: str) -> str:
        suffixes = {
            "lblPickGR": " API",
            "lblPickRHOB": " g/cc",
            "lblPickNPHI": " v/v",
            "lblPickVsh": " v/v",
            "lblPickPHIE": " v/v",
            "lblPickSw": " v/v",
            "lblPickK": " mD",
            "lblPickNetPay": "",
        }
        return suffixes.get(label_name, "")

    @staticmethod
    def _normalize(value: str) -> str:
        return "".join(ch for ch in str(value).upper() if ch.isalnum())
