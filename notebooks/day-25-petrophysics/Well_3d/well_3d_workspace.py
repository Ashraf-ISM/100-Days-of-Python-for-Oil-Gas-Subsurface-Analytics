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

    # ------------------------------------------------------------------ #
    #  Signal wiring                                                        #
    # ------------------------------------------------------------------ #

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
        self._connect_button("btnCustomRange", self._on_custom_range)

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

        view_buttons = QtWidgets.QButtonGroup(self)
        view_buttons.setExclusive(True)
        for name in ("btnViewPerspective", "btnViewTop", "btnViewFront",
                     "btnViewSide", "btnViewIso"):
            button = self._widget(name)
            if button is not None:
                view_buttons.addButton(button)

        self._vis_mode_map: dict[str, str] = {
            "btnVisModeColorTube": "Tube / Cylinder",
            "btnVisModeColorOnly": "Line",
            "btnVisModeRadius":    "Tube / Cylinder",
            "btnVisModeRibbon":    "Ribbon",
            "btnVisModePoints":    "Dotted / Dashed",
            "btnVisModeTrack":     "Line",
        }
        vis_group = QtWidgets.QButtonGroup(self)
        vis_group.setExclusive(True)
        for btn_name in self._vis_mode_map:
            button = self._widget(btn_name)
            if button is not None:
                vis_group.addButton(button)
                button.clicked.connect(
                    lambda _checked=False, bname=btn_name: self._on_vis_mode_clicked(bname)
                )
        first_vis = self._widget("btnVisModeColorTube") 
        if first_vis is not None:
            first_vis.setChecked(True)

    # ------------------------------------------------------------------ #
    #                          Public API                                #
    # ------------------------------------------------------------------ #

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
            ("rdoBgDark", True),
            ("chkShowWellNames", True),
            ("chkShowDepthLabels", True),
            ("chkShowValueLabels", True),
            ("chkShowColorbar", True),
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
            self._set_status(f"3D Well Visualization  |  No numeric '{property_name}' values available")
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

    # ------------------------------------------------------------------ #
    #  Initialisation helpers                                               #
    # ------------------------------------------------------------------ #

    def _configure_ui_defaults(self) -> None:
        self._update_slider_labels()
        self._update_mode_status()
        self._apply_view_preset("perspective", refresh=False)
        self._set_text("lblStatusRenderer", "Renderer: Matplotlib 3D  |  Tube Engine  |  Phong Lighting")
        self._reset_pick_labels()
        first_vis = self._widget("btnVisModeColorTube")
        if first_vis is not None and hasattr(first_vis, "setChecked"):
            first_vis.setChecked(True)

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
        host.setStyleSheet("background:#050D1A;border:none;")
        host_layout = QtWidgets.QVBoxLayout(host)
        host_layout.setContentsMargins(0, 0, 0, 0)
        if layout is not None:
            layout.replaceWidget(gl_widget, host)
        gl_widget.hide()
        gl_widget.setParent(None)
        gl_widget.deleteLater()
        self._plot_host = host
        self.window.frame3DPlotHost = host

    # ------------------------------------------------------------------ #
    #  Main scene renderer — professional tube engine                       #
    # ------------------------------------------------------------------ #

    def _plot_scene(self, trajectories: dict[str, pd.DataFrame]) -> None:
        import matplotlib
        import matplotlib.pyplot as plt
        import matplotlib.cm as cm
        from matplotlib import colors as mcolors
        from matplotlib.cm import ScalarMappable
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection

        bg_mode = self._background_mode()
        figure_face, axes_face, font_color, grid_color = self._background_palette(bg_mode)

        # ── figure with narrow margins for maximum viewport use ────────── #
        fig = plt.figure(figsize=(10.2, 7.2), facecolor=figure_face)
        fig.patch.set_facecolor(figure_face)

        # Leave right margin for colorbar breathing room
        ax = fig.add_axes([0.04, 0.06, 0.84, 0.88], projection="3d")
        ax.set_facecolor(axes_face)

        try:
            ax.set_proj_type("persp")
        except Exception:
            pass

        alpha        = max(0.20, min(self._value("sliderOpacity", 100) / 100.0, 1.0))
        v_exag       = max(self._value("sliderVExag", 1), 1)
        base_radius  = max(1, self._value("sliderTrajRadius", 5)) * 1.35
        style_text   = self._current_text("cmbTrajStyle", "Tube / Cylinder")
        color_mode   = self._current_text("cmbTrajColorBy", "Well (Unique)")
        cmap_name    = self._matplotlib_cmap_name(self._current_text("cmbColormap", "Viridis"))
        use_tube     = style_text in ("Tube / Cylinder", "Ribbon")
        show_cb      = self._is_checked("chkShowColorbar", True)
        show_labels  = self._is_checked("chkShowWellNames", True)
        show_td_lbl  = self._is_checked("chkShowDepthLabels", True)
        show_rings   = self._is_checked("chkShowDepthScale", True)
        show_head    = self._is_checked("chkShowWellHead", True)
        show_td      = self._is_checked("chkShowTD", True)
        show_ribbon  = self._is_checked("chkShowLogRibbon", True)
        show_perf    = self._is_checked("chkShowPerforations", False)
        show_casing  = self._is_checked("chkShowCasing", False)
        show_pay     = self._is_checked("chkShowPayZones", False)
        relief_scale = 0.30 if style_text == "Ribbon" else 0.45

        # Lighting parameters from sliders (0–100 → 0–1)
        ambient_k  = self._value("sliderAmbient",  40) / 100.0
        diffuse_k  = self._value("sliderDiffuse",  70) / 100.0
        specular_k = self._value("sliderSpecular", 25) / 100.0

        all_xyz: list[np.ndarray] = []
        sm_for_colorbar: ScalarMappable | None = None
        global_norm = None
        global_cmap = cmap_name

        self._pick_points = {
            "x": np.array([], dtype=float),
            "y": np.array([], dtype=float),
            "z": np.array([], dtype=float),
            "meta": [],
        }

        # ── first pass: shared colour range ──────────────────────────── #
        all_color_vals: list[np.ndarray] = []
        for name in trajectories:
            traj = trajectories[name]
            cv, norm, use_cmap = self._color_values_for_plot(traj, color_mode)
            if use_cmap and cv is not None:
                finite = cv[np.isfinite(cv)]
                if finite.size:
                    all_color_vals.append(finite)

        if all_color_vals:
            merged  = np.concatenate(all_color_vals)
            v_min   = float(np.nanmin(merged))
            v_max   = float(np.nanmax(merged))
            if v_max <= v_min:
                v_max = v_min + 1.0
            if self._is_log_scale() and v_min > 0:
                global_norm = mcolors.LogNorm(vmin=v_min, vmax=v_max)
            else:
                spin_min = self._widget("spinCmapMin")
                spin_max = self._widget("spinCmapMax")
                if spin_min is not None and spin_max is not None:
                    v_min = spin_min.value()
                    v_max = spin_max.value()
                    if v_max <= v_min:
                        v_max = v_min + 1.0
                global_norm = mcolors.Normalize(vmin=v_min, vmax=v_max)

        # ── second pass: render each well ─────────────────────────────── #
        for idx, (well_name, trajectory) in enumerate(trajectories.items()):
            n_full  = len(trajectory)
            x_full  = trajectory["x"].to_numpy(dtype=float)
            y_full  = trajectory["y"].to_numpy(dtype=float)
            z_full  = trajectory["tvd"].to_numpy(dtype=float) * v_exag
            all_xyz.append(np.column_stack([x_full, y_full, z_full]))

            well_color = self._well_palette(idx)

            # colour values ----------------------------------------------- #
            cv, norm_local, use_cmap = self._color_values_for_plot(trajectory, color_mode)
            if use_cmap and cv is not None:
                norm_use = global_norm or norm_local
                vals_use = cv
            else:
                vals_use  = z_full.copy()
                norm_use  = global_norm or mcolors.Normalize(
                    vmin=float(z_full.min()), vmax=float(z_full.max())
                )

            # downsample for tube geometry -------------------------------- #
            max_pts = 320
            step    = max(1, n_full // max_pts)
            x_ds    = x_full[::step]
            y_ds    = y_full[::step]
            z_ds    = z_full[::step]
            v_ds    = vals_use[::step] if len(vals_use) == n_full else vals_use

            # ── floor projection shadow (subtle, depth-grounding) ─────── #
            if self._is_checked("chkShowDeviation", True) and len(x_ds) > 1:
                floor_z = float(np.max(z_full)) * 1.06
                ax.plot(
                    x_ds, y_ds,
                    zs=floor_z, zdir="z",
                    color=well_color,
                    linewidth=1.0,
                    linestyle=":",
                    alpha=0.22,
                )
                # vertical leader line from wellhead to floor
                ax.plot(
                    [x_full[0], x_full[0]],
                    [y_full[0], y_full[0]],
                    [z_full[0], floor_z],
                    color=well_color,
                    linewidth=0.55,
                    linestyle="--",
                    alpha=0.30,
                )

            # ── tube / fallback line ─────────────────────────────────── #
            if use_tube and len(x_ds) >= 3:
                surf = self._render_tube_surface(
                    ax,
                    x_ds, y_ds, z_ds, v_ds,
                    cmap_name, norm_use, alpha,
                    base_radius, relief_scale,
                    ambient_k=ambient_k,
                    diffuse_k=diffuse_k,
                    specular_k=specular_k,
                    n_sides=24,
                )
                if surf is not None and show_cb and sm_for_colorbar is None:
                    sm_for_colorbar = ScalarMappable(cmap=cmap_name, norm=norm_use)
                    sm_for_colorbar.set_array(v_ds[np.isfinite(v_ds)])
                    global_cmap = cmap_name
            else:
                line_style, line_w = self._line_style_from_ui(style_text)
                ax.plot(
                    x_ds, y_ds, z_ds,
                    color=well_color,
                    linewidth=max(2.0, base_radius * 0.42 * line_w),
                    linestyle=line_style,
                    alpha=alpha,
                    solid_capstyle="round",
                )

            # ── log ribbon overlay (scatter) ─────────────────────────── #
            if show_ribbon:
                ov_vals = self._overlay_values(trajectory)
                if ov_vals is not None:
                    ov_ds   = ov_vals[::step]
                    ov_norm = self._build_norm(ov_vals)
                    scat = ax.scatter(
                        x_ds, y_ds, z_ds,
                        c=ov_ds, cmap=cmap_name, norm=ov_norm,
                        s=max(22, base_radius * 7.5),
                        alpha=min(1.0, alpha + 0.12),
                        linewidths=0.25,
                        edgecolors="#B8D4F0",
                        zorder=6,
                    )
                    if show_cb and sm_for_colorbar is None:
                        sm_for_colorbar = ScalarMappable(cmap=cmap_name, norm=ov_norm)
                        sm_for_colorbar.set_array(ov_ds[np.isfinite(ov_ds)])

            # ── casing shoe marker ────────────────────────────────────── #
            if show_casing and len(x_ds) > 4:
                shoe_idx = min(int(len(x_ds) * 0.22), len(x_ds) - 2)
                self._draw_casing_shoe(
                    ax, x_ds[shoe_idx], y_ds[shoe_idx], z_ds[shoe_idx],
                    base_radius * 2.0, font_color
                )

            # ── perforation cluster markers ───────────────────────────── #
            if show_perf and len(x_ds) > 6:
                perf_indices = np.linspace(int(len(x_ds) * 0.55),
                                           int(len(x_ds) * 0.78),
                                           min(4, len(x_ds) // 3), dtype=int)
                for pi in perf_indices:
                    self._draw_perforation(
                        ax, x_ds[pi], y_ds[pi], z_ds[pi],
                        base_radius * 1.6
                    )

            # ── pay zone highlight band ───────────────────────────────── #
            if show_pay and len(x_ds) > 8:
                pay_start = int(len(x_ds) * 0.58)
                pay_end   = min(int(len(x_ds) * 0.72), len(x_ds) - 1)
                self._draw_pay_zone_band(
                    ax,
                    x_ds[pay_start:pay_end],
                    y_ds[pay_start:pay_end],
                    z_ds[pay_start:pay_end],
                    base_radius * 2.2,
                )

            # ── depth rings ───────────────────────────────────────────── #
            if show_rings and len(x_ds) >= 5:
                self._draw_depth_rings(ax, x_ds, y_ds, z_ds,
                                       base_radius, font_color, n_rings=8)

            # ── well-head sphere + glow ───────────────────────────────── #
            if show_head:
                self._draw_glow_sphere(ax, x_full[0], y_full[0], z_full[0],
                                       base_radius * 2.0, "#4FD1C5",
                                       glow_color="#1AFFF0", alpha=0.96)

            # ── TD cone / sphere + glow ───────────────────────────────── #
            if show_td:
                self._draw_glow_sphere(ax, x_full[-1], y_full[-1], z_full[-1],
                                       base_radius * 2.0, "#FF8A3D",
                                       glow_color="#FFB870", alpha=0.96)

            # ── well labels with leader lines ─────────────────────────── #
            if show_labels:
                lbl_offset_x = base_radius * 3.5
                lbl_offset_z = -base_radius * 2.5
                ax.plot(
                    [x_full[0], x_full[0] + lbl_offset_x],
                    [y_full[0], y_full[0]],
                    [z_full[0], z_full[0] + lbl_offset_z],
                    color=well_color, linewidth=0.7, alpha=0.60, zorder=19,
                )
                ax.text(
                    x_full[0] + lbl_offset_x,
                    y_full[0],
                    z_full[0] + lbl_offset_z,
                    f"  {well_name}",
                    color="#FFFFFF",
                    fontsize=9,
                    fontweight="bold",
                    fontfamily="monospace",
                    bbox=dict(
                        boxstyle="round,pad=0.32",
                        facecolor="#0B1E38",
                        edgecolor=well_color,
                        alpha=0.88,
                        linewidth=1.2,
                    ),
                    zorder=22,
                )

            # ── TD depth label ────────────────────────────────────────── #
            if show_td_lbl:
                ax.text(
                    x_full[-1] + base_radius * 2.0,
                    y_full[-1],
                    z_full[-1],
                    f" ▼ TD {trajectory['md'].iloc[-1]:,.0f} m",
                    color="#FFB870",
                    fontsize=7.8,
                    fontfamily="monospace",
                    bbox=dict(
                        boxstyle="round,pad=0.22",
                        facecolor="#1C0E00",
                        edgecolor="#FF8A3D",
                        alpha=0.80,
                        linewidth=0.9,
                    ),
                    zorder=22,
                )

            self._append_pick_points(well_name, trajectory, z_full)

        # ── professional colorbar ─────────────────────────────────────── #
        if sm_for_colorbar is not None and show_cb:
            try:
                cbar = fig.colorbar(
                    sm_for_colorbar, ax=ax,
                    pad=0.02, shrink=0.68, aspect=22,
                    orientation="vertical",
                    drawedges=False,
                )
                prop_label = self._current_property_name()
                cbar.set_label(
                    prop_label, color=font_color,
                    fontsize=9.5, labelpad=10,
                    fontweight="bold", fontfamily="monospace",
                )
                cbar.ax.yaxis.set_tick_params(color=font_color, labelsize=8, length=3)
                plt.setp(cbar.ax.get_yticklabels(), color=font_color, fontfamily="monospace")
                cbar.outline.set_edgecolor("#2A4A6A")
                cbar.outline.set_linewidth(0.9)
                cbar.ax.set_facecolor(axes_face)
                # min / max annotation pins
                norm_obj = sm_for_colorbar.norm
                arr = sm_for_colorbar.get_array()
                if arr is not None and arr.size:
                    cbar.ax.text(
                        1.55, 0.01, f"{float(np.nanmin(arr)):.3g}",
                        transform=cbar.ax.transAxes,
                        color="#7AAFD4", fontsize=7, fontfamily="monospace", va="bottom",
                    )
                    cbar.ax.text(
                        1.55, 0.99, f"{float(np.nanmax(arr)):.3g}",
                        transform=cbar.ax.transAxes,
                        color="#7AAFD4", fontsize=7, fontfamily="monospace", va="top",
                    )
            except Exception:
                pass

        # ── cross-section plane ───────────────────────────────────────── #
        self._draw_cross_section(ax, trajectories, v_exag)

        # ── base floor plane (structural grounding) ───────────────────── #
        self._draw_floor_plane(ax, all_xyz, font_color, grid_color)

        # ── axes styling & camera ─────────────────────────────────────── #
        self._style_axes(ax, font_color, grid_color)
        self._set_axis_limits(ax, all_xyz)
        self._apply_camera_to_axes(ax)

        # ── title block ───────────────────────────────────────────────── #
        ax.set_title(
            "3D Well Trajectory Visualization",
            fontsize=13, fontweight="bold",
            color=font_color, pad=18,
            fontfamily="monospace",
        )
        ax.set_xlabel("X Offset  (m)", color=font_color, labelpad=12, fontsize=9)
        ax.set_ylabel("Y Offset  (m)", color=font_color, labelpad=12, fontsize=9)
        ax.set_zlabel(f"TVD  ×{v_exag:.0f}  (m)", color=font_color, labelpad=14, fontsize=9)

        # ── renderer info watermark ───────────────────────────────────── #
        fig.text(
            0.01, 0.01,
            "PetroAnalystPro  |  3D Well Module  |  Tube Engine  |  Phong Shading",
            color="#2A4A6A", fontsize=6.5, fontfamily="monospace", alpha=0.70,
        )

        self._disconnect_canvas_events()
        self._render_canvas(FigureCanvas(fig), fig, ax)

    # ------------------------------------------------------------------ #
    #  3-D tube geometry engine — Phong-lit, Bishop-framed                  #
    # ------------------------------------------------------------------ #

    def _render_tube_surface(
        self,
        ax,
        x_vals: np.ndarray,
        y_vals: np.ndarray,
        z_vals: np.ndarray,
        values: np.ndarray,
        cmap_name: str,
        norm,
        alpha: float,
        base_radius: float,
        relief_scale: float = 0.45,
        n_sides: int = 24,
        ambient_k: float = 0.40,
        diffuse_k: float = 0.70,
        specular_k: float = 0.25,
        shininess: float = 18.0,
    ):
        """
        Render a 3-D lit borehole tube using:
          - Parallel-transport (Bishop) frames to eliminate twist artefacts
          - Radial relief mapping from log values
          - Per-face Phong diffuse + specular simulation
          - Edge darkening for visual depth cues
        """
        import matplotlib.cm as cm
        from matplotlib import colors as mcolors

        n = len(x_vals)
        if n < 2:
            return None

        positions = np.column_stack([x_vals, y_vals, z_vals])

        # ── tangent vectors ───────────────────────────────────────────── #
        tangents = np.empty_like(positions)
        tangents[1:-1] = positions[2:] - positions[:-2]
        tangents[0]    = positions[1]  - positions[0]
        tangents[-1]   = positions[-1] - positions[-2]
        t_norms        = np.linalg.norm(tangents, axis=1, keepdims=True)
        tangents       /= np.maximum(t_norms, 1e-10)

        # ── Bishop / parallel-transport frame ─────────────────────────── #
        normals = np.empty_like(positions)
        ref = np.array([0.0, 0.0, 1.0])
        if abs(float(tangents[0, 2])) > 0.85:
            ref = np.array([1.0, 0.0, 0.0])
        n0     = ref - np.dot(ref, tangents[0]) * tangents[0]
        n_mag  = float(np.linalg.norm(n0))
        normals[0] = n0 / max(n_mag, 1e-10)

        for i in range(1, n):
            t_prev = tangents[i - 1]
            t_cur  = tangents[i]
            axis   = np.cross(t_prev, t_cur)
            ax_mag = float(np.linalg.norm(axis))
            if ax_mag < 1e-12:
                normals[i] = normals[i - 1]
            else:
                axis  /= ax_mag
                angle  = float(np.arccos(np.clip(np.dot(t_prev, t_cur), -1.0, 1.0)))
                c, s   = np.cos(angle), np.sin(angle)
                n_prev = normals[i - 1]
                normals[i] = (
                    n_prev * c
                    + np.cross(axis, n_prev) * s
                    + axis * np.dot(axis, n_prev) * (1.0 - c)
                )
            normals[i] /= max(float(np.linalg.norm(normals[i])), 1e-10)

        binormals  = np.cross(tangents, normals)
        bn_mags    = np.linalg.norm(binormals, axis=1, keepdims=True)
        binormals  /= np.maximum(bn_mags, 1e-10)

        # ── sanitise colour values ────────────────────────────────────── #
        if values is not None and np.isfinite(values).any():
            finite_vals = values[np.isfinite(values)]
            fill_val    = float(np.nanmedian(finite_vals))
            vals        = np.where(np.isfinite(values), values, fill_val)
        else:
            vals = z_vals.copy()

        v_lo = float(np.nanmin(vals))
        v_hi = float(np.nanmax(vals))
        if v_hi > v_lo:
            relief = (vals - v_lo) / (v_hi - v_lo)
        else:
            relief = np.zeros(n)

        # ── tube mesh ─────────────────────────────────────────────────── #
        thetas = np.linspace(0.0, 2.0 * np.pi, n_sides, endpoint=False)
        TX = np.empty((n, n_sides + 1))
        TY = np.empty((n, n_sides + 1))
        TZ = np.empty((n, n_sides + 1))
        CV = np.empty((n, n_sides + 1))
        # Outward normals for Phong lighting
        NX = np.empty((n, n_sides + 1))
        NY = np.empty((n, n_sides + 1))
        NZ = np.empty((n, n_sides + 1))

        for j, theta in enumerate(thetas):
            r  = base_radius * (1.0 + relief_scale * relief)
            ct = np.cos(theta)
            st = np.sin(theta)
            # radial outward normal at this circumferential angle
            outward_x = ct * normals[:, 0] + st * binormals[:, 0]
            outward_y = ct * normals[:, 1] + st * binormals[:, 1]
            outward_z = ct * normals[:, 2] + st * binormals[:, 2]
            TX[:, j]  = positions[:, 0] + r * outward_x
            TY[:, j]  = positions[:, 1] + r * outward_y
            TZ[:, j]  = positions[:, 2] + r * outward_z
            CV[:, j]  = vals
            NX[:, j]  = outward_x
            NY[:, j]  = outward_y
            NZ[:, j]  = outward_z

        # close circumferentially
        TX[:, -1] = TX[:, 0];  TY[:, -1] = TY[:, 0];  TZ[:, -1] = TZ[:, 0]
        CV[:, -1] = CV[:, 0]
        NX[:, -1] = NX[:, 0];  NY[:, -1] = NY[:, 0];  NZ[:, -1] = NZ[:, 0]

        # ── per-face values (quad corner average) ─────────────────────── #
        face_vals = (
            CV[:-1, :-1] + CV[1:, :-1] + CV[:-1, 1:] + CV[1:, 1:]
        ) / 4.0

        # per-face outward normals
        fn_x = (NX[:-1, :-1] + NX[1:, :-1] + NX[:-1, 1:] + NX[1:, 1:]) / 4.0
        fn_y = (NY[:-1, :-1] + NY[1:, :-1] + NY[:-1, 1:] + NY[1:, 1:]) / 4.0
        fn_z = (NZ[:-1, :-1] + NZ[1:, :-1] + NZ[:-1, 1:] + NZ[1:, 1:]) / 4.0
        fn_len = np.sqrt(fn_x**2 + fn_y**2 + fn_z**2)
        fn_len = np.maximum(fn_len, 1e-10)
        fn_x /= fn_len;  fn_y /= fn_len;  fn_z /= fn_len

        # ── Phong shading: key light + fill + rim ─────────────────────── #
        key_light  = np.array([0.6,  0.4, -0.7]);  key_light  /= np.linalg.norm(key_light)
        fill_light = np.array([-0.4, 0.3, -0.3]);  fill_light /= np.linalg.norm(fill_light)
        rim_light  = np.array([0.0, -0.5,  0.5]);  rim_light  /= np.linalg.norm(rim_light)

        diff_key   = np.clip( fn_x*key_light[0]  + fn_y*key_light[1]  + fn_z*key_light[2],  0, 1)
        diff_fill  = np.clip( fn_x*fill_light[0] + fn_y*fill_light[1] + fn_z*fill_light[2], 0, 1) * 0.38
        diff_rim   = np.clip( fn_x*rim_light[0]  + fn_y*rim_light[1]  + fn_z*rim_light[2],  0, 1) * 0.22
        diffuse    = diffuse_k * (diff_key + diff_fill + diff_rim)

        # specular (Blinn-Phong halfway vector with view from top-right)
        view_dir  = np.array([0.5, 0.5, -0.7]);  view_dir /= np.linalg.norm(view_dir)
        halfway   = key_light + view_dir;          halfway  /= np.linalg.norm(halfway)
        spec_dot  = np.clip( fn_x*halfway[0] + fn_y*halfway[1] + fn_z*halfway[2], 0, 1)
        specular  = specular_k * (spec_dot ** shininess)

        intensity = np.clip(ambient_k + diffuse + specular, 0.0, 1.0)

        # ── map values → RGBA then modulate by lighting ───────────────── #
        cmap_obj = cm.get_cmap(cmap_name)
        if norm is None:
            norm_obj = mcolors.Normalize(vmin=v_lo, vmax=v_hi)
        else:
            norm_obj = norm

        face_rgba = cmap_obj(norm_obj(face_vals)).copy()   # (n-1, n_sides, 4)
        face_rgba[:, :, :3] *= intensity[:, :, np.newaxis]
        face_rgba[:, :, 3]   = alpha

        # ── edge silhouette darkening (depth cue) ─────────────────────── #
        # Columns near 0° and 180° of circumference are silhouette edges
        edge_mask = np.abs(np.cos(
            np.linspace(0, 2 * np.pi, n_sides, endpoint=False)
        ))                                                  # 1 at top/bottom, 0 at sides
        silhouette = 1.0 - (1.0 - edge_mask) * 0.35        # darken sides by up to 35 %
        face_rgba[:, :, :3] *= silhouette[np.newaxis, :, np.newaxis]
        face_rgba = np.clip(face_rgba, 0.0, 1.0)

        try:
            surf = ax.plot_surface(
                TX, TY, TZ,
                facecolors=face_rgba,
                linewidth=0,
                antialiased=True,
                shade=False,          # we supply our own shading
            )
            return surf
        except Exception:
            ax.plot(x_vals, y_vals, z_vals,
                    color=self._well_palette(0), linewidth=2.2, alpha=alpha)
            return None

    # ------------------------------------------------------------------ #
    #  Floor plane — structural grounding element                            #
    # ------------------------------------------------------------------ #

    def _draw_floor_plane(
        self,
        ax,
        point_blocks: list[np.ndarray],
        font_color: str,
        grid_color: str,
    ) -> None:
        if not point_blocks:
            return
        stacked = np.vstack(point_blocks)
        mins   = stacked.min(axis=0)
        maxs   = stacked.max(axis=0)
        span   = float(np.max(maxs[:2] - mins[:2]))
        pad    = span * 0.12
        floor_z = float(maxs[2]) * 1.10

        xl = [mins[0] - pad, maxs[0] + pad]
        yl = [mins[1] - pad, maxs[1] + pad]
        xx, yy = np.meshgrid(xl, yl)
        zz = np.full_like(xx, floor_z)

        ax.plot_surface(
            xx, yy, zz,
            color="#0D2540", alpha=0.18, linewidth=0, antialiased=False,
        )

        # faint grid lines on floor
        n_grid = 6
        xs = np.linspace(xl[0], xl[1], n_grid)
        ys = np.linspace(yl[0], yl[1], n_grid)
        for xv in xs:
            ax.plot([xv, xv], [yl[0], yl[1]], [floor_z, floor_z],
                    color=grid_color, linewidth=0.35, alpha=0.25)
        for yv in ys:
            ax.plot([xl[0], xl[1]], [yv, yv], [floor_z, floor_z],
                    color=grid_color, linewidth=0.35, alpha=0.25)

    # ------------------------------------------------------------------ #
    #  Depth rings with tick labels                                          #
    # ------------------------------------------------------------------ #

    def _draw_depth_rings(
        self,
        ax,
        x_vals: np.ndarray,
        y_vals: np.ndarray,
        z_vals: np.ndarray,
        radius: float,
        font_color: str,
        n_rings: int = 8,
    ) -> None:
        n = len(x_vals)
        if n < 4:
            return
        indices = np.linspace(1, n - 2, min(n_rings, n - 2), dtype=int)
        for ri in indices:
            rx, ry, rz = self._build_ring_geometry(x_vals, y_vals, z_vals,
                                                    ri, radius * 1.12)
            if rx is None:
                continue
            ax.plot(rx, ry, rz, color="#3E7AAF", linewidth=0.65, alpha=0.60)
            # tick label on ring
            ax.text(
                rx[0], ry[0], rz[0],
                f" {z_vals[ri]:,.0f}m",
                color="#5A96C8",
                fontsize=6.5,
                fontfamily="monospace",
                alpha=0.75,
                zorder=14,
            )

    def _build_ring_geometry(
        self,
        x_vals: np.ndarray,
        y_vals: np.ndarray,
        z_vals: np.ndarray,
        idx: int,
        radius: float,
        n_pts: int = 40,
    ):
        n = len(x_vals)
        if idx <= 0 or idx >= n - 1:
            return None, None, None

        pos     = np.array([x_vals[idx], y_vals[idx], z_vals[idx]])
        tangent = np.array([
            x_vals[idx + 1] - x_vals[idx - 1],
            y_vals[idx + 1] - y_vals[idx - 1],
            z_vals[idx + 1] - z_vals[idx - 1],
        ])
        t_mag = float(np.linalg.norm(tangent))
        if t_mag < 1e-10:
            return None, None, None
        tangent /= t_mag

        ref    = np.array([0.0, 0.0, 1.0]) if abs(tangent[2]) < 0.85 else np.array([1.0, 0.0, 0.0])
        normal = ref - np.dot(ref, tangent) * tangent
        n_mag  = float(np.linalg.norm(normal))
        if n_mag < 1e-10:
            return None, None, None
        normal  /= n_mag
        binormal = np.cross(tangent, normal)

        thetas  = np.linspace(0.0, 2.0 * np.pi, n_pts)
        ring_x  = pos[0] + radius * (np.cos(thetas) * normal[0] + np.sin(thetas) * binormal[0])
        ring_y  = pos[1] + radius * (np.cos(thetas) * normal[1] + np.sin(thetas) * binormal[1])
        ring_z  = pos[2] + radius * (np.cos(thetas) * normal[2] + np.sin(thetas) * binormal[2])
        return ring_x, ring_y, ring_z

    # ------------------------------------------------------------------ #
    #  Glow sphere — well-head / TD markers                                 #
    # ------------------------------------------------------------------ #

    def _draw_glow_sphere(
        self,
        ax,
        cx: float, cy: float, cz: float,
        radius: float,
        color: str,
        glow_color: str = "#FFFFFF",
        alpha: float = 1.0,
        n_lat: int = 12,
        n_lon: int = 16,
    ) -> None:
        """Sphere with a larger translucent halo for a professional 'glow' look."""
        # Halo pass (large, very transparent)
        u = np.linspace(0.0, np.pi, n_lat)
        v = np.linspace(0.0, 2.0 * np.pi, n_lon)
        r_halo = radius * 1.65
        sx = cx + r_halo * np.outer(np.sin(u), np.cos(v))
        sy = cy + r_halo * np.outer(np.sin(u), np.sin(v))
        sz = cz + r_halo * np.outer(np.cos(u), np.ones(n_lon))
        ax.plot_surface(sx, sy, sz,
                        color=glow_color, alpha=0.10,
                        linewidth=0, antialiased=True,
                        shade=False, zorder=14)
        # Core sphere
        sx = cx + radius * np.outer(np.sin(u), np.cos(v))
        sy = cy + radius * np.outer(np.sin(u), np.sin(v))
        sz = cz + radius * np.outer(np.cos(u), np.ones(n_lon))
        ax.plot_surface(sx, sy, sz,
                        color=color, alpha=alpha,
                        linewidth=0, antialiased=True,
                        shade=True, zorder=16)

    # ------------------------------------------------------------------ #
    #  Casing shoe marker                                                    #
    # ------------------------------------------------------------------ #

    def _draw_casing_shoe(
        self,
        ax,
        cx: float, cy: float, cz: float,
        radius: float,
        font_color: str,
    ) -> None:
        """Draw a casing shoe as a double-ring band."""
        for r_scale, lw, col in ((1.0, 1.2, "#A0C0E0"), (0.82, 0.7, "#6090B0")):
            ring_x, ring_y, ring_z = self._build_ring_geometry(
                np.array([cx, cx, cx]),
                np.array([cy, cy, cy]),
                np.array([cz - 0.5, cz, cz + 0.5]),
                1, radius * r_scale, n_pts=32
            )
            if ring_x is not None:
                ax.plot(ring_x, ring_y, ring_z,
                        color=col, linewidth=lw, alpha=0.80, zorder=12)
        ax.text(cx + radius * 1.4, cy, cz,
                " ◈ Casing",
                color="#8AB8D8", fontsize=6.5, fontfamily="monospace",
                alpha=0.75, zorder=18)

    # ------------------------------------------------------------------ #
    #  Perforation cluster marker                                             #
    # ------------------------------------------------------------------ #

    def _draw_perforation(
        self,
        ax,
        cx: float, cy: float, cz: float,
        radius: float,
    ) -> None:
        """Perforation shown as a star-shaped scatter burst."""
        n_perf = 6
        thetas = np.linspace(0, 2 * np.pi, n_perf, endpoint=False)
        for theta in thetas:
            dx = radius * 0.60 * np.cos(theta)
            dy = radius * 0.60 * np.sin(theta)
            ax.scatter(
                cx + dx, cy + dy, cz,
                c="#FF4444", s=9, alpha=0.85,
                edgecolors="#FF8888", linewidths=0.4, zorder=18,
            )
        ax.scatter(cx, cy, cz, c="#FF2222", s=16,
                   alpha=0.90, edgecolors="#FFAAAA",
                   linewidths=0.6, marker="*", zorder=19)

    # ------------------------------------------------------------------ #
    #  Pay zone band                                                          #
    # ------------------------------------------------------------------ #

    def _draw_pay_zone_band(
        self,
        ax,
        x_seg: np.ndarray,
        y_seg: np.ndarray,
        z_seg: np.ndarray,
        radius: float,
    ) -> None:
        """Translucent green band highlighting the pay zone interval."""
        if len(x_seg) < 2:
            return
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        verts = []
        n_pts = 20
        thetas = np.linspace(0, 2 * np.pi, n_pts)
        # Build cylinder caps at start and end of pay segment
        for idx in range(len(x_seg) - 1):
            cx, cy, cz = x_seg[idx], y_seg[idx], z_seg[idx]
            nx, ny, nz = x_seg[idx + 1], y_seg[idx + 1], z_seg[idx + 1]
            # simple ring quad strip approximation
            ax.plot(
                [cx, nx], [cy, ny], [cz, nz],
                color="#22FF88", linewidth=radius * 0.6,
                alpha=0.18, solid_capstyle="butt",
            )
        ax.text(
            x_seg[0], y_seg[0], z_seg[0],
            " ▶ Net Pay",
            color="#44FF99", fontsize=6.5, fontfamily="monospace",
            alpha=0.80, zorder=18,
        )

    # ------------------------------------------------------------------ #
    #  Canvas management                                                    #
    # ------------------------------------------------------------------ #

    def _render_canvas(self, canvas, fig, ax) -> None:
        if self._plot_host is None:
            return
        layout = self._plot_host.layout()
        while layout.count():
            item   = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        layout.addWidget(canvas, 1)
        self.figure = fig
        self.axes   = ax
        self.canvas = canvas
        self._connect_canvas_events()
        canvas.draw_idle()
        try:
            from plotting.plot_context_menu import install_plot_context_menu
            install_plot_context_menu(canvas, fig, self._plot_host)
        except Exception:
            pass

    def _render_message(self, text: str) -> None:
        if self._plot_host is None:
            return
        layout = self._plot_host.layout()
        while layout.count():
            item   = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        label = QtWidgets.QLabel(text, self._plot_host)
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet(
            "color:#5A8FBE;font-size:12px;font-weight:600;"
            "font-family:monospace;padding:24px;letter-spacing:0.5px;"
        )
        layout.addWidget(label, 1)
        self.figure = None
        self.axes   = None
        self.canvas = None
        self._disconnect_canvas_events()

    def _connect_canvas_events(self) -> None:
        if self.canvas is None:
            return
        self._event_ids = [
            self.canvas.mpl_connect("motion_notify_event", self._on_canvas_motion),
            self.canvas.mpl_connect("button_press_event",  self._on_canvas_click),
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

    # ------------------------------------------------------------------ #
    #  Mouse interaction                                                    #
    # ------------------------------------------------------------------ #

    def _on_canvas_motion(self, event) -> None:
        pick = self._nearest_pick(event)
        if pick is None:
            self._set_text("lblCursorX",   "X: --")
            self._set_text("lblCursorY",   "Y: --")
            self._set_text("lblCursorTVD", "TVD (m): --")
            self._set_text("lblCursorMD",  "MD (m): --")
            return
        self._set_text("lblCursorX",   f"X: {pick.x:,.1f}")
        self._set_text("lblCursorY",   f"Y: {pick.y:,.1f}")
        self._set_text("lblCursorTVD", f"TVD (m): {pick.tvd:,.1f}")
        self._set_text("lblCursorMD",  f"MD (m): {pick.md:,.1f}")
        self._set_text("lblPickedWell", pick.well_name)

    def _on_canvas_click(self, event) -> None:
        pick = self._nearest_pick(event)
        if pick is None:
            return
        if self._is_checked("btnModeMeasure", False):
            if self._measure_anchor is None:
                self._measure_anchor = pick
                self._set_status(
                    f"3D Well Visualization  |  Measure start: {pick.well_name} MD {pick.md:,.1f} m"
                )
                return
            dx = pick.x   - self._measure_anchor.x
            dy = pick.y   - self._measure_anchor.y
            dz = pick.tvd - self._measure_anchor.tvd
            distance = float(np.sqrt(dx**2 + dy**2 + dz**2))
            self._set_status(f"3D Well Visualization  |  Measured distance: {distance:,.1f} m")
            self._measure_anchor = None
            return

        self._measure_anchor = None
        self._set_text("lblPickedWell",    pick.well_name)
        self._set_text("lblPickWell",      pick.well_name)
        self._set_text("lblPickMD",        f"{pick.md:,.2f} m")
        self._set_text("lblPickTVD",       f"{pick.tvd:,.2f} m")
        self._set_text("lblPickTVDSS",     f"{-pick.tvd:,.2f} m")
        self._set_text("lblPickFormation", self._infer_formation_label(pick.tvd))

        mapping = {
            "GR":            "lblPickGR",
            "RHOB":          "lblPickRHOB",
            "NPHI":          "lblPickNPHI",
            "VSHALE":        "lblPickVsh",
            "PHIE":          "lblPickPHIE",
            "SW":            "lblPickSw",
            "PERMEABILITYK": "lblPickK",
            "NETPAYFLAG":    "lblPickNetPay",
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
        if (
            self.axes is None
            or not self._pick_points
            or event is None
            or event.inaxes != self.axes
        ):
            return None
        xs = self._pick_points["x"]
        if xs.size == 0:
            return None

        from mpl_toolkits.mplot3d import proj3d

        x2, y2, _ = proj3d.proj_transform(
            self._pick_points["x"],
            self._pick_points["y"],
            self._pick_points["z"],
            self.axes.get_proj(),
        )
        points    = self.axes.transData.transform(np.column_stack([x2, y2]))
        distances = np.hypot(points[:, 0] - event.x, points[:, 1] - event.y)
        index     = int(np.argmin(distances))
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

    def _append_pick_points(
        self,
        well_name: str,
        trajectory: pd.DataFrame,
        z_vals: np.ndarray,
    ) -> None:
        step     = max(1, len(trajectory) // 1500)
        sampled  = trajectory.iloc[::step].reset_index(drop=True)
        sampled_z = z_vals[::step]
        self._pick_points["x"] = np.concatenate(
            [self._pick_points["x"], sampled["x"].to_numpy(dtype=float)]
        )
        self._pick_points["y"] = np.concatenate(
            [self._pick_points["y"], sampled["y"].to_numpy(dtype=float)]
        )
        self._pick_points["z"] = np.concatenate(
            [self._pick_points["z"], sampled_z.astype(float)]
        )
        property_keys = (
            "GR", "RHOB", "NPHI", "VSHALE", "PHIE", "SW", "PERMEABILITYK", "NETPAYFLAG"
        )
        for row_idx, row in sampled.iterrows():
            values = {}
            for key in property_keys:
                values[key] = float(row[key]) if key in row and pd.notna(row[key]) else None
            self._pick_points["meta"].append({
                "well_name": well_name,
                "index":     row_idx,
                "md":        float(row["md"]),
                "tvd":       float(row["tvd"]),
                "x":         float(row["x"]),
                "y":         float(row["y"]),
                "values":    values,
            })

    # ------------------------------------------------------------------ #
    #  File I/O                                                             #
    # ------------------------------------------------------------------ #

    def _save_figure(self, file_path: str) -> None:
        if self.figure is None:
            return
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            self.figure.savefig(
                file_path, dpi=240, bbox_inches="tight",
                facecolor=self.figure.get_facecolor(),
                edgecolor="none",
            )
            QtWidgets.QMessageBox.information(
                self.window, "3D Well Export",
                f"Figure exported successfully:\n{file_path}"
            )
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self.window, "3D Well Export",
                f"Failed to export figure:\n{exc}"
            )

    # ------------------------------------------------------------------ #
    #  View presets & UI helpers                                            #
    # ------------------------------------------------------------------ #

    def _apply_view_preset(self, preset: str, refresh: bool = True) -> None:
        presets = {
            "perspective": (45, 30, "Perspective"),
            "top":         (0,  90, "Top"),
            "front":       (0,   0, "Front"),
            "side":        (90,  0, "Side"),
            "iso":         (45, 35, "Isometric"),
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
            "top":         "btnViewTop",
            "front":       "btnViewFront",
            "side":        "btnViewSide",
            "iso":         "btnViewIso",
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
        target  = "X-Plane" if current == "None" else "None"
        combo.setCurrentText(target)
        self.refresh()

    # ------------------------------------------------------------------ #
    #  Visualisation-mode button handler                                    #
    # ------------------------------------------------------------------ #

    def _on_vis_mode_clicked(self, btn_name: str) -> None:
        vis_map    = getattr(self, "_vis_mode_map", {})
        style_text = vis_map.get(btn_name, "Tube / Cylinder")

        if btn_name == "btnVisModeRadius":
            chk = self._widget("chkShowLogRibbon")
            if chk is not None:
                chk.blockSignals(True);  chk.setChecked(False);  chk.blockSignals(False)
        elif btn_name in ("btnVisModeColorTube", "btnVisModeColorOnly"):
            chk = self._widget("chkShowLogRibbon")
            if chk is not None:
                chk.blockSignals(True)
                chk.setChecked(btn_name == "btnVisModeColorTube")
                chk.blockSignals(False)
        elif btn_name == "btnVisModeRibbon":
            chk = self._widget("chkShowLogRibbon")
            if chk is not None:
                chk.blockSignals(True);  chk.setChecked(True);  chk.blockSignals(False)
        elif btn_name == "btnVisModePoints":
            style_text = "Dotted / Dashed"
        elif btn_name == "btnVisModeTrack":
            style_text = "Line"

        combo = self._widget("cmbTrajStyle")
        if combo is not None:
            idx = combo.findText(style_text)
            if idx >= 0:
                combo.blockSignals(True);  combo.setCurrentIndex(idx);  combo.blockSignals(False)
        self.refresh()

    # ------------------------------------------------------------------ #
    #  Custom range dialog                                                   #
    # ------------------------------------------------------------------ #

    def _on_custom_range(self) -> None:
        spin_min = self._widget("spinCmapMin")
        spin_max = self._widget("spinCmapMax")
        if spin_min is None or spin_max is None:
            return
        current_min = spin_min.value()
        current_max = spin_max.value()

        dialog = QtWidgets.QDialog(self.window)
        dialog.setWindowTitle("Custom Colormap Range")
        dialog.setFixedWidth(290)
        dialog.setStyleSheet(
            "QDialog{background:#0D1E38;border:1px solid #1E4070;}"
            "QLabel{color:#C0D8F0;font-family:monospace;font-size:11px;}"
            "QDoubleSpinBox{background:#0A1828;color:#C0D8F0;border:1px solid #2A4A6A;"
            "border-radius:4px;padding:4px;font-family:monospace;}"
            "QPushButton{border-radius:4px;padding:5px 16px;font-family:monospace;}"
        )
        layout = QtWidgets.QFormLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setVerticalSpacing(10)

        from PyQt5.QtWidgets import QDoubleSpinBox
        sb_min = QDoubleSpinBox(dialog)
        sb_min.setRange(-1e9, 1e9)
        sb_min.setDecimals(4)
        sb_min.setValue(current_min)
        sb_max = QDoubleSpinBox(dialog)
        sb_max.setRange(-1e9, 1e9)
        sb_max.setDecimals(4)
        sb_max.setValue(current_max)
        layout.addRow("Min:", sb_min)
        layout.addRow("Max:", sb_max)

        btn_row    = QtWidgets.QHBoxLayout()
        btn_ok     = QtWidgets.QPushButton("Apply")
        btn_cancel = QtWidgets.QPushButton("Cancel")
        btn_ok.setStyleSheet(
            "background:#1B6CA8;color:#FFF;border:1px solid #2A90D0;"
        )
        btn_cancel.setStyleSheet(
            "background:#1A2A3A;color:#8AADCC;border:1px solid #2A4A6A;"
        )
        btn_ok.clicked.connect(dialog.accept)
        btn_cancel.clicked.connect(dialog.reject)
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        layout.addRow(btn_row)

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            new_min = sb_min.value()
            new_max = sb_max.value()
            if new_max <= new_min:
                new_max = new_min + 1.0
            for sp, val in ((spin_min, new_min), (spin_max, new_max)):
                sp.blockSignals(True);  sp.setValue(val);  sp.blockSignals(False)
            self.refresh()

    def _update_mode_status(self) -> None:
        for name, label in (
            ("btnModeRotate",  "Rotate"),
            ("btnModePan",     "Pan"),
            ("btnModeZoom",    "Zoom"),
            ("btnModePick",    "Pick"),
            ("btnModeMeasure", "Measure"),
        ):
            if self._is_checked(name, False):
                self._set_text(
                    "lblViewportProjection",
                    f"{self._projection_label}  |  Mode: {label}"
                )
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
        azim = self._value("sliderAzimuth",   45)
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
        mins   = stacked.min(axis=0)
        maxs   = stacked.max(axis=0)
        center = (mins + maxs) / 2.0
        span   = float(np.max(maxs - mins))
        zoom   = max(self._value("sliderZoom", 100) / 100.0, 0.1)
        half   = max(span / max(zoom, 0.1) / 2.0, 1.0)
        ax.set_xlim(center[0] - half, center[0] + half)
        ax.set_ylim(center[1] - half, center[1] + half)
        ax.set_zlim(center[2] + half * 1.15, center[2] - half * 0.05)

    def _style_axes(self, ax, font_color: str, grid_color: str) -> None:
        show_grid        = self._is_checked("chkShowReferenceGrid", True)
        show_axes_flag   = self._is_checked("chkShowAxes", True)
        show_depth_scale = self._is_checked("chkShowDepthScale", True)

        ax.grid(show_grid, alpha=0.15 if show_grid else 0.0, linestyle=":")

        for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
            try:
                axis.label.set_color(font_color)
                axis.label.set_fontfamily("monospace")
                axis.set_pane_color((0.06, 0.12, 0.22, 0.04))
                axis._axinfo["grid"]["color"]     = grid_color
                axis._axinfo["grid"]["linewidth"] = 0.4
                axis._axinfo["tick"]["color"]     = font_color
                axis._axinfo["axisline"]["color"] = grid_color
            except Exception:
                pass

        if not show_axes_flag:
            ax.set_axis_off()
            return

        ax.tick_params(colors=font_color, labelsize=7.5, length=2.5, width=0.6)
        for lbl in ax.get_xticklabels() + ax.get_yticklabels() + ax.get_zticklabels():
            lbl.set_fontfamily("monospace")
            lbl.set_fontsize(7)

        if not show_depth_scale:
            ax.set_zticklabels([])

        if self._is_checked("chkShowCompass", False):
            ax.text2D(0.03, 0.96, "▲ N",
                      transform=ax.transAxes,
                      color=font_color, fontsize=10, fontweight="bold",
                      fontfamily="monospace")

    def _draw_cross_section(
        self, ax, trajectories: dict[str, pd.DataFrame], vertical_exag: float
    ) -> None:
        cross_section = self._current_text("cmbCrossSection", "None")
        if cross_section == "None":
            self._set_text("lblCrossSectionVal",
                           f"{self._value('sliderCrossSection', 50)}%")
            return

        stacked = np.vstack([
            np.column_stack([
                df["x"].to_numpy(dtype=float),
                df["y"].to_numpy(dtype=float),
                df["tvd"].to_numpy(dtype=float) * vertical_exag,
            ])
            for df in trajectories.values()
        ])
        mins     = stacked.min(axis=0)
        maxs     = stacked.max(axis=0)
        position = self._value("sliderCrossSection", 50) / 100.0
        self._set_text("lblCrossSectionVal", f"{int(position * 100)}%")

        res = 2
        if cross_section in {"X-Plane", "Custom"}:
            xv = mins[0] + position * (maxs[0] - mins[0])
            y  = np.linspace(mins[1], maxs[1], res)
            z  = np.linspace(mins[2], maxs[2], res)
            yy, zz = np.meshgrid(y, z)
            xx = np.full_like(yy, xv)
        elif cross_section == "Y-Plane":
            yv = mins[1] + position * (maxs[1] - mins[1])
            x  = np.linspace(mins[0], maxs[0], res)
            z  = np.linspace(mins[2], maxs[2], res)
            xx, zz = np.meshgrid(x, z)
            yy = np.full_like(xx, yv)
        else:
            zv = mins[2] + position * (maxs[2] - mins[2])
            x  = np.linspace(mins[0], maxs[0], res)
            y  = np.linspace(mins[1], maxs[1], res)
            xx, yy = np.meshgrid(x, y)
            zz = np.full_like(xx, zv)

        ax.plot_surface(xx, yy, zz,
                        color="#5AAED0", alpha=0.08,
                        linewidth=0, antialiased=False)
        # cross-section edge outline
        ax.plot_wireframe(xx, yy, zz,
                          color="#3A7EA8", alpha=0.30,
                          linewidth=0.6, rstride=1, cstride=1)

    # ------------------------------------------------------------------ #
    #  Well data access                                                     #
    # ------------------------------------------------------------------ #

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
            controller   = getattr(self.window, "controller", None)
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
            current      = (
                getattr(data_service, "_current_well", None)
                if data_service is not None else None
            )
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
        self._selected_names = (
            [name for name in previous if name in well_names]
            or (well_names[:1] if well_names else [])
        )

    def _select_all_wells(self) -> None:
        list_widget = self._widget("listWells")
        if list_widget is None:
            return
        list_widget.selectAll()
        self._selected_names = [
            list_widget.item(i).text() for i in range(list_widget.count())
        ]
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
        if (
            data_service is not None
            and getattr(data_service, "_current_well", None) != selected_names[0]
        ):
            data_service._current_well = selected_names[0]
        self.refresh()

    def _sync_depth_slider_ranges(self, trajectories: dict[str, pd.DataFrame]) -> None:
        min_tvd = min(float(df["tvd"].min()) for df in trajectories.values())
        max_tvd = max(float(df["tvd"].max()) for df in trajectories.values())
        slider_min = self._widget("sliderDepthMin")
        slider_max = self._widget("sliderDepthMax")
        if slider_min is None or slider_max is None:
            return
        lower   = int(np.floor(min_tvd))
        upper   = int(np.ceil(max_tvd))
        if upper <= lower:
            upper = lower + 1
        cur_min = max(lower, min(slider_min.value(), upper))
        cur_max = max(cur_min + 1, min(slider_max.value(), upper))
        for slider, value in ((slider_min, cur_min), (slider_max, cur_max)):
            slider.blockSignals(True)
            slider.setMinimum(lower)
            slider.setMaximum(upper)
            slider.setValue(value)
            slider.blockSignals(False)
        self._update_slider_labels()

    def _clip_trajectories(
        self, trajectories: dict[str, pd.DataFrame]
    ) -> dict[str, pd.DataFrame]:
        depth_min = self._value("sliderDepthMin", 0)
        depth_max = self._value("sliderDepthMax", 5000)
        if depth_min > depth_max:
            depth_min, depth_max = depth_max, depth_min
        clipped: dict[str, pd.DataFrame] = {}
        for name, traj in trajectories.items():
            window = traj[
                (traj["tvd"] >= depth_min) & (traj["tvd"] <= depth_max)
            ].copy()
            if not window.empty:
                clipped[name] = window.reset_index(drop=True)
        return clipped

    # ------------------------------------------------------------------ #
    #  Colour helpers                                                        #
    # ------------------------------------------------------------------ #

    def _color_values_for_plot(self, trajectory: pd.DataFrame, color_mode: str):
        from matplotlib import colors

        if color_mode == "Well (Unique)":
            return None, None, False
        if color_mode == "Formation Zone":
            bins = np.linspace(
                float(trajectory["tvd"].min()), float(trajectory["tvd"].max()), 5
            )
            return (
                np.digitize(trajectory["tvd"].to_numpy(dtype=float), bins, right=True),
                colors.Normalize(vmin=0, vmax=4),
                True,
            )
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
        finite   = values[np.isfinite(values)]
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

    # ------------------------------------------------------------------ #
    #  Trajectory / curve building                                          #
    # ------------------------------------------------------------------ #

    def _attach_curve_columns(self, well, trajectory: pd.DataFrame) -> pd.DataFrame:
        df = getattr(well, "data", None)
        if df is None or getattr(df, "empty", True):
            return trajectory
        result = trajectory.copy()
        property_aliases = {
            "GR":            ("GR", "GAMMA", "GAMMARAY"),
            "RHOB":          ("RHOB", "RHOZ", "DEN", "DENSITY"),
            "NPHI":          ("NPHI", "NPHI_LS", "NEUT", "NEUTRON"),
            "RT":            ("RT", "ILD", "ILM", "LLD", "RDEP", "RESD"),
            "VSHALE":        ("VSHALE", "VSH"),
            "PHIE":          ("PHIE", "PHI", "POR", "EFFECTIVEPOROSITY"),
            "SW":            ("SW", "SATW", "WATERSATURATION"),
            "PERMEABILITYK": ("PERMEABILITY", "PERM", "K"),
            "NETPAYFLAG":    ("NETPAY", "PAYFLAG", "PAY", "NETPAYFLAG"),
        }
        for target, aliases in property_aliases.items():
            series = self._interpolate_curve(df, aliases, result["md"].to_numpy(dtype=float))
            if series is not None:
                result[target] = series

        selected_labels = {
            self._current_text("cmbOverlayCurve", ""),
            self._current_text("cmbCmapProperty", ""),
        }
        for label in filter(None, selected_labels):
            token = self._property_token(label)
            if token in result:
                continue
            series = self._interpolate_curve(df, (label,), result["md"].to_numpy(dtype=float))
            if series is not None:
                result[token] = series
        return result

    def _build_trajectory(self, well):
        df = getattr(well, "data", None)
        if df is None or getattr(df, "empty", True):
            return None, "No well data available"

        trajectory = pd.DataFrame()
        md_col  = self._match_column(df, "MD", "DEPTH", "DEPT", "MEASUREDDEPTH")
        tvd_col = self._match_column(df, "TVD", "TVDSS", "TRUEVERTICALDEPTH")
        x_col   = self._match_column(df, "X", "XCOORD", "XCOORDINATE", "EASTING", "UTMX")
        y_col   = self._match_column(df, "Y", "YCOORD", "YCOORDINATE", "NORTHING", "UTMY")
        dev_col = self._match_column(df, "DEVIATION", "DEVI", "DEV", "INC", "INCLINATION")
        azi_col = self._match_column(df, "AZIMUTH", "AZI", "AZM")

        if md_col is not None:
            trajectory["md"] = pd.to_numeric(df[md_col], errors="coerce")
            notes = [f"MD from '{md_col}'"]
        else:
            trajectory["md"] = np.arange(len(df), dtype=float)
            notes = ["MD synthesized from sample index"]

        for key, column in (
            ("tvd",       tvd_col),
            ("x",         x_col),
            ("y",         y_col),
            ("deviation", dev_col),
            ("azimuth",   azi_col),
        ):
            if column is not None:
                trajectory[key] = pd.to_numeric(df[column], errors="coerce")

        trajectory = (
            trajectory
            .dropna(subset=["md"])
            .sort_values("md")
            .drop_duplicates("md")
            .reset_index(drop=True)
        )
        if trajectory.empty:
            return None, "No numeric depth values were found"

        delta_md = trajectory["md"].diff().fillna(0.0).clip(lower=0.0).to_numpy()

        if "tvd" in trajectory:
            trajectory["tvd"] = (
                trajectory["tvd"].interpolate(limit_direction="both").bfill().ffill()
            )
            trajectory["tvd"] -= float(trajectory["tvd"].iloc[0])
            notes.append(f"TVD from '{tvd_col}'")
        elif "deviation" in trajectory:
            deviation_rad     = np.radians(trajectory["deviation"].fillna(0.0).to_numpy())
            trajectory["tvd"] = np.cumsum(delta_md * np.cos(deviation_rad))
            notes.append(f"TVD estimated from '{dev_col}'")
        else:
            trajectory["tvd"] = trajectory["md"] - float(trajectory["md"].iloc[0])
            notes.append("Vertical TVD assumption from measured depth")

        if "x" in trajectory and "y" in trajectory:
            trajectory["x"] = (
                trajectory["x"].interpolate(limit_direction="both").bfill().ffill()
            )
            trajectory["y"] = (
                trajectory["y"].interpolate(limit_direction="both").bfill().ffill()
            )
            trajectory["x"] -= float(trajectory["x"].iloc[0])
            trajectory["y"] -= float(trajectory["y"].iloc[0])
            notes.append(f"Plan view from '{x_col}' and '{y_col}'")
        elif "deviation" in trajectory and "azimuth" in trajectory:
            deviation_rad = np.radians(trajectory["deviation"].fillna(0.0).to_numpy())
            azimuth_rad   = np.radians(trajectory["azimuth"].fillna(0.0).to_numpy())
            lateral       = delta_md * np.sin(deviation_rad)
            trajectory["x"] = np.cumsum(lateral * np.sin(azimuth_rad))
            trajectory["y"] = np.cumsum(lateral * np.cos(azimuth_rad))
            notes.append(f"Lateral offsets from '{dev_col}' and '{azi_col}'")
        else:
            trajectory["x"] = 0.0
            trajectory["y"] = 0.0
            notes.append("Vertical well path assumed")

        if "deviation" not in trajectory:
            dx = np.diff(trajectory["x"].to_numpy(dtype=float),
                         prepend=float(trajectory["x"].iloc[0]))
            dy = np.diff(trajectory["y"].to_numpy(dtype=float),
                         prepend=float(trajectory["y"].iloc[0]))
            dz = np.diff(trajectory["tvd"].to_numpy(dtype=float),
                         prepend=float(trajectory["tvd"].iloc[0]))
            lateral  = np.sqrt(dx**2 + dy**2)
            vertical = np.maximum(np.abs(dz), 1e-9)
            trajectory["deviation"] = np.degrees(np.arctan2(lateral, vertical))
        else:
            trajectory["deviation"] = trajectory["deviation"].ffill().fillna(0.0)

        return trajectory, " | ".join(notes)

    def _match_column(self, df: pd.DataFrame, *aliases: str) -> str | None:
        lookup: dict[str, str] = {}
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

    def _interpolate_curve(
        self,
        df: pd.DataFrame,
        aliases: tuple[str, ...],
        target_md: np.ndarray,
    ) -> np.ndarray | None:
        curve_col = self._match_column(df, *aliases)
        if curve_col is None:
            return None
        md_col = self._match_column(df, "MD", "DEPTH", "DEPT", "MEASUREDDEPTH")
        if md_col is None:
            source_md = np.arange(len(df), dtype=float)
        else:
            source_md = pd.to_numeric(df[md_col], errors="coerce").to_numpy(dtype=float)
        values = pd.to_numeric(df[curve_col], errors="coerce").to_numpy(dtype=float)
        mask   = np.isfinite(source_md) & np.isfinite(values)
        if mask.sum() < 2:
            return None
        source_md = source_md[mask]
        values    = values[mask]
        order     = np.argsort(source_md)
        return np.interp(
            target_md,
            source_md[order],
            values[order],
            left=np.nan,
            right=np.nan,
        )

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
        defaults  = ["GR", "RHOB", "NPHI", "RT", "VSHALE", "PHIE", "SW",
                     "PERMEABILITY", "NETPAYFLAG"]
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

    # ------------------------------------------------------------------ #
    #  Property name helpers                                                #
    # ------------------------------------------------------------------ #

    def _property_name_from_color_mode(self, color_mode: str) -> str:
        mapping = {
            "Log Curve":        self._current_property_name(),
            "Vshale":           "VSHALE",
            "Porosity (PHIE)":  "PHIE",
            "Water Sat. (Sw)":  "SW",
            "Permeability (K)": "PERMEABILITYK",
            "Net Pay Flag":     "NETPAYFLAG",
        }
        return mapping.get(color_mode, self._current_property_name())

    def _current_property_name(self) -> str:
        text = self._current_text(
            "cmbCmapProperty",
            self._current_text("cmbOverlayCurve", "GR"),
        )
        return self._property_token(text)

    def _current_overlay_property_name(self) -> str:
        text = self._current_text(
            "cmbOverlayCurve",
            self._current_text("cmbCmapProperty", "GR"),
        )
        return self._property_token(text)

    def _property_token(self, text: str) -> str:
        normalized = self._normalize(text)
        mapping = {
            "GR":             "GR",
            "RHOB":           "RHOB",
            "NPHI":           "NPHI",
            "RTILD":          "RT",
            "RT":             "RT",
            "VSHALE":         "VSHALE",
            "PHIE":           "PHIE",
            "POROSITYPHIE":   "PHIE",
            "WATERSATSW":     "SW",
            "SW":             "SW",
            "PERMEABILITYK":  "PERMEABILITYK",
            "NETPAYFLAG":     "NETPAYFLAG",
        }
        return mapping.get(normalized, normalized)

    def _infer_formation_label(self, tvd: float) -> str:
        if not np.isfinite(tvd):
            return "--"
        if tvd < 500:
            return "Shallow  (<500 m)"
        if tvd < 1500:
            return "Intermediate  (500–1500 m)"
        if tvd < 3000:
            return "Reservoir  (1500–3000 m)"
        return "Deep  (>3000 m)"

    # ------------------------------------------------------------------ #
    #  Style helpers                                                         #
    # ------------------------------------------------------------------ #

    def _line_style_from_ui(self, text: str) -> tuple[str, float]:
        if text == "Line":
            return "-", 1.0
        if text == "Ribbon":
            return "-", 1.6
        if text == "Dotted / Dashed":
            return "--", 0.9
        return "-", 1.4

    def _well_palette(self, index: int) -> str:
        # Carefully chosen palette with good contrast on dark backgrounds
        palette = [
            "#4DC8E8",   # ice blue
            "#85D96B",   # soft green
            "#F5A623",   # amber
            "#E86262",   # warm red
            "#B57BFF",   # lavender
            "#F5E642",   # yellow
            "#FF8A3D",   # orange
            "#4FD1C5",   # teal
            "#C0A080",   # sandy
        ]
        return palette[index % len(palette)]

    def _matplotlib_cmap_name(self, text: str) -> str:
        mapping = {
            "Rainbow":        "rainbow",
            "Jet":            "jet",
            "Viridis":        "viridis",
            "Plasma":         "plasma",
            "Inferno":        "inferno",
            "Hot":            "hot",
            "RdYlGn":         "RdYlGn",
            "Seismic":        "seismic",
            "Petro (Custom)": "turbo",
            "Magma":          "magma",
            "Cividis":        "cividis",
        }
        cmap = mapping.get(text, "viridis")
        if self._is_checked("chkInvertCmap", False):
            return f"{cmap}_r"
        return cmap

    def _background_mode(self) -> str:
        if self._is_checked("rdoBgLight",    False):
            return "light"
        if self._is_checked("rdoBgGradient", False):
            return "gradient"
        return "dark"

    def _background_palette(self, mode: str) -> tuple[str, str, str, str]:
        if mode == "light":
            return "#EEF4FB", "#F8FCFF", "#112233", "#B0C8DE"
        if mode == "gradient":
            return "#09152A", "#0F1E36", "#C8DCF0", "#3E5A72"
        # dark (default) — deep navy
        return "#050D1A", "#050D1A", "#C8DCF0", "#263D55"

    def _camera_status_text(self) -> str:
        return (
            f"{self._projection_label}  |  "
            f"Az {self._value('sliderAzimuth', 45)}°  "
            f"El {self._value('sliderElevation', 30)}°  |  "
            f"Zoom {self._value('sliderZoom', 100)}%"
        )

    def _update_status_renderer(self) -> None:
        ambient  = self._value("sliderAmbient",  40)
        diffuse  = self._value("sliderDiffuse",  70)
        specular = self._value("sliderSpecular", 25)
        shadows  = " + Shadows" if self._is_checked("chkShadows", False) else ""
        self._set_text(
            "lblStatusRenderer",
            f"Renderer: Matplotlib 3D  |  Tube Engine  |  Phong {ambient}/{diffuse}/{specular}{shadows}",
        )

    def _update_slider_labels(self) -> None:
        self._set_text("lblDepthMinVal",     str(self._value("sliderDepthMin", 0)))
        self._set_text("lblDepthMaxVal",     str(self._value("sliderDepthMax", 5000)))
        self._set_text("lblVExagVal",        f"{self._value('sliderVExag', 1)}x")
        self._set_text("lblCrossSectionVal", f"{self._value('sliderCrossSection', 50)}%")
        self._set_text("lblTrajRadiusVal",   f"{self._value('sliderTrajRadius', 5)} px")
        opacity_pct      = self._value("sliderOpacity", 100)
        transparency_pct = max(0, 100 - opacity_pct)
        self._set_text("lblOpacityVal",      f"{transparency_pct}%")
        self._set_text("lblAzimuthVal",      f"{self._value('sliderAzimuth', 45)}°")
        self._set_text("lblElevationVal",    f"{self._value('sliderElevation', 30)}°")
        self._set_text("lblFOVVal",          f"{self._value('sliderFOV', 60)}°")
        self._set_text("lblZoomVal",         f"{self._value('sliderZoom', 100)}%")
        self._set_text("lblAmbientVal",      f"{self._value('sliderAmbient', 40)}%")
        self._set_text("lblDiffuseVal",      f"{self._value('sliderDiffuse', 70)}%")
        self._set_text("lblSpecularVal",     f"{self._value('sliderSpecular', 25)}%")
        self._set_text("lblStatusCamera",    self._camera_status_text())

    def _advance_animation(self) -> None:
        slider     = self._widget("sliderDepthMax")
        slider_min = self._widget("sliderDepthMin")
        if slider is None or slider_min is None:
            self.stop_animation()
            return
        step       = max(1, int((slider.maximum() - slider.minimum()) / 60))
        next_value = slider.value() + step
        if next_value > slider.maximum():
            next_value = max(slider_min.value() + step, slider.minimum())
        slider.setValue(next_value)

    # ------------------------------------------------------------------ #
    #  Status / label helpers                                               #
    # ------------------------------------------------------------------ #

    def _reset_pick_labels(self) -> None:
        for name, text in (
            ("lblPickWell",        "--"),
            ("lblPickMD",          "--"),
            ("lblPickTVD",         "--"),
            ("lblPickTVDSS",       "--"),
            ("lblPickFormation",   "--"),
            ("lblPickGR",          "--  API"),
            ("lblPickRHOB",        "--  g/cc"),
            ("lblPickNPHI",        "--  v/v"),
            ("lblPickVsh",         "--  v/v"),
            ("lblPickPHIE",        "--  v/v"),
            ("lblPickSw",          "--  v/v"),
            ("lblPickK",           "--  mD"),
            ("lblPickNetPay",      "--"),
            ("lblCursorX",         "X: --"),
            ("lblCursorY",         "Y: --"),
            ("lblCursorTVD",       "TVD (m): --"),
            ("lblCursorMD",        "MD (m): --"),
            ("lblPickedWell",      "--"),
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
            "lblPickGR":     " API",
            "lblPickRHOB":   " g/cc",
            "lblPickNPHI":   " v/v",
            "lblPickVsh":    " v/v",
            "lblPickPHIE":   " v/v",
            "lblPickSw":     " v/v",
            "lblPickK":      " mD",
            "lblPickNetPay": "",
        }
        return suffixes.get(label_name, "")

    @staticmethod
    def _normalize(value: str) -> str:
        return "".join(ch for ch in str(value).upper() if ch.isalnum())
