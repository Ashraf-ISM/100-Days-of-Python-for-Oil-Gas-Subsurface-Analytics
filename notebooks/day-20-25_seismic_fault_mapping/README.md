# 🌍 Fault Mapping Using Seismic Attributes
### A Complete Python Workflow — From Raw Seismic to Interpreted Fault Maps

---

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python)](https://python.org)
[![NumPy](https://img.shields.io/badge/NumPy-2.x-blue?style=flat-square&logo=numpy)](https://numpy.org)
[![SciPy](https://img.shields.io/badge/SciPy-1.x-blue?style=flat-square)](https://scipy.org)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.x-orange?style=flat-square&logo=scikit-learn)](https://scikit-learn.org)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green?style=flat-square&logo=opencv)](https://opencv.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

---

## 📋 Overview

This project implements a **complete, production-style Python pipeline** for detecting and mapping geological faults in 3D seismic reflection data using classical signal processing, seismic attribute analysis, and supervised/unsupervised machine learning.

Faults are planar discontinuities in subsurface rock formations caused by tectonic stress. Accurate fault mapping is essential for:

- **Petroleum exploration** — fault-bounded traps are primary hydrocarbon targets
- **Seismic hazard assessment** — active fault identification for earthquake risk
- **Carbon capture & storage** — ensuring structural integrity of CO₂ repositories
- **Geothermal energy** — fault zones as preferential fluid pathways
- **Groundwater management** — fault-controlled aquifer compartmentalization

---

## 🗺️ Workflow Roadmap

```
Raw Seismic (SEG-Y / Synthetic)
        │
        ▼
┌───────────────────────┐
│  1. DATA LOADING      │  segyio, numpy
│     & PREPROCESSING   │  Normalization, QC
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐
│  2. ATTRIBUTE         │  Envelope, Phase, Freq  (Hilbert)
│     COMPUTATION       │  RMS, AAA               (Windowed)
│     (16 attributes)   │  Coherence/Similarity   (Structural)
│                       │  Dip, Azimuth           (Structure Tensor)
│                       │  Curvature              (2nd derivatives)
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐
│  3. FAULT             │  Sobel / Laplacian
│     ENHANCEMENT       │  Canny Edge Detector
│                       │  Fault Likelihood (plane-scanning)
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐
│  4. MACHINE           │  Feature Engineering (9 attributes)
│     LEARNING          │  PCA — dimensionality analysis
│                       │  K-Means (unsupervised, k=2)
│                       │  Random Forest (supervised, 100 trees)
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐
│  5. POST-PROCESSING   │  Thresholding
│     & ENSEMBLE        │  Morphological clean-up
│                       │  Connected component filtering
│                       │  Weighted ensemble combination
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐
│  6. VISUALIZATION     │  2D Time Slices & Inline Sections
│     & FAULT MAP       │  Attribute overlays
│                       │  3D scatter fault surfaces
│                       │  Dice score comparison
└───────────────────────┘
```

---

## 📁 Repository Structure

```
fault_mapping_seismic_attributes/
│
├── fault_mapping_seismic_attributes.ipynb   # 🔑 Main Jupyter Notebook
├── README.md                                # This file
│
├── data/                                    # (Optional) Real SEG-Y data
│   └── your_seismic.segy
│
├── outputs/                                 # Generated figures & results
│   ├── fig_01_raw_seismic.png
│   ├── fig_02_attribute_dashboard.png
│   ├── fig_03_fault_enhancement.png
│   ├── fig_04_correlation.png
│   ├── fig_05_pca.png
│   ├── fig_06_rf_results.png
│   ├── fig_07_final_fault_map.png
│   ├── fig_08_inline_overlay.png
│   └── fig_09_3d_faults.png
│
└── requirements.txt                         # Python dependencies
```

---

## 🔬 Seismic Attributes Computed

### Amplitude Attributes
| Attribute | Description | Fault Sensitivity |
|-----------|-------------|------------------|
| **Envelope** | Instantaneous amplitude via Hilbert transform | Moderate |
| **RMS Amplitude** | Root-mean-square in sliding time window | Low |
| **Average Absolute Amplitude** | Mean \|A\| in time window | Low |

### Instantaneous Attributes (Hilbert Transform)
| Attribute | Description | Fault Sensitivity |
|-----------|-------------|------------------|
| **Instantaneous Phase** | Phase angle of analytic signal | High |
| **Cosine of Phase** | Structural continuity indicator | High |
| **Instantaneous Frequency** | Temporal derivative of phase | Moderate |

### Geometric / Structural Attributes ← *Primary fault indicators*
| Attribute | Description | Fault Sensitivity |
|-----------|-------------|------------------|
| **Coherence / Similarity** | Lateral trace similarity (0–1) | **Very High** |
| **1 − Coherence (Incoherence)** | Discontinuity measure | **Very High** |
| **Structural Dip (°)** | Local reflector inclination | High |
| **Azimuth (°)** | Dip direction from structure tensor | Moderate |
| **Mean Curvature** | Surface bending (mean) | High |
| **Gaussian Curvature** | Surface bending (Gauss) | High |
| **Shape Index** | −1=bowl, 0=saddle, +1=dome | Moderate |

### Edge / Enhancement Attributes
| Attribute | Description | Fault Sensitivity |
|-----------|-------------|------------------|
| **Sobel Magnitude** | Gradient edge detector | High |
| **Laplacian** | Second-order edge sharpening | High |
| **Fault Likelihood** | Oriented plane-scanning score | **Very High** |
| **Canny Edges** | Hysteresis-thresholded edges | High |

---

## 🤖 Machine Learning Methods

### Unsupervised: K-Means Clustering
- **Input**: 9 seismic attribute features per voxel
- **k = 2** (fault / background)
- Fault cluster identified by maximum mean incoherence
- No labelled training data required

### Supervised: Random Forest
- **Input**: 9 features, synthetic ground truth labels
- 100 decision trees, balanced class weights
- Feature importance ranking provided
- Outputs per-voxel fault probability [0, 1]

### Ensemble
- Weighted combination: `0.35·RF + 0.25·KMeans + 0.25·FL + 0.15·Incoherence`
- Post-processed with morphological closing and component filtering
- Achieves best Dice score vs ground truth

---

## ⚙️ Requirements

### Core Dependencies

```
numpy>=1.24
scipy>=1.10
scikit-learn>=1.2
matplotlib>=3.7
pandas>=2.0
opencv-python>=4.7
seaborn>=0.12
```

### Optional (Real Seismic Data)

```
segyio>=1.9        # SEG-Y file reading
obspy>=1.4         # Seismic data processing
```

---

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/fault-mapping-seismic.git
cd fault-mapping-seismic
```

### 2. Create a Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows
```

### 3. Install Dependencies

```bash
pip install numpy scipy scikit-learn matplotlib pandas opencv-python seaborn
pip install segyio               # For real SEG-Y data (optional)
pip install jupyter              # To run the notebook
```

### 4. Launch the Notebook

```bash
jupyter notebook fault_mapping_seismic_attributes.ipynb
# or in VS Code:
code fault_mapping_seismic_attributes.ipynb
```

---

## 📦 Using Real SEG-Y Data

Replace the synthetic data generation in **Step 2** of the notebook with:

```python
import segyio

SEGY_FILE = 'data/your_seismic.segy'

with segyio.open(SEGY_FILE, iline=189, xline=193, strict=False) as f:
    seismic_cube = segyio.tools.cube(f)   # shape: (n_il, n_xl, n_t)
    dt = segyio.tools.dt(f) / 1e6         # sample interval in seconds
    ilines = f.ilines
    xlines = f.xlines
    t_samples = f.samples                  # two-way time in ms

NX, NY, NZ = seismic_cube.shape
DT = dt

print(f"Volume loaded: {NX} IL × {NY} XL × {NZ} samples")
print(f"Time range: {t_samples[0]:.0f} – {t_samples[-1]:.0f} ms")
print(f"Sample interval: {dt*1000:.2f} ms")
```

**Public SEG-Y datasets for testing:**
- [Penobscot 3D](https://wiki.seg.org/wiki/Penobscot_3D_survey) — Open seismic repository
- [Teapot Dome 3D](https://wiki.seg.org/wiki/Teapot_Dome_3D_survey) — RMOTC public dataset
- [Kerry-3D (New Zealand)](https://www.nzpam.govt.nz) — GNS open data

---

## 📊 Expected Outputs

After running the complete notebook, you will have:

| Output | Description |
|--------|-------------|
| `fig_01_raw_seismic.png` | Inline, crossline, time-slice views + amplitude histogram |
| `fig_02_attribute_dashboard.png` | 9-panel attribute comparison map |
| `fig_03_fault_enhancement.png` | 6-panel edge/fault enhancement comparison |
| `fig_04_correlation.png` | Attribute cross-correlation matrix |
| `fig_05_pca.png` | PCA scatter + scree plot |
| `fig_06_rf_results.png` | Feature importances + confusion matrix |
| `fig_07_final_fault_map.png` | All methods compared + Dice score bar chart |
| `fig_08_inline_overlay.png` | Inline section with fault overlays |
| `fig_09_3d_faults.png` | 3D fault surface visualization |

---

## 🔭 Advanced Extensions

### Deep Learning (Recommended for Production)

For large 3D seismic volumes, convolutional neural networks significantly outperform classical ML:

| Model | Architecture | Reference |
|-------|-------------|-----------|
| **FaultSeg3D** | 3D U-Net | Wu et al. (2019), *Geophysics* |
| **SegFault** | Transformer + CNN | Jiang et al. (2021) |
| **FaultNet** | 2D CNN per time slice | Guitton (2018) |

```bash
# FaultSeg3D (PyTorch):
git clone https://github.com/xinwucwp/faultSeg
```

### Horizon-Constrained Attributes

For stratigraphically-complex areas, compute attributes within **horizon-parallel windows** rather than fixed time windows to avoid cross-cutting artefacts.

### Ant Tracking (Petrel/OpendTect)

Ant tracking iteratively traces fault planes from seed points using a biologically-inspired path-following algorithm. Available in commercial packages (Schlumberger Petrel) and OpendTect (open-source).

---

## 📚 Key References

1. **Bahorich & Farmer (1995)** — *"3-D seismic discontinuity for faults and stratigraphic features"* — The Leading Edge
2. **Gersztenkorn & Marfurt (1999)** — *"Eigenstructure-based coherence computations"* — Geophysics
3. **Roberts (2001)** — *"Curvature attributes and their application to 3D interpreted horizons"* — First Break
4. **Hale (2013)** — *"Methods to compute fault images, extract fault surfaces, and estimate fault throws from 3D seismic images"* — Geophysics
5. **Wu et al. (2019)** — *"FaultSeg3D: Using synthetic datasets to train an end-to-end convolutional neural network for 3D seismic fault segmentation"* — Geophysics
6. **Tingdahl & de Rooij (2005)** — *"Semi-automatic detection of faults in 3D seismic data"* — Geophysical Prospecting

---

## 🙋 Author

**Ashraf**
Seismic Processing & Machine Learning Workflows
Earthquake Catalog Declustering | Seismic Attribute Analysis

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

> *"The Earth is not only the mother of all creatures but also the best seismograph ever built."*
