from PyQt5 import QtWidgets, QtCore


class AboutHelpDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("PetroARX Information")
        self.setMinimumSize(600, 450)
        self.setStyleSheet("""
            QDialog {
                background-color: #F4F7FB;
            }
            QLabel {
                font-size: 11pt;
            }
            QTabWidget::pane {
                border: 1px solid #D0D7E2;
                background: white;
                border-radius: 8px;
            }
        """)

        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # 🔷 Title
        title = QtWidgets.QLabel("PetroARX")
        title.setStyleSheet("font-size: 18pt; font-weight: bold; color: #1B3A57;")
        title.setAlignment(QtCore.Qt.AlignCenter)

        subtitle = QtWidgets.QLabel("Petrophysics Interpretation Platform")
        subtitle.setAlignment(QtCore.Qt.AlignCenter)
        subtitle.setStyleSheet("color: gray; font-size: 10pt;")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        # 🔷 Tabs
        tabs = QtWidgets.QTabWidget()

        tabs.addTab(self._about_tab(), "About")
        tabs.addTab(self._help_tab(), "Help")

        layout.addWidget(tabs)

        # 🔷 Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()

        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #1B5E20;
                color: white;
                padding: 6px 14px;
                border-radius: 6px;
            }
        """)

        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    # --------------------------
    # ABOUT TAB
    # --------------------------
    def _about_tab(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        text = QtWidgets.QLabel("""
        <b>PetroARX</b> is a modern desktop platform designed for advanced 
        <b>petrophysical interpretation</b> and <b>multi-well analysis</b>.

        <br><br>

        <b>Core Capabilities:</b>
        <ul>
            <li>Well log loading and curve management</li>
            <li>Quality control workflows</li>
            <li>Multi-track plotting and crossplots</li>
            <li>Porosity, Vsh, Sw, permeability, and net pay</li>
            <li>Advanced interpretation modules (pore pressure, geomechanics)</li>
        </ul>

        <br>
        <b>Version:</b> 1.0
        """)

        text.setWordWrap(True)
        layout.addWidget(text)

        return widget

    # --------------------------
    # HELP TAB
    # --------------------------
    def _help_tab(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        text = QtWidgets.QLabel("""
        <b>Recommended Workflow:</b>

        <ol>
            <li>Import well data (LAS / CSV)</li>
            <li>Perform Quality Control (QC)</li>
            <li>Run interpretation modules (Vsh, Phi, Sw)</li>
            <li>Analyze plots and export results</li>
        </ol>

        <br>

        <b>Tips:</b>
        <ul>
            <li>Always run QC before interpretation</li>
            <li>Check depth consistency</li>
            <li>Validate logs before calculations</li>
        </ul>

        <br>
        Refer to documentation for detailed workflows.
        """)

        text.setWordWrap(True)
        layout.addWidget(text)

        return widget