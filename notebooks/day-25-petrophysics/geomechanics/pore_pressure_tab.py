import os
import numpy as np
import pandas as pd
from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

# ---------------------------------------------------------
# UI STYLING CONSTANTS (Matching PetroARX Light Theme)
# ---------------------------------------------------------

STYLE_FRAME = """
    QFrame#PanelFrame {
        background-color: #F8F9FA;
        border: 1px solid #D0D7E5;
        border-radius: 4px;
    }
"""

STYLE_HEADER = """
    QLabel#PanelHeader {
        background-color: #1a4276;
        color: #FFFFFF;
        font-weight: bold;
        font-size: 13px;
        padding: 8px;
        border-top-left-radius: 3px;
        border-top-right-radius: 3px;
    }
"""

STYLE_BTN_GREEN = """
    QPushButton {
        background-color: #2F9E74;
        color: #FFFFFF;
        border: none;
        border-radius: 3px;
        padding: 8px 12px;
        font-weight: bold;
    }
    QPushButton:hover { background-color: #26825f; }
    QPushButton:pressed { background-color: #1b6146; }
"""

STYLE_BTN_LIGHT = """
    QPushButton {
        background-color: #FFFFFF;
        color: #1a4276;
        border: 1px solid #1a4276;
        border-radius: 3px;
        padding: 8px 12px;
        font-weight: bold;
    }
    QPushButton:hover { background-color: #EAF0F6; }
"""

STYLE_BTN_BLUE = """
    QPushButton {
        background-color: #316BB5;
        color: #FFFFFF;
        border: none;
        border-radius: 3px;
        padding: 5px 10px;
        font-weight: bold;
    }
    QPushButton:hover { background-color: #2b5d9e; }
"""

STYLE_BTN_OUTLINE = """
    QPushButton {
        background-color: #FFFFFF;
        color: #333333;
        border: 1px solid #C2D0E0;
        border-radius: 3px;
        padding: 5px 10px;
    }
    QPushButton:hover { background-color: #EDF1F5; }
"""

STYLE_TABLE = """
    QTableWidget {
        background-color: #FFFFFF;
        alternate-background-color: #F8F9FA;
        gridline-color: #E2E8F0;
        selection-background-color: #D3E3F5;
        selection-color: #000000;
        border: 1px solid #D0D7E5;
        font-size: 11px;
    }
    QHeaderView::section {
        background-color: #FFFFFF;
        border: 1px solid #D0D7E5;
        border-top: none;
        border-left: none;
        padding: 4px;
        font-weight: bold;
        color: #4A5568;
    }
"""

class PPViewerEngine(QtWidgets.QWidget):
    """PyQtGraph based engine for Pore Pressure Plots"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        pg.setConfigOptions(antialias=True)
        pg.setConfigOption('background', '#FFFFFF')
        pg.setConfigOption('foreground', '#333333')
        
        self.canvas = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.canvas)
        
        # Plot 1: Pore Pressure Profile
        self.p1 = self.canvas.addPlot(title="Pore Pressure Profile", col=0)
        self.p1.setLabel('left', "Depth (m)")
        self.p1.setLabel('bottom', "Pressure (psi)")
        self.p1.invertY(True)
        self.p1.showGrid(x=True, y=True, alpha=0.3)
        self.p1.addLegend(offset=(10, 10))
        
        # Plot 2: Overburden vs Hydrostatic
        self.p2 = self.canvas.addPlot(title="Overburden vs Hydrostatic", col=1)
        self.p2.setLabel('left', "Depth (m)")
        self.p2.setLabel('bottom', "Pressure (psi)")
        self.p2.invertY(True)
        self.p2.showGrid(x=True, y=True, alpha=0.3)
        self.p2.addLegend(offset=(10, 10))
        
        # Plot 3: Effective Stress plot
        self.p3 = self.canvas.addPlot(title="Effective Stress", col=2)
        self.p3.setLabel('left', "Depth (m)")
        self.p3.setLabel('bottom', "σ' (psi)")
        self.p3.invertY(True)
        self.p3.showGrid(x=True, y=True, alpha=0.3)
        self.p3.addLegend(offset=(10, 10))
        
        # Link Y axes
        self.p2.setYLink(self.p1)
        self.p3.setYLink(self.p1)
        
        # Data items
        self.curve_pp = None
        self.curve_ph1 = None
        self.curve_sv1 = None
        
        self.curve_sv2 = None
        self.curve_ph2 = None
        
        self.curve_eff = None
        self.fill_region = None
        
    def plot_data(self, df):
        self.p1.clear()
        self.p2.clear()
        self.p3.clear()
        
        if 'Depth' not in df.columns or df.empty:
            return
            
        depth = df['Depth'].values
        
        # Plot 1
        pp = df['Pp'].values if 'Pp' in df else np.zeros_like(depth)
        ph = df['Ph'].values if 'Ph' in df else np.zeros_like(depth)
        sv = df['Sv'].values if 'Sv' in df else np.zeros_like(depth)
        
        self.curve_pp = self.p1.plot(pp, depth, pen=pg.mkPen('#0000FF', width=2), name="Pore Pressure (Pp)")
        self.curve_ph1 = self.p1.plot(ph, depth, pen=pg.mkPen('#0000FF', width=1.5, style=QtCore.Qt.DashLine), name="Hydrostatic (Ph)")
        self.curve_sv1 = self.p1.plot(sv, depth, pen=pg.mkPen('#FF0000', width=1.5, style=QtCore.Qt.DashLine), name="Overburden (Sv)")
        
        # Shade overpressure zone if Pp > Ph
        fill_x1 = np.maximum(pp, ph)
        self.fill1 = pg.FillBetweenItem(self.curve_ph1, self.curve_pp, brush=pg.mkBrush(255, 0, 0, 50))
        self.p1.addItem(self.fill1)
        
        # Text alarms where differences are large
        if 'KickRisk' in df and len(df[df['KickRisk']]) > 0:
            kr_depths = df[df['KickRisk']]['Depth'].values
            if len(kr_depths) > 0:
                mid_kr = kr_depths[len(kr_depths)//2]
                val = np.interp(mid_kr, depth, pp)
                txt = pg.TextItem("High Overpressure\nKick Risk!", color=(255,0,0), anchor=(0, 0.5))
                self.p1.addItem(txt)
                txt.setPos(val, mid_kr)
        
        # Plot 2
        self.curve_sv2 = self.p2.plot(sv, depth, pen=pg.mkPen('#FF0000', width=2), name="Overburden (Sv)")
        self.curve_ph2 = self.p2.plot(ph, depth, pen=pg.mkPen('#0000FF', width=1.5, style=QtCore.Qt.DashLine), name="Hydrostatic (Ph)")
        
        # Plot 3
        eff = df['Effective_Stress'].values if 'Effective_Stress' in df else (sv - pp)
        self.curve_eff = self.p3.plot(eff, depth, pen=pg.mkPen('#00A050', width=2), name="Effective Stress (σ' = Sv - Pp)")

class PorePressureTab(QtWidgets.QWidget):
    """Main Pore Pressure Analysis Module"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data_service = None
        self.current_df = None
        self.setStyleSheet("QWidget { font-family: 'Segoe UI', Arial; font-size: 12px; color: #333333; background-color: #EDF1F5; }")
        self.init_ui()
        
    def set_data_service(self, data_service) -> None:
        self._data_service = data_service
        self._refresh_data()
        
    def _refresh_data(self):
        if self._data_service:
            well = self._data_service._get_current_well()
            if well and well.data is not None:
                self.current_df = well.data.copy()
                cols = list(self.current_df.columns)
                self._update_combo(self.cmb_depth, cols, ['DEPT', 'DEPTH', 'MD'])
                self._update_combo(self.cmb_rhob, cols, ['RHOB', 'ROB', 'DEN'])
                self._update_combo(self.cmb_dt, cols, ['DT', 'DTC', 'AC'])
                self._update_combo(self.cmb_rt, ["(Optional)"] + cols, ['RT', 'RES', 'ILD'])
                
                # Update depth ranges
                depth_col = self.cmb_depth.currentText()
                if depth_col in self.current_df:
                    dep = pd.to_numeric(self.current_df[depth_col], errors='coerce').dropna()
                    if not dep.empty:
                        self.txt_from.setText(f"{dep.min():.0f}")
                        self.txt_to.setText(f"{dep.max():.0f}")

    def _update_combo(self, combo, items, preferred):
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(items)
        for pref in preferred:
            for i in range(combo.count()):
                if pref.upper() == combo.itemText(i).upper():
                    combo.setCurrentIndex(i)
                    break
        combo.blockSignals(False)

    def init_ui(self):
        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(8)
        
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.main_layout.addWidget(self.splitter)
        
        self._build_left_sidebar()
        self._build_right_area()
        
        self.splitter.setSizes([320, 1100])

    def _build_panel_frame(self, title):
        frame = QtWidgets.QFrame()
        frame.setObjectName("PanelFrame")
        frame.setStyleSheet(STYLE_FRAME)
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        header = QtWidgets.QLabel(title)
        header.setObjectName("PanelHeader")
        header.setStyleSheet(STYLE_HEADER)
        layout.addWidget(header)
        
        content = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(10)
        layout.addWidget(content)
        
        return frame, content_layout

    def _build_left_sidebar(self):
        self.left_sidebar = QtWidgets.QWidget()
        self.left_sidebar.setMinimumWidth(300)
        self.left_sidebar.setMaximumWidth(380)
        l_layout = QtWidgets.QVBoxLayout(self.left_sidebar)
        l_layout.setContentsMargins(0, 0, 0, 0)
        l_layout.setSpacing(12)
        
        # Panel
        ctrl_frame, ctrl_layout = self._build_panel_frame("PORE PRESSURE ANALYSIS")
        
        # 1. Curve Selection
        ctrl_layout.addWidget(self._make_section_title("1. Curve Selection"))
        grid1 = QtWidgets.QGridLayout()
        grid1.setSpacing(8)
        
        grid1.addWidget(QtWidgets.QLabel("Depth:"), 0, 0)
        self.cmb_depth = QtWidgets.QComboBox(); self.cmb_depth.addItems(['DEPT'])
        self.cmb_depth.setStyleSheet("background:white;")
        grid1.addWidget(self.cmb_depth, 0, 1)
        
        grid1.addWidget(QtWidgets.QLabel("Density (pb):"), 1, 0)
        self.cmb_rhob = QtWidgets.QComboBox(); self.cmb_rhob.addItems(['RHOB'])
        self.cmb_rhob.setStyleSheet("background:white;")
        grid1.addWidget(self.cmb_rhob, 1, 1)
        
        grid1.addWidget(QtWidgets.QLabel("Sonic (Δt):"), 2, 0)
        self.cmb_dt = QtWidgets.QComboBox(); self.cmb_dt.addItems(['DT'])
        self.cmb_dt.setStyleSheet("background:white;")
        grid1.addWidget(self.cmb_dt, 2, 1)
        
        grid1.addWidget(QtWidgets.QLabel("Resistivity (Rt):"), 3, 0)
        self.cmb_rt = QtWidgets.QComboBox(); self.cmb_rt.addItems(['RT (Optional)'])
        self.cmb_rt.setStyleSheet("background:white;")
        grid1.addWidget(self.cmb_rt, 3, 1)
        ctrl_layout.addLayout(grid1)
        
        # 2. Method & Parameters
        ctrl_layout.addWidget(self._make_section_title("2. Method & Parameters"))
        grid2 = QtWidgets.QGridLayout()
        grid2.setSpacing(8)
        
        grid2.addWidget(QtWidgets.QLabel("Method:"), 0, 0)
        self.cmb_method = QtWidgets.QComboBox(); self.cmb_method.addItems(['Eaton (Sonic)', 'Bowers (Sonic)', 'Eaton (Resistivity)'])
        self.cmb_method.setStyleSheet("background:white;")
        grid2.addWidget(self.cmb_method, 0, 1)
        
        grid2.addWidget(QtWidgets.QLabel("Eaton Exponent (n):"), 1, 0)
        self.spn_eaton = QtWidgets.QDoubleSpinBox(); self.spn_eaton.setValue(3.00)
        self.spn_eaton.setStyleSheet("background:white;")
        grid2.addWidget(self.spn_eaton, 1, 1)
        
        grid2.addWidget(QtWidgets.QLabel("Normal Compaction Trend (NCT):"), 2, 0, 1, 2)
        vbox_nct = QtWidgets.QVBoxLayout()
        self.rad_nct_auto = QtWidgets.QRadioButton("Auto - Rolling Average"); self.rad_nct_auto.setChecked(True)
        self.rad_nct_manual = QtWidgets.QRadioButton("Manual - Specify Points")
        vbox_nct.addWidget(self.rad_nct_auto)
        vbox_nct.addWidget(self.rad_nct_manual)
        grid2.addLayout(vbox_nct, 3, 0, 1, 2)
        
        grid2.addWidget(QtWidgets.QLabel("NCT Window (m):"), 4, 0)
        self.spn_window = QtWidgets.QSpinBox(); self.spn_window.setValue(50); self.spn_window.setMaximum(1000)
        self.spn_window.setStyleSheet("background:white;")
        grid2.addWidget(self.spn_window, 4, 1)
        
        grid2.addWidget(QtWidgets.QLabel("Mud Weight (ppg):"), 5, 0)
        self.spn_mw = QtWidgets.QDoubleSpinBox(); self.spn_mw.setValue(12.50)
        self.spn_mw.setStyleSheet("background:white;")
        grid2.addWidget(self.spn_mw, 5, 1)
        
        grid2.addWidget(QtWidgets.QLabel("Water Density (g/cc):"), 6, 0)
        self.spn_wd = QtWidgets.QDoubleSpinBox(); self.spn_wd.setValue(1.000); self.spn_wd.setDecimals(3)
        self.spn_wd.setStyleSheet("background:white;")
        grid2.addWidget(self.spn_wd, 6, 1)
        
        ctrl_layout.addLayout(grid2)
        
        # 3. Depth Range
        ctrl_layout.addWidget(self._make_section_title("3. Depth Range"))
        grid3 = QtWidgets.QGridLayout()
        grid3.setSpacing(8)
        
        grid3.addWidget(QtWidgets.QLabel("From (m):"), 0, 0)
        self.txt_from = QtWidgets.QLineEdit("3200"); self.txt_from.setStyleSheet("background:white;")
        grid3.addWidget(self.txt_from, 0, 1)
        
        grid3.addWidget(QtWidgets.QLabel("To (m):"), 1, 0)
        self.txt_to = QtWidgets.QLineEdit("4200"); self.txt_to.setStyleSheet("background:white;")
        grid3.addWidget(self.txt_to, 1, 1)
        
        ctrl_layout.addLayout(grid3)
        
        # Buttons
        ctrl_layout.addSpacing(10)
        self.btn_run = QtWidgets.QPushButton("Run Pore Pressure")
        self.btn_run.setStyleSheet(STYLE_BTN_GREEN)
        self.btn_run.clicked.connect(self.run_analysis)
        ctrl_layout.addWidget(self.btn_run)
        
        self.btn_reset = QtWidgets.QPushButton("Reset")
        self.btn_reset.setStyleSheet(STYLE_BTN_LIGHT)
        ctrl_layout.addWidget(self.btn_reset)
        
        ctrl_layout.addStretch()
        l_layout.addWidget(ctrl_frame)
        self.splitter.addWidget(self.left_sidebar)

    def _make_section_title(self, text):
        lbl = QtWidgets.QLabel(text)
        lbl.setStyleSheet("font-weight: bold; margin-top: 5px;")
        return lbl

    def _build_right_area(self):
        self.right_area = QtWidgets.QWidget()
        r_layout = QtWidgets.QVBoxLayout(self.right_area)
        r_layout.setContentsMargins(0, 0, 0, 0)
        r_layout.setSpacing(8)
        
        # Top Plot Panel
        plots_frame, plots_layout = self._build_panel_frame("PLOT RESULTS")
        self.viewer_engine = PPViewerEngine()
        plots_layout.addWidget(self.viewer_engine)
        r_layout.addWidget(plots_frame, 2) # Expand more
        
        # Bottom area: 3 sub-panels
        bottom_area = QtWidgets.QWidget()
        b_layout = QtWidgets.QHBoxLayout(bottom_area)
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setSpacing(8)
        
        # 1. Summary
        sum_frame, sum_layout = self._build_panel_frame("PORE PRESSURE SUMMARY")
        self.tbl_summary = QtWidgets.QTableWidget()
        self.tbl_summary.setColumnCount(2)
        self.tbl_summary.horizontalHeader().setVisible(False)
        self.tbl_summary.verticalHeader().setVisible(False)
        self.tbl_summary.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.tbl_summary.setStyleSheet(STYLE_TABLE)
        self.tbl_summary.setRowCount(6)
        sum_items = [
            ("Maximum Pore Pressure", "13,650 psi @ 4112 m"),
            ("Hydrostatic Pressure @ TD", "12,800 psi"),
            ("Overburden Stress @ TD", "18,920 psi"),
            ("Maximum Overpressure", "850 psi (6.6%)"),
            ("Depth of First Overpressure", "3568 m"),
            ("Kick Risk Zone", "3810 m - 4200 m")
        ]
        for i, (k, v) in enumerate(sum_items):
            self.tbl_summary.setItem(i, 0, QtWidgets.QTableWidgetItem(k))
            item_v = QtWidgets.QTableWidgetItem(v)
            if '850' in v or '3810' in v:
                item_v.setForeground(QtGui.QBrush(QtGui.QColor("red")))
                item_v.setFont(QtGui.QFont("Segoe UI", 9, QtGui.QFont.Bold))
            self.tbl_summary.setItem(i, 1, item_v)
        sum_layout.addWidget(self.tbl_summary)
        b_layout.addWidget(sum_frame, 1)
        
        # 2. Mud Window
        mud_frame, mud_layout = self._build_panel_frame("MUD WINDOW")
        self.tbl_mud = QtWidgets.QTableWidget()
        self.tbl_mud.setColumnCount(4)
        self.tbl_mud.setHorizontalHeaderLabels(["Depth (m)", "Pp (psi)", "Sv (psi)", "Safe Mud Weight (ppg)"])
        self.tbl_mud.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.tbl_mud.verticalHeader().setVisible(False)
        self.tbl_mud.setStyleSheet(STYLE_TABLE)
        self.tbl_mud.setRowCount(4)
        mud_data = [
            ("3200", "10,200", "14,850", "8.6 - 12.5"),
            ("3600", "11,950", "16,730", "10.1 - 14.1"),
            ("4000", "13,400", "18,250", "11.3 - 15.4"),
            ("4200", "13,650", "18,920", "11.5 - 16.0")
        ]
        for i, row in enumerate(mud_data):
            for j, val in enumerate(row):
                self.tbl_mud.setItem(i, j, QtWidgets.QTableWidgetItem(val))
        mud_layout.addWidget(self.tbl_mud)
        b_layout.addWidget(mud_frame, 1)
        
        # 3. Interpretation Notes
        notes_frame, notes_layout = self._build_panel_frame("INTERPRETATION NOTES")
        self.txt_notes = QtWidgets.QTextEdit()
        self.txt_notes.setReadOnly(True)
        self.txt_notes.setStyleSheet("border: 1px solid #D0D7E5; background: white; padding: 5px; color: #333333;")
        self.txt_notes.setHtml("<ul>"
                               "<li>Pore pressure begins to exceed hydrostatic around <b>3568 m</b>.</li>"
                               "<li>Significant overpressure detected between <b>3810</b> m and <b>4200</b> m.</li>"
                               "<li>Adjust mud weight above <b>13.5 ppg</b> below 4000 m to avoid kick.</li>"
                               "</ul>")
        notes_layout.addWidget(self.txt_notes)
        
        hbox_notes = QtWidgets.QHBoxLayout()
        btn_exp = QtWidgets.QPushButton("⬇ Export Results")
        btn_exp.setStyleSheet(STYLE_BTN_BLUE)
        btn_gen = QtWidgets.QPushButton("📄 Generate Report")
        btn_gen.setStyleSheet(STYLE_BTN_OUTLINE)
        hbox_notes.addWidget(btn_exp)
        hbox_notes.addWidget(btn_gen)
        notes_layout.addLayout(hbox_notes)
        b_layout.addWidget(notes_frame, 1)
        
        r_layout.addWidget(bottom_area, 1) # Take half space of plots
        
        self.splitter.addWidget(self.right_area)

    def run_analysis(self):
        """Perform mock/real calculations and update plots and tables."""
        if self.current_df is None or self.current_df.empty:
            df = self._generate_mock_data()
        else:
            try:
                df = self._run_eaton_calculation()
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Calculation Error", str(e))
                df = self._generate_mock_data()
        
        self.viewer_engine.plot_data(df)
        self._update_tables(df)
        
    def _run_eaton_calculation(self):
        """Simple Eaton method pore pressure calculation implementation."""
        # Grab configs
        depth_col = self.cmb_depth.currentText()
        rhob_col = self.cmb_rhob.currentText()
        dt_col = self.cmb_dt.currentText()
        
        df = self.current_df.copy()
        
        if depth_col not in df or rhob_col not in df or dt_col not in df:
            raise ValueError(f"Required columns ({depth_col}, {rhob_col}, {dt_col}) not found.")
            
        try:
            frm = float(self.txt_from.text())
            to = float(self.txt_to.text())
        except:
            frm, to = df[depth_col].min(), df[depth_col].max()
            
        df = df[(df[depth_col] >= frm) & (df[depth_col] <= to)].copy()
        
        # Unit conversion constants roughly
        water_density = self.spn_wd.value() # g/cc
        eaton_n = self.spn_eaton.value()
        
        # Ensure numeric
        depth = pd.to_numeric(df[depth_col], errors='coerce').interpolate().fillna(method='bfill')
        rhob = pd.to_numeric(df[rhob_col], errors='coerce').interpolate().fillna(method='bfill')
        dt = pd.to_numeric(df[dt_col], errors='coerce').interpolate().fillna(method='bfill')
        
        # 1. Overburden (Sv) in psi. Integration of density * 0.433
        # Since rhob is g/cc -> convert to psi/ft by * 0.433, then * depth in ft?
        # Let's assume Depth is in m, so depth * 3.28084 = ft
        depth_ft = depth * 3.28084
        # simple cumsum:
        d_depth_ft = depth_ft.diff().fillna(depth_ft.iloc[0])
        sv_psi = (rhob * 0.433 * d_depth_ft).cumsum()
        
        # 2. Hydrostatic (Ph) in psi
        ph_psi = water_density * 0.433 * depth_ft
        
        # 3. NCT for DT (Simple rolling average + shift or linear trend)
        dt_nct = dt.rolling(window=self.spn_window.value(), min_periods=1, center=True).mean() * 0.9
        
        # 4. Eaton Pore Pressure (Pp)
        # Pp = Sv - (Sv - Ph) * (dt_nct / dt)^n
        dt_ratio = dt_nct / dt
        # Clip ratio to avoid crazy values
        dt_ratio = dt_ratio.clip(lower=0.5, upper=1.5)
        pp_psi = sv_psi - (sv_psi - ph_psi) * (dt_ratio ** eaton_n)
        
        # Ensure Pp doesn't go below Ph
        pp_psi = np.maximum(pp_psi, ph_psi)
        
        res_df = pd.DataFrame({
            'Depth': depth,
            'Sv': sv_psi,
            'Ph': ph_psi,
            'Pp': pp_psi,
            'Effective_Stress': sv_psi - pp_psi
        })
        res_df['KickRisk'] = res_df['Pp'] > (res_df['Ph'] + 500)
        
        return res_df

    def _generate_mock_data(self):
        """Generate mock data analogous to the requested figure if data isn't clean."""
        depth = np.linspace(3200, 4200, 500)
        ph = depth * (1.0 * 0.433 * 3.28084) # Hydrostatic
        sv = depth * (2.4 * 0.433 * 3.28084) # Overburden approx
        
        # Normal compaction up to 3600m
        pp = ph.copy()
        
        # Overpressure starting at 3600
        ov_idx = depth > 3600
        pp[ov_idx] = ph[ov_idx] + (depth[ov_idx] - 3600) * 1.5 
        
        df = pd.DataFrame({
            'Depth': depth,
            'Pp': pp,
            'Ph': ph,
            'Sv': sv,
            'Effective_Stress': sv - pp
        })
        df['KickRisk'] = df['Pp'] > (df['Ph'] + 800)
        return df

    def _update_tables(self, df):
        if df.empty: return
        max_pp = df['Pp'].max()
        max_depth = df.loc[df['Pp'].idxmax(), 'Depth']
        
        ph_td = df['Ph'].iloc[-1]
        sv_td = df['Sv'].iloc[-1]
        
        overpressure = df['Pp'] - df['Ph']
        max_ov = overpressure.max()
        pct = (max_ov / max_pp * 100) if max_pp > 0 else 0
        
        op_zone = df[df['Pp'] > df['Ph'] + 10]
        first_op = op_zone['Depth'].iloc[0] if not op_zone.empty else "-"
        
        kr_zone = df[df['KickRisk']]
        if not kr_zone.empty:
            kr_str = f"{kr_zone['Depth'].min():.0f} m - {kr_zone['Depth'].max():.0f} m"
        else:
            kr_str = "None"
            
        sum_items = [
            (f"{max_pp:,.0f} psi @ {max_depth:.0f} m"),
            (f"{ph_td:,.0f} psi"),
            (f"{sv_td:,.0f} psi"),
            (f"{max_ov:,.0f} psi ({pct:.1f}%)"),
            (f"{first_op:.0f} m" if isinstance(first_op, float) else first_op),
            (kr_str)
        ]
        
        for i, v in enumerate(sum_items):
            item_v = QtWidgets.QTableWidgetItem(str(v))
            if i == 3 or i == 5:
                if 'None' not in str(v) and '-' not in str(v):
                    item_v.setForeground(QtGui.QBrush(QtGui.QColor("red")))
                    item_v.setFont(QtGui.QFont("Segoe UI", 9, QtGui.QFont.Bold))
            self.tbl_summary.setItem(i, 1, item_v)
