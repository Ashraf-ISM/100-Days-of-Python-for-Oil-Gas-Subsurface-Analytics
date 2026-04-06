import os
import sys
import numpy as np
import pandas as pd
import lasio
from pathlib import Path
from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import matplotlib.cm as cm

# ---------------------------------------------------------
# CONSTANTS & THEMING
# ---------------------------------------------------------
COLORS = {
    "bg_main": "#1A1D2E",
    "bg_panel": "#1E2235",
    "border": "#2A2F45",
    "accent_primary": "#00B4D8",
    "accent_secondary": "#0077B6",
    "text_primary": "#E8ECF0",
    "text_secondary": "#8B9BB4",
    "fracture": "#E63946",
    "bedding": "#FFD166",
    "fault": "#F4A261",
    "vugs": "#00FFFF"
}

QSS_THEME = f"""
QWidget {{
    background-color: {COLORS['bg_main']};
    color: {COLORS['text_primary']};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 10pt;
}}
QSplitter::handle {{
    background-color: {COLORS['border']};
    width: 2px;
}}
QGroupBox {{
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
    color: {COLORS['text_secondary']};
    background-color: {COLORS['bg_panel']};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    top: -6px;
    color: {COLORS['accent_primary']};
    background-color: {COLORS['bg_main']};
    padding: 0 4px;
}}
QPushButton {{
    background-color: {COLORS['bg_panel']};
    border: 1px solid {COLORS['border']};
    padding: 6px 12px;
    border-radius: 4px;
    color: {COLORS['text_primary']};
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: rgba(0, 180, 216, 0.12);
    border: 1px solid {COLORS['accent_primary']};
}}
QPushButton:pressed {{
    background-color: {COLORS['accent_secondary']};
    color: #fff;
}}
QPushButton[active="true"] {{
    border: 1px solid {COLORS['accent_primary']};
    background: rgba(0, 180, 216, 0.15);
    color: {COLORS['accent_primary']};
}}
QComboBox, QDoubleSpinBox, QSpinBox {{
    background-color: {COLORS['bg_main']};
    border: 1px solid {COLORS['border']};
    padding: 4px 8px;
    border-radius: 4px;
    color: {COLORS['text_primary']};
}}
QComboBox:hover, QDoubleSpinBox:hover, QSpinBox:hover {{
    border: 1px solid {COLORS['accent_primary']};
}}
QTableWidget {{
    background-color: {COLORS['bg_panel']};
    alternate-background-color: {COLORS['bg_main']};
    border: 1px solid {COLORS['border']};
    gridline-color: {COLORS['border']};
}}
QHeaderView::section {{
    background-color: {COLORS['bg_main']};
    color: {COLORS['text_secondary']};
    border: 1px solid {COLORS['border']};
    padding: 4px;
    font-weight: bold;
}}
QScrollBar:vertical {{
    border: none;
    background: {COLORS['bg_main']};
    width: 10px;
    margin: 0px 0px 0px 0px;
}}
QScrollBar::handle:vertical {{
    background: {COLORS['border']};
    min-height: 20px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLORS['text_secondary']};
}}
"""

# ---------------------------------------------------------
# UI COMPONENTS
# ---------------------------------------------------------
class ImageViewerEngine(QtWidgets.QWidget):
    """SECTION 1 - IMAGE VIEWER ENGINE"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Configure pyqtgraph global settings for a professional look
        pg.setConfigOptions(antialias=True)
        pg.setConfigOption('background', COLORS['bg_main'])
        pg.setConfigOption('foreground', COLORS['text_secondary'])
        
        self.canvas = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.canvas)
        
        # Setup Depth Plot (Left)
        self.depth_plot = self.canvas.addPlot(col=0)
        self.depth_plot.setMaximumWidth(80)
        self.depth_plot.setLabel('left', "Depth (MD)")
        self.depth_plot.hideAxis('bottom')
        self.depth_plot.invertY(True)
        self.depth_plot.setYRange(0, 100) # Default
        
        # Setup Image Plot (Right)
        self.img_plot = self.canvas.addPlot(col=1)
        self.img_plot.setLabel('bottom', "Azimuth (°)", units='')
        self.img_plot.getAxis('bottom').setTicks([[(0, '0'), (90, '90 E'), (180, '180 S'), (270, '270 W'), (360, '360')]])
        self.img_plot.setXRange(0, 360)
        self.img_plot.hideAxis('left') # Shared Y axis
        self.img_plot.invertY(True)
        
        # Link Y axes
        self.img_plot.setYLink(self.depth_plot)
        
        # Image Item
        self.image_item = pg.ImageItem()
        self.img_plot.addItem(self.image_item)
        
        self.set_colormap('hot_r')
        
    def set_colormap(self, cmap_name):
        try:
            cmap = cm.get_cmap(cmap_name)
            lut = (cmap(np.linspace(0.0, 1.0, 256)) * 255).astype(np.uint8)
            self.image_item.setLookupTable(lut)
        except Exception as e:
            print(f"Colormap error: {e}")
        
    def load_image(self, data, depth_start, depth_end):
        """Map numpy array physically to depth and azimuth via setRect."""
        # Clean infinite/nan
        data = np.nan_to_num(data, nan=np.nanmean(data))
        
        # pyqtgraph expects image as (x, y) not (y, x), so we transpose and rotate
        # But setRect handles coordinates easily.
        # Data shape should be (Depth, Azimuth) -> transpose for pyqtgraph (Azimuth, Depth)
        self.image_item.setImage(data.T, autoLevels=True)
        
        # Setting Rect: QRectF(x, y, width, height)
        # x=0, y=depth_start, w=360, h=(depth_end - depth_start)
        rect = QtCore.QRectF(0, depth_start, 360, depth_end - depth_start)
        self.image_item.setRect(rect)
        
        # Adjust view ranges
        self.depth_plot.setYRange(depth_start, depth_end)
        self.img_plot.setXRange(0, 360)

class ImageAnalysisTab(QtWidgets.QWidget):
    """Main Borehole Image Log Analysis Module"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(QSS_THEME)
        self.init_ui()
        
    def init_ui(self):
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.main_layout.setSpacing(12)
        
        self._build_toolbar()
        
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.main_layout.addWidget(self.splitter, stretch=1)
        
        self._build_left_panel()
        
        # Center Canvas
        self.viewer_engine = ImageViewerEngine()
        self.splitter.addWidget(self.viewer_engine)
        
        self._build_right_panel()
        
        self.splitter.setSizes([260, 900, 260])
        
        self._build_bottom_panel()
        
    def _build_toolbar(self):
        self.toolbar_layout = QtWidgets.QHBoxLayout()
        self.toolbar_layout.setSpacing(8)
        
        self.btn_load = QtWidgets.QPushButton("📂 Load Image...")
        self.btn_load.clicked.connect(self.prompt_load_image)
        self.btn_load.setToolTip("Load LAS or NumPy Image Array")
        
        self.lbl_cmap = QtWidgets.QLabel("Colormap:")
        self.lbl_cmap.setStyleSheet(f"color:{COLORS['text_secondary']}; font-weight:bold;")
        
        self.cmb_colormap = QtWidgets.QComboBox()
        self.cmb_colormap.addItems(["hot_r", "gray", "RdYlBu_r", "jet", "bone", "copper"])
        self.cmb_colormap.currentTextChanged.connect(self.change_colormap)
        
        self.btn_export = QtWidgets.QPushButton("💾 Export ▼")
        
        # Assemble
        self.toolbar_layout.addWidget(self.btn_load)
        self.toolbar_layout.addSpacing(16)
        self.toolbar_layout.addWidget(self.lbl_cmap)
        self.toolbar_layout.addWidget(self.cmb_colormap)
        self.toolbar_layout.addStretch()
        self.toolbar_layout.addWidget(self.btn_export)
        
        self.main_layout.addLayout(self.toolbar_layout)

    def _build_left_panel(self):
        self.left_panel = QtWidgets.QWidget()
        self.left_panel.setMinimumWidth(240)
        self.left_panel.setStyleSheet(f"background-color: {COLORS['bg_panel']}; border-radius: 8px;")
        layout = QtWidgets.QVBoxLayout(self.left_panel)
        
        # Well Info Group
        grp_info = QtWidgets.QGroupBox("WELL & IMAGE INFO")
        v_info = QtWidgets.QVBoxLayout(grp_info)
        self.lbl_well_name = QtWidgets.QLabel("Well: N/A")
        self.lbl_type = QtWidgets.QLabel("Type: N/A")
        self.lbl_depth_range = QtWidgets.QLabel("Depth: -")
        self.lbl_shape = QtWidgets.QLabel("Resolution: -")
        v_info.addWidget(self.lbl_well_name)
        v_info.addWidget(self.lbl_type)
        v_info.addWidget(self.lbl_depth_range)
        v_info.addWidget(self.lbl_shape)
        layout.addWidget(grp_info)
        
        # Tools Group
        grp_tools = QtWidgets.QGroupBox("INTERPRETATION TOOLS")
        v_tools = QtWidgets.QVBoxLayout(grp_tools)
        v_tools.setSpacing(6)
        
        self.btn_zoom = QtWidgets.QPushButton("🔍 Zoom / Pan")
        self.btn_zoom.setProperty("active", "true")
        self.btn_frac = QtWidgets.QPushButton("🪨 Fracture (F)")
        self.btn_bed = QtWidgets.QPushButton("📐 Bedding (B)")
        self.btn_vug = QtWidgets.QPushButton("🌊 Vugs (V)")
        self.btn_fault = QtWidgets.QPushButton("🚫 Fault (T)")
        
        v_tools.addWidget(self.btn_zoom)
        v_tools.addWidget(self.btn_frac)
        v_tools.addWidget(self.btn_bed)
        v_tools.addWidget(self.btn_vug)
        v_tools.addWidget(self.btn_fault)
        layout.addWidget(grp_tools)
        
        # Adjusting Sinusoid Fit
        grp_sin = QtWidgets.QGroupBox("MANUAL SINUSOID FIT")
        f_sin = QtWidgets.QFormLayout(grp_sin)
        self.spn_dip = QtWidgets.QDoubleSpinBox()
        self.spn_dip.setRange(0, 90)
        self.spn_dip.setSuffix(" °")
        self.spn_azi = QtWidgets.QDoubleSpinBox()
        self.spn_azi.setRange(0, 360)
        self.spn_azi.setSuffix(" °")
        f_sin.addRow("Dip:", self.spn_dip)
        f_sin.addRow("Azimuth:", self.spn_azi)
        btn_preview = QtWidgets.QPushButton("Preview Fit")
        f_sin.addRow("", btn_preview)
        layout.addWidget(grp_sin)
        
        layout.addStretch()
        self.splitter.addWidget(self.left_panel)

    def _build_right_panel(self):
        self.right_panel = QtWidgets.QWidget()
        self.right_panel.setMinimumWidth(240)
        self.right_panel.setStyleSheet(f"background-color: {COLORS['bg_panel']}; border-radius: 8px;")
        layout = QtWidgets.QVBoxLayout(self.right_panel)
        
        # Stats Group
        grp_stats = QtWidgets.QGroupBox("INTERVAL STATISTICS")
        v_stats = QtWidgets.QVBoxLayout(grp_stats)
        self.lbl_pick_count = QtWidgets.QLabel("Total Picks: 0")
        self.lbl_mean_dip = QtWidgets.QLabel("Mean Dip: -")
        self.lbl_p50_dip = QtWidgets.QLabel("P50 Dip: -")
        v_stats.addWidget(self.lbl_pick_count)
        v_stats.addWidget(self.lbl_mean_dip)
        v_stats.addWidget(self.lbl_p50_dip)
        layout.addWidget(grp_stats)
        
        # Inspector Group
        grp_insp = QtWidgets.QGroupBox("PICK INSPECTOR")
        f_insp = QtWidgets.QFormLayout(grp_insp)
        f_insp.addRow("Depth:", QtWidgets.QLineEdit("Select pick..."))
        f_insp.addRow("Type:", QtWidgets.QComboBox())
        f_insp.addRow("Dip:", QtWidgets.QLineEdit(""))
        btn_del = QtWidgets.QPushButton("🗑 Delete Pick")
        f_insp.addRow("", btn_del)
        layout.addWidget(grp_insp)
        
        layout.addStretch()
        self.splitter.addWidget(self.right_panel)
        
    def _build_bottom_panel(self):
        # Table & Status Base
        self.bottom_widget = QtWidgets.QWidget()
        self.bottom_widget.setFixedHeight(200)
        b_layout = QtWidgets.QVBoxLayout(self.bottom_widget)
        b_layout.setContentsMargins(0,0,0,0)
        
        # Table
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Depth (MD)", "Type", "Dip (°)", "Azimuth (°)", "Aperture", "Confidence"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        b_layout.addWidget(self.table)
        
        # Status Bar
        self.status_lbl = QtWidgets.QLabel("Status: Ready. Image analysis module initialized.")
        self.status_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; padding: 4px;")
        b_layout.addWidget(self.status_lbl)
        
        self.main_layout.addWidget(self.bottom_widget)

    def prompt_load_image(self):
        options = QtWidgets.QFileDialog.Options()
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load Borehole Image", "", "LAS Files (*.las);;NumPy Arrays (*.npy);;Images (*.png *.jpg)", options=options
        )
        if file_path:
            self.status_lbl.setText(f"Loading: {os.path.basename(file_path)}...")
            QtWidgets.QApplication.processEvents()
            try:
                if file_path.lower().endswith('.las'):
                    las = lasio.read(file_path)
                    df = las.df()
                    
                    well_name = las.well.WELL.value if las.well.WELL.value else os.path.basename(file_path)
                    self.lbl_well_name.setText(f"Well: {well_name}")
                    
                    # Checking if we have density or gamma ray logs
                    azid_cols = [f'ABDC{i}M' for i in range(1, 17)]
                    azig_cols = [f'GRAS{i}M' for i in range(0, 8)]
                    
                    available_images = []
                    if all(c in df.columns for c in azid_cols):
                        available_images.append("Azimuthal Density (16 sectors)")
                    if all(c in df.columns for c in azig_cols):
                        available_images.append("Azimuthal Gamma Ray (8 sectors)")
                        
                    if not available_images:
                        raise ValueError("No recognizable LWD image sectors found in LAS file.")
                    
                    choice, ok = QtWidgets.QInputDialog.getItem(
                        self, "Select Image Log", "Choose image to display:", available_images, 0, False
                    )
                    if not ok: 
                        self.status_lbl.setText("Status: Load aborted.")
                        return
                    
                    if "Density" in choice:
                        img_df = df[azid_cols].dropna(how='all')
                        self.lbl_type.setText("Type: LWD Azi. Density")
                        # Basic normalisation for viz
                        vals = img_df.values
                        p1, p99 = np.percentile(vals[~np.isnan(vals)], (1, 99))
                        vals = np.clip(vals, p1, p99)
                    else:
                        img_df = df[azig_cols].dropna(how='all')
                        self.lbl_type.setText("Type: LWD Azi. Gamma")
                        vals = img_df.values
                        
                    depth_start = img_df.index.min()
                    depth_end = img_df.index.max()
                    data = vals
                    
                elif file_path.endswith('.npy'):
                    data = np.load(file_path)
                    depth_start, ok1 = QtWidgets.QInputDialog.getDouble(self, "Depth Start", "Enter Top Depth (MD):", 1000.0, -10000, 10000, 2)
                    if not ok1: return
                    depth_end, ok2 = QtWidgets.QInputDialog.getDouble(self, "Depth End", "Enter Bottom Depth (MD):", 1100.0, -10000, 10000, 2)
                    if not ok2: return
                    self.lbl_type.setText("Type: Generic NPY Array")
                else:
                    data = np.random.rand(1000, 360) * 255
                    depth_start, ok1 = QtWidgets.QInputDialog.getDouble(self, "Depth Start", "Enter Top Depth (MD):", 1000.0, 0, 10000)
                    if not ok1: return
                    depth_end, ok2 = QtWidgets.QInputDialog.getDouble(self, "Depth End", "Enter Bottom Depth (MD):", 1100.0, 0, 10000)
                    if not ok2: return
                    self.lbl_type.setText("Type: Mock Visualisation")
                
                self.viewer_engine.load_image(data, depth_start, depth_end)
                self.lbl_depth_range.setText(f"Depth: {depth_start:.1f} - {depth_end:.1f}")
                self.lbl_shape.setText(f"Res: {data.shape[1]} sects x {data.shape[0]}")
                self.status_lbl.setText(f"Success: Displaying dataset from {os.path.basename(file_path)}")
                
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Image Engine Error", f"Failed to parse and generate borehole image:\n{str(e)}")
                self.status_lbl.setText("Status: Error loading file.")
                
    def change_colormap(self, cmap_name):
        self.viewer_engine.set_colormap(cmap_name)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = ImageAnalysisTab()
    window.resize(1400, 900)
    window.show()
    sys.exit(app.exec_())
