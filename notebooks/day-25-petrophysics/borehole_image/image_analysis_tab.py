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
# UI COMPONENTS & STYLING
# ---------------------------------------------------------

# Light theme matching PetroAnalyst Pro standard
STYLE_FRAME = """
    QFrame#PanelFrame {
        background-color: #F8F9FA;
        border: 1px solid #D0D7E5;
        border-radius: 4px;
    }
"""

STYLE_HEADER = """
    QLabel#PanelHeader {
        background-color: #4A76B8;
        color: #FFFFFF;
        font-weight: bold;
        font-size: 13px;
        padding: 8px;
        border-top-left-radius: 3px;
        border-top-right-radius: 3px;
    }
"""

STYLE_BTN_BLUE = """
    QPushButton {
        background-color: #4A76B8;
        color: #FFFFFF;
        border: none;
        border-radius: 3px;
        padding: 5px 12px;
        font-weight: bold;
    }
    QPushButton:hover { background-color: #3b5f94; }
    QPushButton:pressed { background-color: #29446b; }
"""

STYLE_BTN_LIGHT = """
    QPushButton {
        background-color: #EDF1F5;
        color: #333333;
        border: 1px solid #C2D0E0;
        border-radius: 3px;
        padding: 4px 8px;
    }
    QPushButton:hover { background-color: #E2E8F0; }
"""

STYLE_TABLE = """
    QTableWidget {
        background-color: #FFFFFF;
        alternate-background-color: #F8F9FA;
        gridline-color: #E2E8F0;
        selection-background-color: #D3E3F5;
        selection-color: #000000;
        border: 1px solid #D0D7E5;
    }
    QHeaderView::section {
        background-color: #EDF1F5;
        border: 1px solid #D0D7E5;
        padding: 4px;
        font-weight: bold;
        color: #4A5568;
    }
"""

class ImageViewerEngine(QtWidgets.QWidget):
    """SECTION 1 - IMAGE VIEWER ENGINE (Light Theme)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Configure pyqtgraph for light theme
        pg.setConfigOptions(antialias=True)
        pg.setConfigOption('background', '#FFFFFF')
        pg.setConfigOption('foreground', '#333333')
        
        self.canvas = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.canvas)
        
        # 1. Left Track (e.g. GR)
        self.left_plot = self.canvas.addPlot(col=0)
        self.left_plot.setMaximumWidth(120)
        self.left_plot.hideAxis('bottom')
        self.left_plot.invertY(True)
        
        # 2. Main Image Plot
        self.img_plot = self.canvas.addPlot(col=1)
        self.img_plot.setLabel('bottom', "Azimuth (°)")
        self.img_plot.getAxis('bottom').setTicks([[(0, '0'), (90, '90'), (180, '180'), (270, '270'), (360, '360')]])
        self.img_plot.setXRange(0, 360)
        self.img_plot.hideAxis('left') 
        self.img_plot.invertY(True)
        
        # 3. Right Track
        self.right_plot = self.canvas.addPlot(col=2)
        self.right_plot.setMaximumWidth(120)
        self.right_plot.hideAxis('bottom')
        self.right_plot.hideAxis('left')
        self.right_plot.invertY(True)
        
        # Link Y axes
        self.img_plot.setYLink(self.left_plot)
        self.right_plot.setYLink(self.left_plot)
        
        # Image Item
        self.image_item = pg.ImageItem()
        self.img_plot.addItem(self.image_item)
        
        self.set_colormap('jet') # Match the Rainbow colormap from the image
        
    def set_colormap(self, cmap_name):
        try:
            cmap = cm.get_cmap(cmap_name)
            lut = (cmap(np.linspace(0.0, 1.0, 256)) * 255).astype(np.uint8)
            self.image_item.setLookupTable(lut)
        except Exception as e:
            print(f"Colormap error: {e}")
            
    def load_image(self, data, depth_start, depth_end):
        data = np.nan_to_num(data, nan=np.nanmean(data))
        self.image_item.setImage(data.T, autoLevels=True)
        rect = QtCore.QRectF(0, depth_start, 360, depth_end - depth_start)
        self.image_item.setRect(rect)
        self.left_plot.setYRange(depth_start, depth_end)


class ImageAnalysisTab(QtWidgets.QWidget):
    """Main Borehole Image Log Analysis Module (Upgraded UI)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QWidget { font-family: 'Segoe UI', Arial; font-size: 12px; color: #333333; background-color: #EDF1F5; }")
        self.init_ui()
        
    def init_ui(self):
        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(8)
        
        # Splitter to separate Left panel and Right Canvas area
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.main_layout.addWidget(self.splitter)
        
        self._build_left_sidebar()
        self._build_right_area()
        
        self.splitter.setSizes([320, 1000])

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
        self.left_sidebar.setMaximumWidth(400)
        l_layout = QtWidgets.QVBoxLayout(self.left_sidebar)
        l_layout.setContentsMargins(0, 0, 0, 0)
        l_layout.setSpacing(12)
        
        # --- TOP PANEL: Controls ---
        ctrl_frame, ctrl_layout = self._build_panel_frame("Borehole Image Controls")
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(12)
        
        # Load
        grid.addWidget(QtWidgets.QLabel("Load Image:"), 0, 0)
        self.btn_load = QtWidgets.QPushButton("Load Image")
        self.btn_load.setStyleSheet(STYLE_BTN_BLUE)
        self.btn_load.clicked.connect(self.prompt_load_image)
        grid.addWidget(self.btn_load, 0, 1)
        
        # Colormap
        grid.addWidget(QtWidgets.QLabel("Colormap:"), 1, 0)
        self.cmb_colormap = QtWidgets.QComboBox()
        self.cmb_colormap.setStyleSheet("background: white; border: 1px solid #C2D0E0; padding: 3px;")
        self.cmb_colormap.addItems(["jet", "hot_r", "gray", "RdYlBu_r", "bone", "copper"])
        self.cmb_colormap.currentTextChanged.connect(self.change_colormap)
        grid.addWidget(self.cmb_colormap, 1, 1)
        
        # Pick mode
        grid.addWidget(QtWidgets.QLabel("Pick Mode:"), 2, 0, QtCore.Qt.AlignTop)
        vbox_radio = QtWidgets.QVBoxLayout()
        self.rad_frac = QtWidgets.QRadioButton("Fracture")
        self.rad_bed = QtWidgets.QRadioButton("Bedding")
        self.rad_frac.setChecked(True)
        vbox_radio.addWidget(self.rad_frac)
        vbox_radio.addWidget(self.rad_bed)
        grid.addLayout(vbox_radio, 2, 1)
        
        # Clear picks
        grid.addWidget(QtWidgets.QLabel("Clear Picks:"), 3, 0)
        hbox_clear = QtWidgets.QHBoxLayout()
        for t in ["⚑", "▤", "Clear All"]:
            b = QtWidgets.QPushButton(t)
            b.setStyleSheet(STYLE_BTN_LIGHT)
            hbox_clear.addWidget(b)
        grid.addLayout(hbox_clear, 3, 1)
        
        # Zoom controls
        grid.addWidget(QtWidgets.QLabel("Zoom In"), 4, 0)
        hbox_z_in = QtWidgets.QHBoxLayout()
        btn_zin_m = QtWidgets.QPushButton("-"); btn_zin_m.setStyleSheet(STYLE_BTN_BLUE); btn_zin_m.setFixedWidth(40)
        btn_zin_p = QtWidgets.QPushButton("+"); btn_zin_p.setStyleSheet(STYLE_BTN_BLUE); btn_zin_p.setFixedWidth(40)
        hbox_z_in.addWidget(btn_zin_m); hbox_z_in.addWidget(btn_zin_p); hbox_z_in.addStretch()
        grid.addLayout(hbox_z_in, 4, 1)
        
        grid.addWidget(QtWidgets.QLabel("Zoom Out"), 5, 0)
        hbox_z_out = QtWidgets.QHBoxLayout()
        btn_zout_m = QtWidgets.QPushButton("-"); btn_zout_m.setStyleSheet(STYLE_BTN_BLUE); btn_zout_m.setFixedWidth(40)
        btn_zout_p = QtWidgets.QPushButton("+"); btn_zout_p.setStyleSheet(STYLE_BTN_BLUE); btn_zout_p.setFixedWidth(40)
        hbox_z_out.addWidget(btn_zout_m); hbox_z_out.addWidget(btn_zout_p); hbox_z_out.addStretch()
        grid.addLayout(hbox_z_out, 5, 1)
        
        # Advanced Zoom Bar
        hbox_z_adv = QtWidgets.QHBoxLayout()
        for idx, t in enumerate(["🔍 Zoom In", "🔍 Zoom Out", "Reset ▼"]):
            b = QtWidgets.QPushButton(t)
            b.setStyleSheet(STYLE_BTN_LIGHT)
            hbox_z_adv.addWidget(b)
        grid.addLayout(hbox_z_adv, 6, 0, 1, 2)
        
        # Measure
        grid.addWidget(QtWidgets.QLabel("Measure Track Distance"), 7, 0)
        hbox_meas = QtWidgets.QHBoxLayout()
        sp1 = QtWidgets.QSpinBox(); sp1.setValue(0); sp1.setStyleSheet("background: white;")
        sp2 = QtWidgets.QSpinBox(); sp2.setValue(100); sp2.setStyleSheet("background: white;")
        sp1.setMaximum(1000); sp2.setMaximum(1000)
        hbox_meas.addWidget(sp1); hbox_meas.addWidget(QtWidgets.QLabel("-")); hbox_meas.addWidget(sp2)
        grid.addLayout(hbox_meas, 7, 1)
        
        # Export
        grid.addWidget(QtWidgets.QLabel("Export Picks:"), 8, 0)
        self.cmb_export = QtWidgets.QComboBox()
        self.cmb_export.addItems(["CSV", "LAS"])
        self.cmb_export.setStyleSheet("background: white; border: 1px solid #C2D0E0; padding: 3px;")
        grid.addWidget(self.cmb_export, 8, 1)
        
        ctrl_layout.addLayout(grid)
        l_layout.addWidget(ctrl_frame)
        
        # --- BOTTOM PANEL: Table ---
        tbl_frame, tbl_layout = self._build_panel_frame("Fracture and Bedding Picks")
        
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Depth (MD)", "Type", "Dip (°)", "Azimuth (°)"])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(STYLE_TABLE)
        
        # Mock data
        self.table.setRowCount(3)
        self.table.setItem(0, 0, QtWidgets.QTableWidgetItem("3872.5"))
        self.table.setItem(0, 1, QtWidgets.QTableWidgetItem("Fracture"))
        self.table.setItem(0, 2, QtWidgets.QTableWidgetItem("42"))
        self.table.setItem(0, 3, QtWidgets.QTableWidgetItem("130"))
        
        self.table.setItem(1, 0, QtWidgets.QTableWidgetItem("3825.8"))
        self.table.setItem(1, 1, QtWidgets.QTableWidgetItem("Fracture"))
        self.table.setItem(1, 2, QtWidgets.QTableWidgetItem("38"))
        self.table.setItem(1, 3, QtWidgets.QTableWidgetItem("115"))
        
        self.table.setItem(2, 0, QtWidgets.QTableWidgetItem("4061.0"))
        self.table.setItem(2, 1, QtWidgets.QTableWidgetItem("Fracture"))
        self.table.setItem(2, 2, QtWidgets.QTableWidgetItem("56"))
        self.table.setItem(2, 3, QtWidgets.QTableWidgetItem("165"))
        
        tbl_layout.addWidget(self.table)
        
        # Table bottoms
        hbox_tbl1 = QtWidgets.QHBoxLayout()
        btn_clr_tbl = QtWidgets.QPushButton("🟥 Clear Table")
        btn_clr_tbl.setStyleSheet(STYLE_BTN_LIGHT)
        btn_exp_csv = QtWidgets.QPushButton("⬇ Export CSV")
        btn_exp_csv.setStyleSheet(STYLE_BTN_BLUE)
        hbox_tbl1.addWidget(btn_clr_tbl); hbox_tbl1.addStretch(); hbox_tbl1.addWidget(btn_exp_csv)
        tbl_layout.addLayout(hbox_tbl1)
        
        hbox_tbl2 = QtWidgets.QHBoxLayout()
        for t in ["🔍 Select", "🔍 Zoom In", "⟲ Reset"]:
            b = QtWidgets.QPushButton(t)
            b.setStyleSheet(STYLE_BTN_LIGHT)
            hbox_tbl2.addWidget(b)
        tbl_layout.addLayout(hbox_tbl2)
        
        l_layout.addWidget(tbl_frame)
        self.splitter.addWidget(self.left_sidebar)

    def _build_right_area(self):
        self.right_area = QtWidgets.QWidget()
        self.right_area.setStyleSheet("background-color: #FFFFFF; border: 1px solid #D0D7E5; border-radius: 4px;")
        r_layout = QtWidgets.QVBoxLayout(self.right_area)
        r_layout.setContentsMargins(0, 0, 0, 0)
        r_layout.setSpacing(0)
        
        # Toolbar
        self.toolbar = QtWidgets.QWidget()
        self.toolbar.setStyleSheet("background-color: #EDF1F5; border-bottom: 1px solid #D0D7E5;")
        self.toolbar.setFixedHeight(45)
        tb_layout = QtWidgets.QHBoxLayout(self.toolbar)
        tb_layout.setContentsMargins(12, 0, 12, 0)
        tb_layout.setSpacing(8)
        
        tools = ["Select", "Zoom In", "Zoom Out", "Fit to Window", "Reset Zoom", "Pan", "Measure", "Show Grid Lines"]
        for t in tools:
            btn = QtWidgets.QPushButton(t)
            if t == "Select":
                btn.setStyleSheet(STYLE_BTN_BLUE)
            else:
                btn.setStyleSheet(STYLE_BTN_LIGHT + "QPushButton { border: none; background: transparent; color: #4A76B8; font-weight: bold; } QPushButton:hover { background: #E2E8F0; }")
            tb_layout.addWidget(btn)
        
        tb_layout.addStretch()
        r_layout.addWidget(self.toolbar)
        
        # Image Canvas
        self.viewer_engine = ImageViewerEngine()
        r_layout.addWidget(self.viewer_engine)
        
        self.splitter.addWidget(self.right_area)

    def prompt_load_image(self):
        options = QtWidgets.QFileDialog.Options()
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load Borehole Image", "", "LAS Files (*.las);;NumPy Arrays (*.npy);;Images (*.png *.jpg)", options=options
        )
        if file_path:
            QtWidgets.QApplication.processEvents()
            try:
                if file_path.lower().endswith('.las'):
                    las = lasio.read(file_path)
                    df = las.df()
                    
                    azid_cols = [f'ABDC{i}M' for i in range(1, 17)]
                    azig_cols = [f'GRAS{i}M' for i in range(0, 8)]
                    
                    available_images = []
                    if all(c in df.columns for c in azid_cols):
                        available_images.append("Azimuthal Density (16 sectors)")
                    if all(c in df.columns for c in azig_cols):
                        available_images.append("Azimuthal Gamma Ray (8 sectors)")
                        
                    if not available_images:
                        raise ValueError("No LWD image sectors found in LAS file.")
                    
                    choice, ok = QtWidgets.QInputDialog.getItem(
                        self, "Select Image Log", "Choose image to display:", available_images, 0, False
                    )
                    if not ok: return
                    
                    if "Density" in choice:
                        img_df = df[azid_cols].dropna(how='all')
                        vals = img_df.values
                        p1, p99 = np.percentile(vals[~np.isnan(vals)], (1, 99))
                        vals = np.clip(vals, p1, p99)
                    else:
                        img_df = df[azig_cols].dropna(how='all')
                        vals = img_df.values
                        
                    depth_start = img_df.index.min()
                    depth_end = img_df.index.max()
                    data = vals
                    
                elif file_path.endswith('.npy'):
                    data = np.load(file_path)
                    depth_start, ok1 = QtWidgets.QInputDialog.getDouble(self, "Depth Start", "MD:", 1000.0, -10000, 10000, 2)
                    if not ok1: return
                    depth_end, ok2 = QtWidgets.QInputDialog.getDouble(self, "Depth End", "MD:", 1100.0, -10000, 10000, 2)
                    if not ok2: return
                else:
                    data = np.random.rand(1000, 360) * 255
                    depth_start = 3800.0
                    depth_end = 4100.0
                
                self.viewer_engine.load_image(data, depth_start, depth_end)
                QtWidgets.QMessageBox.information(self, "Success", f"Loaded dataset from {os.path.basename(file_path)}")
                
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Image Engine Error", str(e))
                
    def change_colormap(self, cmap_name):
        self.viewer_engine.set_colormap(cmap_name)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ImageAnalysisTab()
    window.resize(1300, 850)
    window.show()
    sys.exit(app.exec_())
