import os
import sys
import numpy as np
from pathlib import Path
from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import matplotlib.cm as cm

class ImageViewerEngine(QtWidgets.QWidget):
    """
    SECTION 1 - IMAGE VIEWER ENGINE
    Using pyqtgraph for high-performance 2D raster rendering of wellbore images.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Depth Track (Placeholder)
        self.depth_track = pg.PlotWidget(title="Depth")
        self.depth_track.setFixedWidth(80)
        self.depth_track.hideAxis('bottom')
        self.depth_track.invertY(True)
        self.layout.addWidget(self.depth_track)
        
        # Main Image Canvas
        self.canvas = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.canvas)
        
        self.plot_item = self.canvas.addPlot(title="Borehole Image (Azimuth 0-360°)")
        self.plot_item.setLabel('bottom', "Azimuth")
        self.plot_item.setLabel('left', "Depth")
        self.plot_item.invertY(True)
        
        self.image_item = pg.ImageItem()
        self.plot_item.addItem(self.image_item)
        
        # Setup Colormap
        self.set_colormap('hot_r')
        
    def set_colormap(self, cmap_name):
        cmap = cm.get_cmap(cmap_name)
        # Create a lookup table (LUT) from matplotlib colormap
        lut = (cmap(np.linspace(0.0, 1.0, 256)) * 255).astype(np.uint8)
        self.image_item.setLookupTable(lut)
        
    def load_image(self, data, depth_start, depth_end):
        """Load 2D numpy array and map to depth"""
        self.image_item.setImage(data.T, autoLevels=True)
        # Scale image to match depth physically
        # Y (depth) starts at depth_start and goes to depth_end
        # X (azimuth) goes from 0 to 360
        y_scale = (depth_end - depth_start) / data.shape[0]
        x_scale = 360.0 / data.shape[1]
        
        transform = QtGui.QTransform()
        transform.scale(x_scale, y_scale)
        transform.translate(0, depth_start / y_scale)
        self.image_item.setTransform(transform)
        self.plot_item.autoRange()

class ImageAnalysisTab(QtWidgets.QWidget):
    """
    Main Borehole Image Log Analysis Module
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.apply_dark_theme()
        
    def init_ui(self):
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        
        # Top Toolbar
        self.toolbar_layout = QtWidgets.QHBoxLayout()
        
        self.btn_load = QtWidgets.QPushButton("Load Image")
        self.btn_load.clicked.connect(self.prompt_load_image)
        
        self.cmb_colormap = QtWidgets.QComboBox()
        self.cmb_colormap.addItems(["hot_r", "gray", "RdYlBu_r", "jet"])
        self.cmb_colormap.currentTextChanged.connect(self.change_colormap)
        
        self.toolbar_layout.addWidget(self.btn_load)
        self.toolbar_layout.addWidget(QtWidgets.QLabel("Colormap:"))
        self.toolbar_layout.addWidget(self.cmb_colormap)
        self.toolbar_layout.addStretch()
        
        self.main_layout.addLayout(self.toolbar_layout)
        
        # Central Splitter (Left Panel, Center Canvas, Right Panel)
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        
        # Left Panel (Controls)
        self.left_panel = QtWidgets.QWidget()
        self.left_panel.setFixedWidth(240)
        self.left_layout = QtWidgets.QVBoxLayout(self.left_panel)
        self.lbl_info = QtWidgets.QLabel("Image Properties\nNo Image Loaded")
        self.left_layout.addWidget(self.lbl_info)
        self.left_layout.addStretch()
        
        # Center Canvas Engine
        self.viewer_engine = ImageViewerEngine()
        
        # Right Panel (Inspector)
        self.right_panel = QtWidgets.QWidget()
        self.right_panel.setFixedWidth(220)
        self.right_layout = QtWidgets.QVBoxLayout(self.right_panel)
        self.right_layout.addWidget(QtWidgets.QLabel("Pick Inspector"))
        self.right_layout.addStretch()
        
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.viewer_engine)
        self.splitter.addWidget(self.right_panel)
        
        # Give majority of space to center viewer
        self.splitter.setSizes([240, 800, 220])
        self.main_layout.addWidget(self.splitter)
        
        # Bottom Status Bar / Table Placeholder
        self.status_lbl = QtWidgets.QLabel("Status: Ready | Not Loaded")
        self.main_layout.addWidget(self.status_lbl)
        
    def prompt_load_image(self):
        options = QtWidgets.QFileDialog.Options()
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load Borehole Image", "", "NumPy Arrays (*.npy);;Images (*.png *.jpg)", options=options
        )
        if file_path:
            self.status_lbl.setText(f"Loaded: {os.path.basename(file_path)}")
            # For phase 1 demonstration, simulate a random dataset 
            # (In production, load with standard cv2/PIL or numpy)
            try:
                if file_path.endswith('.npy'):
                    data = np.load(file_path)
                else:
                    # dummy fallback for standard images
                    data = np.random.rand(1000, 360) * 255
                
                # Mock Depth dialog for phase 1
                depth_start, ok1 = QtWidgets.QInputDialog.getDouble(self, "Depth Start", "Enter Top Depth (MD):", 1000.0, 0, 10000)
                if not ok1: return
                depth_end, ok2 = QtWidgets.QInputDialog.getDouble(self, "Depth End", "Enter Bottom Depth (MD):", 1100.0, 0, 10000)
                if not ok2: return
                
                self.viewer_engine.load_image(data, depth_start, depth_end)
                self.lbl_info.setText(f"Depth: {depth_start} - {depth_end}\nShape: {data.shape}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", str(e))
                
    def change_colormap(self, cmap_name):
        self.viewer_engine.set_colormap(cmap_name)

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1A1D2E;
                color: #E8ECF0;
                font-family: 'Segoe UI';
            }
            QPushButton {
                background-color: #1E2235;
                border: 1px solid #2A2F45;
                padding: 4px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                border: 1px solid #00B4D8;
            }
            QComboBox {
                background-color: #1E2235;
                border: 1px solid #2A2F45;
                padding: 4px;
            }
        """)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = ImageAnalysisTab()
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec_())