from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5 import uic
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
UI_DIR = ROOT_DIR / "ui"
UI_FILE = "data_downloader.ui"

class DataDownloaderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        ui_path = UI_DIR / UI_FILE
        uic.loadUi(str(ui_path), self)
        
        # Connect the site buttons
        # The object names are generated as btnNLOG, btnNPD, etc.
        self._connect_buttons()
        
        # Connect close button
        if hasattr(self, 'btnClose'):
            self.btnClose.clicked.connect(self.accept)

    def _connect_buttons(self):
        urls = {
            "btnNLOG": "https://www.nlog.nl/en",
            "btnNPD": "https://www.sodir.no/en/data-and-services/",
            "btnEquinor": "https://www.equinor.com/energy/volve-data-sharing",
            "btnNOPIMS": "https://nopims.dmp.wa.gov.au/nopims/",
            "btnUKNDR": "https://ndr.nstauthority.co.uk/",
            "btnKGS": "https://www.kgs.ku.edu/Magellan/Logs/index.html",
            "btnParihaka": "https://data.nzpam.govt.nz/"
        }
        
        for btn_name, url in urls.items():
            if hasattr(self, btn_name):
                btn = getattr(self, btn_name)
                # Ensure the url is captured by lambda
                btn.clicked.connect(lambda checked, u=url: QDesktopServices.openUrl(QUrl(u)))

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dlg = DataDownloaderDialog()
    dlg.show()
    sys.exit(app.exec_())
