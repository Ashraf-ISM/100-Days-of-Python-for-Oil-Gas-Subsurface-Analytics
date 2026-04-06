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
# CONSTANTS & THEMING - Light Professional Theme
# ---------------------------------------------------------
COLORS = {
    "bg_main": "#FFFFFF",
    "bg_panel": "#F8F9FA",
    "bg_secondary": "#F0F2F5",
    "border": "#D9D9E3",
    "border_light": "#E8E8F0",
    "accent_primary": "#1976D2",
    "accent_secondary": "#1565C0",
    "accent_hover": "#1565C0",
    "accent_light": "#E3F2FD",
    "text_primary": "#212529",
    "text_secondary": "#6C757D",
    "text_tertiary": "#ADB5BD",
    "success": "#28A745",
    "warning": "#FFC107",
    "danger": "#DC3545",
    "fracture": "#E63946",
    "bedding": "#FF9800",
    "fault": "#F4A261",
    "vugs": "#00ACC1",
    "shadow": "rgba(0, 0, 0, 0.08)"
}

QSS_THEME = f"""
/* Global Styling */
QWidget {{
    background-color: {COLORS['bg_main']};
    color: {COLORS['text_primary']};
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif;
    font-size: 10pt;
}}

/* Main Container */
QMainWindow, QDialog {{
    background-color: {COLORS['bg_main']};
}}

/* Splitter */
QSplitter {{
    background-color: {COLORS['bg_main']};
}}
QSplitter::handle {{
    background-color: {COLORS['border_light']};
    width: 1px;
    margin: 0px;
}}
QSplitter::handle:hover {{
    background-color: {COLORS['border']};
}}

/* Group Box */
QGroupBox {{
    border: 1px solid {COLORS['border_light']};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 18px;
    padding-left: 12px;
    padding-right: 12px;
    padding-bottom: 12px;
    font-weight: 600;
    color: {COLORS['text_primary']};
    background-color: {COLORS['bg_panel']};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: -8px;
    color: {COLORS['accent_primary']};
    background-color: {COLORS['bg_main']};
    padding: 0 6px;
    font-size: 10pt;
    font-weight: 600;
    letter-spacing: 0.5px;
}}

/* Primary Button */
QPushButton {{
    background-color: {COLORS['bg_panel']};
    border: 1px solid {COLORS['border_light']};
    padding: 7px 14px;
    border-radius: 6px;
    color: {COLORS['text_primary']};
    font-weight: 500;
    font-size: 10pt;
}}
QPushButton:hover {{
    background-color: {COLORS['bg_secondary']};
    border: 1px solid {COLORS['accent_primary']};
    color: {COLORS['accent_primary']};
}}
QPushButton:pressed {{
    background-color: {COLORS['accent_primary']};
    border: 1px solid {COLORS['accent_secondary']};
    color: white;
}}
QPushButton:disabled {{
    color: {COLORS['text_tertiary']};
    border: 1px solid {COLORS['border_light']};
}}

/* Active Button State */
QPushButton[active="true"] {{
    border: 2px solid {COLORS['accent_primary']};
    background-color: {COLORS['accent_light']};
    color: {COLORS['accent_primary']};
    font-weight: 600;
}}
QPushButton[active="true"]:hover {{
    background-color: {COLORS['accent_light']};
}}

/* Accent Button */
QPushButton[accent="true"] {{
    background-color: {COLORS['accent_primary']};
    border: 1px solid {COLORS['accent_secondary']};
    color: white;
    font-weight: 600;
}}
QPushButton[accent="true"]:hover {{
    background-color: {COLORS['accent_hover']};
}}

/* Combo Box */
QComboBox {{
    background-color: {COLORS['bg_main']};
    border: 1px solid {COLORS['border']};
    padding: 6px 10px;
    border-radius: 6px;
    color: {COLORS['text_primary']};
    font-size: 10pt;
}}
QComboBox:hover {{
    border: 1px solid {COLORS['accent_primary']};
    background-color: {COLORS['accent_light']};
}}
QComboBox:focus {{
    border: 2px solid {COLORS['accent_primary']};
    padding: 5px 9px;
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 1px solid {COLORS['border_light']};
    width: 12px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_panel']};
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['accent_light']};
    outline: none;
}}

/* Spin Boxes */
QDoubleSpinBox, QSpinBox {{
    background-color: {COLORS['bg_main']};
    border: 1px solid {COLORS['border']};
    padding: 6px 10px;
    border-radius: 6px;
    color: {COLORS['text_primary']};
    font-size: 10pt;
}}
QDoubleSpinBox:hover, QSpinBox:hover {{
    border: 1px solid {COLORS['accent_primary']};
    background-color: {COLORS['accent_light']};
}}
QDoubleSpinBox:focus, QSpinBox:focus {{
    border: 2px solid {COLORS['accent_primary']};
    padding: 5px 9px;
}}
QDoubleSpinBox::up-button, QSpinBox::up-button {{
    border: none;
    width: 20px;
}}
QDoubleSpinBox::down-button, QSpinBox::down-button {{
    border: none;
    width: 20px;
}}

/* Line Edit */
QLineEdit {{
    background-color: {COLORS['bg_main']};
    border: 1px solid {COLORS['border']};
    padding: 6px 10px;
    border-radius: 6px;
    color: {COLORS['text_primary']};
    font-size: 10pt;
    selection-background-color: {COLORS['accent_light']};
}}
QLineEdit:focus {{
    border: 2px solid {COLORS['accent_primary']};
    padding: 5px 9px;
}}
QLineEdit:hover {{
    border: 1px solid {COLORS['accent_primary']};
}}

/* Table Widget */
QTableWidget {{
    background-color: {COLORS['bg_main']};
    alternate-background-color: {COLORS['bg_panel']};
    border: 1px solid {COLORS['border_light']};
    gridline-color: {COLORS['border_light']};
    font-size: 9pt;
}}
QTableWidget::item {{
    padding: 4px 6px;
}}
QTableWidget::item:selected {{
    background-color: {COLORS['accent_light']};
    color: {COLORS['text_primary']};
}}

/* Table Header */
QHeaderView {{
    background-color: {COLORS['bg_panel']};
    color: {COLORS['text_primary']};
}}
QHeaderView::section {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_primary']};
    border: none;
    border-right: 1px solid {COLORS['border_light']};
    border-bottom: 2px solid {COLORS['border']};
    padding: 8px 6px;
    font-weight: 600;
    font-size: 9pt;
}}
QHeaderView::section:hover {{
    background-color: {COLORS['bg_panel']};
}}

/* Scroll Bar */
QScrollBar:vertical {{
    border: none;
    background: {COLORS['bg_main']};
    width: 10px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: {COLORS['border']};
    min-height: 20px;
    border-radius: 5px;
    margin: 0px 2px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLORS['accent_primary']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    border: none;
    background: none;
}}

QScrollBar:horizontal {{
    border: none;
    background: {COLORS['bg_main']};
    height: 10px;
}}
QScrollBar::handle:horizontal {{
    background: {COLORS['border']};
    min-width: 20px;
    border-radius: 5px;
    margin: 2px 0px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {COLORS['accent_primary']};
}}

/* Label */
QLabel {{
    color: {COLORS['text_primary']};
    font-size: 10pt;
}}

/* Status Bar */
QStatusBar {{
    background-color: {COLORS['bg_panel']};
    border-top: 1px solid {COLORS['border_light']};
    color: {COLORS['text_secondary']};
}}

/* Tooltips */
QToolTip {{
    background-color: {COLORS['text_primary']};
    color: white;
    border: 1px solid {COLORS['text_secondary']};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 9pt;
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

        # Configure pyqtgraph global settings for professional light theme
        pg.setConfigOptions(antialias=True)
        pg.setConfigOption('background', COLORS['bg_main'])
        pg.setConfigOption('foreground', COLORS['text_secondary'])

        self.canvas = pg.GraphicsLayoutWidget()
        self.canvas.setStyleSheet(f"background-color: {COLORS['bg_main']}; border: none;")
        self.layout.addWidget(self.canvas)

        # Setup Depth Plot (Left)
        self.depth_plot = self.canvas.addPlot(col=0)
        self.depth_plot.setMaximumWidth(80)
        self.depth_plot.setLabel('left', "Depth (MD)", units='m', color=COLORS['text_secondary'])
        self.depth_plot.hideAxis('bottom')
        self.depth_plot.invertY(True)
        self.depth_plot.setYRange(0, 100)
        self.depth_plot.getAxis('left').setPen(pg.mkPen(color=COLORS['border']))
        self.depth_plot.getAxis('left').setTextPen(pg.mkPen(color=COLORS['text_secondary']))

        # Setup Image Plot (Right)
        self.img_plot = self.canvas.addPlot(col=1)
        self.img_plot.setLabel('bottom', "Azimuth (°)", color=COLORS['text_secondary'])
        self.img_plot.getAxis('bottom').setTicks([[(0, '0°'), (90, '90°E'), (180, '180°S'), (270, '270°W'), (360, '360°')]])
        self.img_plot.setXRange(0, 360)
        self.img_plot.hideAxis('left')
        self.img_plot.invertY(True)
        self.img_plot.getAxis('bottom').setPen(pg.mkPen(color=COLORS['border']))
        self.img_plot.getAxis('bottom').setTextPen(pg.mkPen(color=COLORS['text_secondary']))

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

        # pyqtgraph expects image as (x, y) not (y, x), so we transpose
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
        self.toolbar_layout.setSpacing(12)
        self.toolbar_layout.setContentsMargins(0, 0, 0, 0)

        # Top Toolbar Frame
        toolbar_frame = QtWidgets.QFrame()
        toolbar_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_panel']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        toolbar_frame.setLayout(self.toolbar_layout)

        # Load Button
        self.btn_load = QtWidgets.QPushButton("📂 Load Image...")
        self.btn_load.setMinimumHeight(36)
        self.btn_load.clicked.connect(self.prompt_load_image)
        self.btn_load.setToolTip("Load LAS file or NumPy array image")
        self.btn_load.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        # Colormap Label
        self.lbl_cmap = QtWidgets.QLabel("Colormap:")
        self.lbl_cmap.setStyleSheet(f"color:{COLORS['text_secondary']}; font-weight:600; font-size: 10pt;")

        # Colormap Selector
        self.cmb_colormap = QtWidgets.QComboBox()
        self.cmb_colormap.setMinimumHeight(36)
        self.cmb_colormap.addItems(["hot_r", "gray", "RdYlBu_r", "jet", "bone", "copper", "viridis", "plasma", "inferno"])
        self.cmb_colormap.currentTextChanged.connect(self.change_colormap)
        self.cmb_colormap.setToolTip("Select color mapping for image visualization")

        # Separator
        sep1 = QtWidgets.QFrame()
        sep1.setFrameShape(QtWidgets.QFrame.VLine)
        sep1.setStyleSheet(f"border-left: 1px solid {COLORS['border_light']}; margin: 0 4px;")

        # Contrast Controls
        lbl_contrast = QtWidgets.QLabel("Contrast:")
        lbl_contrast.setStyleSheet(f"color:{COLORS['text_secondary']}; font-weight:600; font-size: 10pt;")

        self.spn_brightness = QtWidgets.QDoubleSpinBox()
        self.spn_brightness.setMinimumHeight(36)
        self.spn_brightness.setRange(0.5, 2.0)
        self.spn_brightness.setValue(1.0)
        self.spn_brightness.setSingleStep(0.1)
        self.spn_brightness.setMaximumWidth(80)
        self.spn_brightness.setToolTip("Brightness adjustment")

        # Separator
        sep2 = QtWidgets.QFrame()
        sep2.setFrameShape(QtWidgets.QFrame.VLine)
        sep2.setStyleSheet(f"border-left: 1px solid {COLORS['border_light']}; margin: 0 4px;")

        # Export/Actions Button
        self.btn_export = QtWidgets.QPushButton("💾 Export")
        self.btn_export.setMinimumHeight(36)
        self.btn_export.setProperty("accent", "true")
        self.btn_export.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_export.setToolTip("Export interpretation results")

        # Assemble Toolbar
        self.toolbar_layout.addWidget(self.btn_load)
        self.toolbar_layout.addSpacing(4)
        self.toolbar_layout.addWidget(self.lbl_cmap)
        self.toolbar_layout.addWidget(self.cmb_colormap)
        self.toolbar_layout.addWidget(sep1)
        self.toolbar_layout.addWidget(lbl_contrast)
        self.toolbar_layout.addWidget(self.spn_brightness)
        self.toolbar_layout.addStretch()
        self.toolbar_layout.addWidget(sep2)
        self.toolbar_layout.addWidget(self.btn_export)

        self.main_layout.addWidget(toolbar_frame)

    def _build_left_panel(self):
        self.left_panel = QtWidgets.QWidget()
        self.left_panel.setMinimumWidth(260)
        self.left_panel.setMaximumWidth(320)
        self.left_panel.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg_panel']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        layout = QtWidgets.QVBoxLayout(self.left_panel)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # ========== WELL & IMAGE INFO ==========
        grp_info = QtWidgets.QGroupBox("WELL & IMAGE INFO")
        v_info = QtWidgets.QVBoxLayout(grp_info)
        v_info.setSpacing(8)

        self.lbl_well_name = QtWidgets.QLabel("Well: —")
        self.lbl_well_name.setStyleSheet(f"font-weight: 600; color: {COLORS['text_primary']};")

        self.lbl_type = QtWidgets.QLabel("Type: —")
        self.lbl_type.setStyleSheet(f"font-size: 9pt; color: {COLORS['text_secondary']};")

        self.lbl_depth_range = QtWidgets.QLabel("Depth Range: —")
        self.lbl_depth_range.setStyleSheet(f"font-size: 9pt; color: {COLORS['text_secondary']};")

        self.lbl_shape = QtWidgets.QLabel("Resolution: —")
        self.lbl_shape.setStyleSheet(f"font-size: 9pt; color: {COLORS['text_secondary']};")

        v_info.addWidget(self.lbl_well_name)
        v_info.addWidget(self.lbl_type)
        v_info.addWidget(self.lbl_depth_range)
        v_info.addWidget(self.lbl_shape)
        layout.addWidget(grp_info)

        # ========== INTERPRETATION TOOLS ==========
        grp_tools = QtWidgets.QGroupBox("INTERPRETATION TOOLS")
        v_tools = QtWidgets.QVBoxLayout(grp_tools)
        v_tools.setSpacing(6)

        self.btn_zoom = QtWidgets.QPushButton("🔍 Zoom / Pan")
        self.btn_zoom.setMinimumHeight(32)
        self.btn_zoom.setProperty("active", "true")
        self.btn_zoom.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        self.btn_frac = QtWidgets.QPushButton("🪨 Fracture (F)")
        self.btn_frac.setMinimumHeight(32)
        self.btn_frac.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        self.btn_bed = QtWidgets.QPushButton("📐 Bedding (B)")
        self.btn_bed.setMinimumHeight(32)
        self.btn_bed.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        self.btn_vug = QtWidgets.QPushButton("🌊 Vugs (V)")
        self.btn_vug.setMinimumHeight(32)
        self.btn_vug.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        self.btn_fault = QtWidgets.QPushButton("🚫 Fault (T)")
        self.btn_fault.setMinimumHeight(32)
        self.btn_fault.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        v_tools.addWidget(self.btn_zoom)
        v_tools.addWidget(self.btn_frac)
        v_tools.addWidget(self.btn_bed)
        v_tools.addWidget(self.btn_vug)
        v_tools.addWidget(self.btn_fault)
        layout.addWidget(grp_tools)

        # ========== MANUAL SINUSOID FIT ==========
        grp_sin = QtWidgets.QGroupBox("MANUAL SINUSOID FIT")
        f_sin = QtWidgets.QFormLayout(grp_sin)
        f_sin.setSpacing(8)
        f_sin.setContentsMargins(8, 12, 8, 8)

        self.spn_dip = QtWidgets.QDoubleSpinBox()
        self.spn_dip.setMinimumHeight(30)
        self.spn_dip.setRange(0, 90)
        self.spn_dip.setValue(45)
        self.spn_dip.setSingleStep(1)
        self.spn_dip.setSuffix(" °")

        self.spn_azi = QtWidgets.QDoubleSpinBox()
        self.spn_azi.setMinimumHeight(30)
        self.spn_azi.setRange(0, 360)
        self.spn_azi.setValue(0)
        self.spn_azi.setSingleStep(1)
        self.spn_azi.setSuffix(" °")

        btn_preview = QtWidgets.QPushButton("Preview Fit")
        btn_preview.setMinimumHeight(30)
        btn_preview.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        f_sin.addRow("Dip:", self.spn_dip)
        f_sin.addRow("Azimuth:", self.spn_azi)
        f_sin.addRow("", btn_preview)
        layout.addWidget(grp_sin)

        layout.addStretch()
        self.splitter.addWidget(self.left_panel)

    def _build_right_panel(self):
        self.right_panel = QtWidgets.QWidget()
        self.right_panel.setMinimumWidth(260)
        self.right_panel.setMaximumWidth(320)
        self.right_panel.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg_panel']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        layout = QtWidgets.QVBoxLayout(self.right_panel)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # ========== INTERVAL STATISTICS ==========
        grp_stats = QtWidgets.QGroupBox("INTERVAL STATISTICS")
        v_stats = QtWidgets.QVBoxLayout(grp_stats)
        v_stats.setSpacing(8)

        self.lbl_pick_count = QtWidgets.QLabel("Total Picks: 0")
        self.lbl_pick_count.setStyleSheet(f"font-weight: 600; color: {COLORS['accent_primary']};")

        self.lbl_mean_dip = QtWidgets.QLabel("Mean Dip: —")
        self.lbl_mean_dip.setStyleSheet(f"font-size: 9pt; color: {COLORS['text_secondary']};")

        self.lbl_p50_dip = QtWidgets.QLabel("Median Dip: —")
        self.lbl_p50_dip.setStyleSheet(f"font-size: 9pt; color: {COLORS['text_secondary']};")

        self.lbl_std_dip = QtWidgets.QLabel("Std Dev: —")
        self.lbl_std_dip.setStyleSheet(f"font-size: 9pt; color: {COLORS['text_secondary']};")

        v_stats.addWidget(self.lbl_pick_count)
        v_stats.addWidget(self.lbl_mean_dip)
        v_stats.addWidget(self.lbl_p50_dip)
        v_stats.addWidget(self.lbl_std_dip)
        layout.addWidget(grp_stats)

        # ========== PICK INSPECTOR ==========
        grp_insp = QtWidgets.QGroupBox("PICK INSPECTOR")
        f_insp = QtWidgets.QFormLayout(grp_insp)
        f_insp.setSpacing(8)
        f_insp.setContentsMargins(8, 12, 8, 8)

        self.line_depth = QtWidgets.QLineEdit("Select pick...")
        self.line_depth.setMinimumHeight(30)
        self.line_depth.setReadOnly(True)

        self.cmb_type = QtWidgets.QComboBox()
        self.cmb_type.setMinimumHeight(30)
        self.cmb_type.addItems(["Fracture", "Bedding", "Fault", "Vugs", "Other"])

        self.line_dip = QtWidgets.QLineEdit("")
        self.line_dip.setMinimumHeight(30)
        self.line_dip.setPlaceholderText("0.0 °")

        self.line_azi = QtWidgets.QLineEdit("")
        self.line_azi.setMinimumHeight(30)
        self.line_azi.setPlaceholderText("0.0 °")

        btn_del = QtWidgets.QPushButton("🗑 Delete Pick")
        btn_del.setMinimumHeight(30)
        btn_del.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        f_insp.addRow("Depth (MD):", self.line_depth)
        f_insp.addRow("Type:", self.cmb_type)
        f_insp.addRow("Dip:", self.line_dip)
        f_insp.addRow("Azimuth:", self.line_azi)
        f_insp.addRow("", btn_del)
        layout.addWidget(grp_insp)

        # ========== FILTER OPTIONS ==========
        grp_filter = QtWidgets.QGroupBox("FILTER OPTIONS")
        v_filter = QtWidgets.QVBoxLayout(grp_filter)
        v_filter.setSpacing(6)

        self.chk_fracture = QtWidgets.QCheckBox("Fractures")
        self.chk_fracture.setChecked(True)
        self.chk_fracture.setStyleSheet(f"color: {COLORS['fracture']}; font-weight: 600;")

        self.chk_bedding = QtWidgets.QCheckBox("Bedding")
        self.chk_bedding.setChecked(True)
        self.chk_bedding.setStyleSheet(f"color: {COLORS['bedding']}; font-weight: 600;")

        self.chk_fault = QtWidgets.QCheckBox("Faults")
        self.chk_fault.setChecked(True)
        self.chk_fault.setStyleSheet(f"color: {COLORS['fault']}; font-weight: 600;")

        self.chk_vugs = QtWidgets.QCheckBox("Vugs")
        self.chk_vugs.setChecked(True)
        self.chk_vugs.setStyleSheet(f"color: {COLORS['vugs']}; font-weight: 600;")

        v_filter.addWidget(self.chk_fracture)
        v_filter.addWidget(self.chk_bedding)
        v_filter.addWidget(self.chk_fault)
        v_filter.addWidget(self.chk_vugs)
        layout.addWidget(grp_filter)

        layout.addStretch()
        self.splitter.addWidget(self.right_panel)
        
    def _build_bottom_panel(self):
        # Table & Status Base
        self.bottom_widget = QtWidgets.QWidget()
        self.bottom_widget.setFixedHeight(220)
        self.bottom_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg_panel']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 8px;
            }}
        """)
        b_layout = QtWidgets.QVBoxLayout(self.bottom_widget)
        b_layout.setContentsMargins(12, 12, 12, 12)
        b_layout.setSpacing(8)

        # Table Label
        lbl_table = QtWidgets.QLabel("INTERPRETATION PICKS")
        lbl_table.setStyleSheet(f"""
            color: {COLORS['accent_primary']};
            font-weight: 600;
            font-size: 10pt;
            letter-spacing: 0.5px;
        """)
        b_layout.addWidget(lbl_table)

        # Table
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Depth (MD)", "Type", "Dip (°)", "Azimuth (°)", "Aperture", "Confidence", "Notes"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setMaximumHeight(140)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                gridline-color: {COLORS['border_light']};
                background-color: {COLORS['bg_main']};
                alternate-background-color: {COLORS['bg_panel']};
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS['accent_light']};
                color: {COLORS['text_primary']};
            }}
        """)
        b_layout.addWidget(self.table)

        # Status Bar with Icons
        status_layout = QtWidgets.QHBoxLayout()
        status_layout.setSpacing(8)

        # Status Indicator
        self.status_indicator = QtWidgets.QLabel("●")
        self.status_indicator.setStyleSheet(f"color: {COLORS['success']}; font-size: 14pt;")
        self.status_indicator.setMaximumWidth(20)

        # Status Text
        self.status_lbl = QtWidgets.QLabel("Status: Ready • Image analysis module initialized")
        self.status_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 9pt;")

        status_layout.addWidget(self.status_indicator)
        status_layout.addWidget(self.status_lbl)
        status_layout.addStretch()

        b_layout.addLayout(status_layout)

        self.main_layout.addWidget(self.bottom_widget)

    def prompt_load_image(self):
        options = QtWidgets.QFileDialog.Options()
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Borehole Image Dataset", "",
            "LAS Files (*.las);;NumPy Arrays (*.npy);;Images (*.png *.jpg);;All Files (*)",
            options=options
        )
        if file_path:
            self._set_status(f"Loading: {os.path.basename(file_path)}...", "info")
            QtWidgets.QApplication.processEvents()
            try:
                if file_path.lower().endswith('.las'):
                    las = lasio.read(file_path)
                    df = las.df()

                    well_name = las.well.WELL.value if hasattr(las.well, 'WELL') and las.well.WELL.value else os.path.basename(file_path)
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
                        self, "Select Image Log", "Choose image log to display:", available_images, 0, False
                    )
                    if not ok:
                        self._set_status("Load aborted", "warning")
                        return

                    if "Density" in choice:
                        img_df = df[azid_cols].dropna(how='all')
                        self.lbl_type.setText("Type: LWD Azimuthal Density")
                        # Basic normalisation for viz
                        vals = img_df.values
                        p1, p99 = np.percentile(vals[~np.isnan(vals)], (1, 99))
                        vals = np.clip(vals, p1, p99)
                    else:
                        img_df = df[azig_cols].dropna(how='all')
                        self.lbl_type.setText("Type: LWD Azimuthal Gamma Ray")
                        vals = img_df.values

                    depth_start = img_df.index.min()
                    depth_end = img_df.index.max()
                    data = vals

                elif file_path.endswith('.npy'):
                    data = np.load(file_path)
                    depth_start, ok1 = QtWidgets.QInputDialog.getDouble(self, "Depth Start", "Enter Top Depth (MD) [m]:", 1000.0, -10000, 10000, 2)
                    if not ok1: return
                    depth_end, ok2 = QtWidgets.QInputDialog.getDouble(self, "Depth End", "Enter Bottom Depth (MD) [m]:", 1100.0, -10000, 10000, 2)
                    if not ok2: return
                    self.lbl_type.setText("Type: Generic NumPy Array")
                else:
                    data = np.random.rand(1000, 360) * 255
                    depth_start, ok1 = QtWidgets.QInputDialog.getDouble(self, "Depth Start", "Enter Top Depth (MD) [m]:", 1000.0, 0, 10000, 2)
                    if not ok1: return
                    depth_end, ok2 = QtWidgets.QInputDialog.getDouble(self, "Depth End", "Enter Bottom Depth (MD) [m]:", 1100.0, 0, 10000, 2)
                    if not ok2: return
                    self.lbl_type.setText("Type: Sample Visualization")

                self.viewer_engine.load_image(data, depth_start, depth_end)
                self.lbl_depth_range.setText(f"Depth Range: {depth_start:.1f}—{depth_end:.1f} m")
                self.lbl_shape.setText(f"Resolution: {data.shape[1]} sectors × {data.shape[0]} samples")
                self._set_status(f"✓ Dataset loaded: {os.path.basename(file_path)}", "success")

            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self, "Image Engine Error",
                    f"Failed to load and parse image:\n{str(e)}",
                    QtWidgets.QMessageBox.Ok
                )
                self._set_status("✗ Error loading file", "error")

    def change_colormap(self, cmap_name):
        self.viewer_engine.set_colormap(cmap_name)
        self._set_status(f"Colormap: {cmap_name}", "info")

    def _set_status(self, message, status_type="info"):
        """Update status bar with colored indicator"""
        self.status_lbl.setText(f"Status: {message}")
        if status_type == "success":
            self.status_indicator.setStyleSheet(f"color: {COLORS['success']}; font-size: 14pt;")
        elif status_type == "error":
            self.status_indicator.setStyleSheet(f"color: {COLORS['danger']}; font-size: 14pt;")
        elif status_type == "warning":
            self.status_indicator.setStyleSheet(f"color: {COLORS['warning']}; font-size: 14pt;")
        else:
            self.status_indicator.setStyleSheet(f"color: {COLORS['accent_primary']}; font-size: 14pt;")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = ImageAnalysisTab()
    window.resize(1400, 900)
    window.show()
    sys.exit(app.exec_())
