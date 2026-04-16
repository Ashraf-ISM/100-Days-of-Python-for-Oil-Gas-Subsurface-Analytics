import sys

with open("notebooks/day-25-petrophysics/services/interpretation_service.py", "r") as f:
    lines = f.readlines()

out = []
in_build = False
for i, line in enumerate(lines):
    if line.startswith("    def _build_porosity_workspace(self) -> None:"):
        in_build = True
        out.append("""    def _init_porosity_bindings(self) -> None:
        if getattr(self.ui, "_porosity_workspace_built", False):
            return

        poroPlotsCanvas = getattr(self.ui, "poroPlotsCanvas", None)
        if poroPlotsCanvas is not None:
            layout = poroPlotsCanvas.layout()
            if layout is None:
                layout = QtWidgets.QVBoxLayout(poroPlotsCanvas)
                layout.setContentsMargins(0, 0, 0, 0)
            
            tab_widget = QtWidgets.QTabWidget(poroPlotsCanvas)
            self.ui.tabPhiLogView = QtWidgets.QWidget(tab_widget)
            self.ui.tabPhiCrossplot = QtWidgets.QWidget(tab_widget)
            self.ui.tabPhiHistogram = QtWidgets.QWidget(tab_widget)
            tab_widget.addTab(self.ui.tabPhiLogView, "Log View")
            tab_widget.addTab(self.ui.tabPhiCrossplot, "Crossplot")
            tab_widget.addTab(self.ui.tabPhiHistogram, "Histogram")
            layout.addWidget(tab_widget)
            
            for page_name, page_widget in (
                ("log", self.ui.tabPhiLogView),
                ("crossplot", self.ui.tabPhiCrossplot),
                ("histogram", self.ui.tabPhiHistogram),
            ):
                page_layout = QtWidgets.QVBoxLayout(page_widget)
                page_layout.setContentsMargins(0, 0, 0, 0)
                host = QtWidgets.QFrame(page_widget)
                host.setMinimumHeight(340)
                host_layout = QtWidgets.QVBoxLayout(host)
                host_layout.setContentsMargins(10, 10, 10, 10)
                page_layout.addWidget(host)
                if page_name == "log":
                    self._porosity_log_host = host
                elif page_name == "crossplot":
                    self._porosity_crossplot_host = host
                else:
                    self._porosity_hist_host = host
                    
        self._porosity_activity_list = None 
        
        self.ui.comboPoroDepth = getattr(self.ui, "comboPoroDepth", None)
        self.ui.comboPoroRhob = getattr(self.ui, "comboPoroRhob", None)
        self.ui.comboPoroNphi = getattr(self.ui, "comboPoroNphi", None)
        self.ui.comboPoroDt = getattr(self.ui, "comboPoroDt", None)
        self.ui.comboPoroGr = getattr(self.ui, "comboPoroGr", None)

        self.ui.refresh_porosity_tab = self.refresh_porosity_workspace
        if getattr(self.ui, "btnCalcPorosityRun", None) is not None:
             self.ui.btnCalcPorosityRun.clicked.connect(self.compute_phi)

        self.ui._porosity_workspace_built = True
        self.refresh_porosity_workspace()
""")
    elif in_build and line.startswith("    def refresh_porosity_workspace(self) -> None:"):
        in_build = False
        out.append(line)
    elif not in_build:
        out.append(line)

with open("notebooks/day-25-petrophysics/services/interpretation_service.py", "w") as f:
    f.writelines(out)
