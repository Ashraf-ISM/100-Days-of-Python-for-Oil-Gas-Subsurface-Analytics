from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QWidget, QFrame)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont, QDesktopServices

class DataDownloaderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Open Data Sources - Well Logs & Seismic")
        self.resize(600, 500)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #f4f6f9;
            }
            QLabel#header {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px 0;
            }
            QFrame.DatasetFrame {
                background-color: #ffffff;
                border: 1px solid #dcdde1;
                border-radius: 6px;
                padding: 10px;
                margin-bottom: 10px;
            }
            QLabel.DatasetTitle {
                font-size: 14px;
                font-weight: bold;
                color: #192a56;
            }
            QLabel.DatasetDesc {
                font-size: 12px;
                color: #7f8fa6;
            }
            QPushButton.LinkButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton.LinkButton:hover {
                background-color: #2980b9;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        
        header_lbl = QLabel("Public Subsurface Data Repositories")
        header_lbl.setObjectName("header")
        header_lbl.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header_lbl)
        
        # Scroll area for links
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        scroll_content = QWidget()
        self.content_layout = QVBoxLayout(scroll_content)
        self.content_layout.setAlignment(Qt.AlignTop)
        
        self.add_data_source(
            "NLOG - Netherlands Oil and Gas Portal",
            "Publicly available data from the Dutch sector, including well logs, seismic surveys, and reports.",
            "https://www.nlog.nl/en"
        )
        
        self.add_data_source(
            "Norwegian Offshore Directorate (NPD / Diskos)",
            "Extensive data spanning the Norwegian continental shelf: wellbores, field data, and seismic.",
            "https://www.sodir.no/en/data-and-services/"
        )
        
        self.add_data_source(
            "Equinor Volve Data Village",
            "A complete open dataset from the Volve field including well logs, petrophysical evaluations, and seismic data.",
            "https://www.equinor.com/energy/volve-data-sharing"
        )
        
        self.add_data_source(
            "NOPIMS (Australia)",
            "National Offshore Petroleum Information Management System. A vast repository of Australian offshore data.",
            "https://nopims.dmp.wa.gov.au/nopims/"
        )
        
        self.add_data_source(
            "UK NSTA National Data Repository (NDR)",
            "The UK's central repository for offshore petroleum data.",
            "https://ndr.nstauthority.co.uk/"
        )

        self.add_data_source(
            "KGS - Kansas Geological Survey",
            "Huge database of wireline logs (LAS files) for the state of Kansas.",
            "https://www.kgs.ku.edu/Magellan/Logs/index.html"
        )

        self.add_data_source(
            "Parihaka-3D Seismic Data (NZ)",
            "Open data available from the New Zealand Petroleum and Minerals (NZPAM) online database via Crown Minerals.",
            "https://data.nzpam.govt.nz/"
        )
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setFixedWidth(100)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #7f8fa6;
                color: white;
                padding: 6px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #718093; }
        """)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        main_layout.addLayout(btn_layout)
        
    def add_data_source(self, title, desc, url):
        frame = QFrame()
        frame.setProperty("class", "DatasetFrame")
        layout = QHBoxLayout(frame)
        
        text_layout = QVBoxLayout()
        t_lbl = QLabel(title)
        t_lbl.setProperty("class", "DatasetTitle")
        d_lbl = QLabel(desc)
        d_lbl.setProperty("class", "DatasetDesc")
        d_lbl.setWordWrap(True)
        
        text_layout.addWidget(t_lbl)
        text_layout.addWidget(d_lbl)
        
        btn = QPushButton("Go Context")
        btn.setText("Visit Site")
        btn.setProperty("class", "LinkButton")
        btn.clicked.connect(lambda _, u=url: QDesktopServices.openUrl(QUrl(u)))
        
        layout.addLayout(text_layout)
        layout.addWidget(btn, alignment=Qt.AlignRight | Qt.AlignVCenter)
        
        self.content_layout.addWidget(frame)

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dlg = DataDownloaderDialog()
    dlg.show()
    sys.exit(app.exec_())
