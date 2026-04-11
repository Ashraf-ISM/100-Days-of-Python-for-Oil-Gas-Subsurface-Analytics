import sys
from pathlib import Path
from PyQt5.QtWidgets import QMainWindow, QApplication, QTableWidgetItem
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QDesktopServices
from PyQt5 import uic

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
UI_DIR = ROOT_DIR / "ui"
UI_FILE = "data_downloader.ui"

RAW_DATA = {
    "tableSeismic": [
        ("Equinor Volve Data Village", "Equinor", "SEGY / ZGY", "Norway - North Sea", "Free / Open Access", "https://www.equinor.com/energy/volve-data-sharing", "A complete open dataset from the Volve field including well logs, petrophysical evaluations, and seismic data."),
        ("Parihaka-3D Seismic Data", "NZPAM", "SEGY", "New Zealand", "Free / Open Access", "https://data.nzpam.govt.nz/", "Open data available from the New Zealand Petroleum and Minerals (NZPAM) online database via Crown Minerals."),
        ("SEAM Phase 1", "SEG", "SEGY", "Synthetic Model", "Paid / Licensed", "https://seg.org/", "SEG Advanced Modeling Corporation Phase 1 datasets for seismic imaging challenges.")
    ],
    "tableWellLog": [
        ("NLOG Open Data", "TNO - Netherlands", "LAS / DLIS / LIS", "Netherlands", "Free / Open Access", "https://www.nlog.nl/en", "Publicly available data from the Dutch sector, including well logs, seismic surveys, and reports."),
        ("NPD Diskos", "Norwegian Offshore Directorate", "LAS / DLIS", "Norway", "Free / Open Access", "https://www.sodir.no/en/data-and-services/", "Extensive data spanning the Norwegian continental shelf: wellbores, field data, and seismic."),
        ("KGS Well Log Database", "Kansas Geological Survey", "LAS", "Kansas, USA", "Free / Open Access", "https://www.kgs.ku.edu/Magellan/Logs/index.html", "Huge database of wireline logs (LAS files) for the state of Kansas."),
        ("NOPIMS", "Geoscience Australia", "LAS / DLIS", "Australia", "Free / Open Access", "https://nopims.dmp.wa.gov.au/nopims/", "National Offshore Petroleum Information Management System. A vast repository of Australian offshore data."),
        ("UK NDR", "NSTA", "LAS / DLIS / LIS", "UK North Sea", "Free / Open Access", "https://ndr.nstauthority.co.uk/", "The UK's central repository for offshore petroleum data.")
    ],
    "tableGeo": [
        ("USGS EarthExplorer", "USGS", "Shapefiles / GeoTIFF", "Global", "Free / Open Access", "https://earthexplorer.usgs.gov/", "Comprehensive USGS repository for Earth science data, satellite imagery, and maps."),
        ("OneGeology", "OneGeology", "WMS / WFS", "Global", "Free / Open Access", "http://www.onegeology.org/", "International initiative providing geological map data globally.")
    ],
    "tableGeophysical": [
        ("NOAA NCEI Magnetic/Gravity", "NOAA", "Grids / Point Data", "Global", "Free / Open Access", "https://www.ncei.noaa.gov/mgg/gravity/", "Marine gravity and magnetic data from NOAA National Centers for Environmental Information.")
    ],
    "tableSatellite": [
        ("Copernicus Open Access Hub", "ESA", "Multispectral", "Global", "Free / Open Access", "https://scihub.copernicus.eu/", "Sentinel-1 and Sentinel-2 satellite data for Earth observation."),
    ],
    "tableResearch": [
        ("Zenodo Subsurface", "CERN / Zenodo", "Various", "Global", "Free / Open Access", "https://zenodo.org/", "Open-access repository with various scientific research datasets and machine learning benchmarks.")
    ]
}

class DataDownloaderWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        ui_path = UI_DIR / UI_FILE
        uic.loadUi(str(ui_path), self)
        
        self.current_url = ""
        self._populate_tables()
        self._connect_signals()

    def _populate_tables(self):
        # We find each table by objectName, set its headers, and populate it
        for table_name, data in RAW_DATA.items():
            table = getattr(self, table_name, None)
            if not table:
                continue
            
            table.setRowCount(0)
            table.setColumnCount(6)
            table.setHorizontalHeaderLabels(["Resource Name", "Organization", "Data Format", "Coverage", "Access Type", "URL"])
            
            # Stretch the last section to fill available space
            table.horizontalHeader().setStretchLastSection(True)
            
            for row_idx, row_data in enumerate(data):
                table.insertRow(row_idx)
                for col_idx in range(6):
                    item = QTableWidgetItem(row_data[col_idx])
                    # Ensure items aren't editable
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    # We store the description into the first column item so we can retrieve it later
                    if col_idx == 0:
                        item.setData(Qt.UserRole, row_data[6]) 
                    table.setItem(row_idx, col_idx, item)
            
            table.resizeColumnsToContents()
            # Hook up click signal to update detail pane
            table.itemSelectionChanged.connect(lambda t=table: self._on_table_selection_changed(t))

    def _connect_signals(self):
        if hasattr(self, 'btnOpenBrowser'):
            self.btnOpenBrowser.clicked.connect(self._open_url)
        if hasattr(self, 'btnOpenInBrowserDetail'):
            self.btnOpenInBrowserDetail.clicked.connect(self._open_url)
            
        if hasattr(self, 'btnCopyLink'):
            self.btnCopyLink.clicked.connect(self._copy_link)
        if hasattr(self, 'btnCopyLinkDetail'):
            self.btnCopyLinkDetail.clicked.connect(self._copy_link)
            
        if hasattr(self, 'actionClose'):
            self.actionClose.triggered.connect(self.close)

    def _on_table_selection_changed(self, table):
        selected_items = table.selectedItems()
        if not selected_items:
            return
            
        row = selected_items[0].row()
        name = table.item(row, 0).text()
        desc = table.item(row, 0).data(Qt.UserRole)
        org = table.item(row, 1).text()
        fmt = table.item(row, 2).text()
        cov = table.item(row, 3).text()
        acc = table.item(row, 4).text()
        url = table.item(row, 5).text()
        
        self.current_url = url
        
        # Update details pane in the split view
        if hasattr(self, 'lbl_name_val'): self.lbl_name_val.setText(name)
        if hasattr(self, 'lbl_org_val'): self.lbl_org_val.setText(org)
        if hasattr(self, 'lbl_format_val'): self.lbl_format_val.setText(fmt)
        if hasattr(self, 'lbl_coverage_val'): self.lbl_coverage_val.setText(cov)
        if hasattr(self, 'lbl_access_val'): self.lbl_access_val.setText(acc)
        if hasattr(self, 'urlLineEdit'): self.urlLineEdit.setText(url)
        if hasattr(self, 'detailTextEdit'): self.detailTextEdit.setPlainText(desc)

    def _open_url(self):
        if self.current_url:
            QDesktopServices.openUrl(QUrl(self.current_url))
            
    def _copy_link(self):
        if self.current_url:
            cb = QApplication.clipboard()
            cb.setText(self.current_url)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = DataDownloaderWindow()
    win.show()
    sys.exit(app.exec_())
