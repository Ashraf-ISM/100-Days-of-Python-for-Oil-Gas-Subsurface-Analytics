from PyQt5.QtWidgets import QFileDialog, QMessageBox
from core.las_handler import load_las_file
from core.preprocessing import clean_data
from core.shale import compute_vsh
from core.porosity import compute_porosity
from core.saturation import compute_sw
from utils.plotting import plot_logs

class Controller:
    def __init__(self, ui):
        self.ui = ui
        self.df = None

    def load_las(self):
        file_path, _ = QFileDialog.getOpenFileName(self.ui, "Open LAS File", "", "LAS Files (*.las)")
        
        if not file_path:
            return

        try:
            self.df = load_las_file(file_path)
            self.df = clean_data(self.df)
            QMessageBox.information(self.ui, "Success", "LAS file loaded successfully!")
        except Exception as e:
            QMessageBox.critical(self.ui, "Error", str(e))

    def run_petrophysics(self):
        if self.df is None:
            QMessageBox.warning(self.ui, "Warning", "Load LAS file first!")
            return

        try:
            self.df["Vsh"] = compute_vsh(self.df["GR"])
            self.df["PHI"] = compute_porosity(self.df)
            self.df["Sw"] = compute_sw(self.df)

            plot_logs(self.df)

        except Exception as e:
            QMessageBox.critical(self.ui, "Error", str(e))
