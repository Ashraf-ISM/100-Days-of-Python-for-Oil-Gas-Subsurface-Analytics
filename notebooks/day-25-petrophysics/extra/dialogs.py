from PyQt5 import QtWidgets


def show_about(parent):
    """Display About dialog for PetroARX."""

    message = """
    <h2>PetroARX</h2>

    <p>
        A modern desktop platform for <b>petrophysical interpretation</b> 
        and <b>multi-well analysis</b>.
    </p>

    <hr>

    <h3>Core Capabilities</h3>
    <ul>
        <li><b>Data Management:</b> Well log loading, curve handling, and QC workflows</li>
        <li><b>Visualization:</b> Multi-track plotting and crossplot analysis</li>
        <li><b>Petrophysical Evaluation:</b> Vsh, Porosity, Permeability, Net Pay</li>
        <li><b>Saturation Analysis:</b> Archie, Simandoux, Modified Simandoux, Indonesia</li>
    </ul>

    <hr>

    <h3>Quick Help</h3>
    <p>Go to <b>Help → Documentation</b> for detailed workflows.</p>

    <p style="color: gray;">Version 1.0</p>
    """

    QtWidgets.QMessageBox.about(parent, "About PetroARX", message)


def show_help(parent):
    """Display Help dialog."""

    message = """
    <h2>PetroARX Help</h2>

    <p><b>Recommended Workflow:</b></p>

    <ol>
        <li>Import well data (LAS / CSV / SEGY)</li>
        <li>Perform Quality Control (QC)</li>
        <li>Run interpretation modules (Vsh, Phi, Sw, Net Pay)</li>
        <li>Analyze plots and export results</li>
    </ol>

    <hr>

    <p>
        Refer to <b>QUICKSTART.md</b> and 
        <b>PROJECT_MANAGEMENT_GUIDE.md</b> for detailed guidance.
    </p>
    """

    QtWidgets.QMessageBox.information(parent, "PetroARX Documentation", message)