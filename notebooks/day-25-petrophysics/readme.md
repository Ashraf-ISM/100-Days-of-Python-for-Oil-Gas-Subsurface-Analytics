# 🛢️ Petrophysics Workstation

### GUI-Based Well Log Analysis & Reservoir Evaluation Toolkit

---

## 📌 Overview

**Petrophysics Workstation** is a modular, GUI-based application designed for **well log analysis, petrophysical interpretation, and reservoir characterization**.

Built using **PyQt5 + Python**, this tool integrates core petrophysical workflows with a clean user interface, enabling users to:

* Load and visualize LAS well log data
* Perform petrophysical calculations
* Identify reservoir zones
* Analyze subsurface properties efficiently

---

## 🎯 Key Features

### 📂 Data Handling

* Load **LAS files** using `lasio`
* Automatic depth indexing and preprocessing
* Missing value handling and log normalization

---

### 📊 Log Visualization

* Multi-track plotting:

  * Gamma Ray (GR)
  * Porosity (PHI)
  * Water Saturation (Sw)
* Depth-based visualization with inverted axis

---

### 🧠 Petrophysical Analysis

#### 1. Volume of Shale (Vsh)

* Computed using Gamma Ray log

#### 2. Porosity (ϕ)

* Density porosity
* Neutron-density combination (if available)

#### 3. Water Saturation (Sw)

* Archie’s Equation implementation

#### 4. Reservoir Identification

* Net pay estimation based on:

  * Vsh cutoff
  * Porosity threshold
  * Water saturation limit

---

### 🏗️ Modular Architecture

The application is designed using a **clean, scalable architecture**:

```bash
petrophysics_app/
│
├── app/            # GUI & Controller
├── core/           # Petrophysical computations
├── ml/             # Machine learning (facies)
├── utils/          # Plotting & helpers
├── data/           # Sample datasets
├── main.py         # Entry point
```

---

## ⚙️ Installation

### 1. Clone Repository

```bash
git clone https://github.com/your-username/petrophysics-workstation.git
cd petrophysics-workstation
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## ▶️ Usage

```bash
python main.py
```

### Steps:

1. Click **Load LAS File**
2. Select your `.las` file
3. Click **Compute**
4. View petrophysical results

---

## 📁 Input Requirements

Your LAS file should contain:

* `GR` → Gamma Ray
* `RHOB` → Bulk Density
* `NPHI` → Neutron Porosity *(optional)*
* `RT` → True Resistivity

---

## 📈 Core Equations Used

### Porosity:

```text
ϕ = (ρ_matrix - ρ_bulk) / (ρ_matrix - ρ_fluid)
```

### Water Saturation (Archie):

```text
Sw = [(a * Rw) / (ϕ^m * Rt)]^(1/n)
```

---

## 🧪 Future Enhancements

* 📊 Embedded plotting inside GUI
* 📉 Crossplots (Density–Neutron, M-N plots)
* 🤖 ML-based facies classification
* 🌍 Multi-well comparison
* 📤 Export results (CSV / LAS)
* 📊 Volumetrics (OOIP / OGIP estimation)

---

## 🧑‍💻 Tech Stack

* Python
* PyQt5
* NumPy, Pandas
* Matplotlib
* lasio
* scikit-learn

---

## 🚀 Project Vision

This project aims to evolve into a **lightweight alternative to industry tools** such as:

* Schlumberger Techlog
* Interactive Petrophysics (IP)
* Petrel (log module)

---

## 👤 Author

**Md Ashraf**
M.Sc (Tech) Applied Geophysics
IIT (ISM) Dhanbad

---

## ⭐ Acknowledgment

Built as part of a hands-on initiative to bridge **geophysics + data science + software engineering** for real-world oil & gas applications.

---

## 📜 License

This project is for educational and research purposes.
You may modify and extend it for personal or academic use.

---
