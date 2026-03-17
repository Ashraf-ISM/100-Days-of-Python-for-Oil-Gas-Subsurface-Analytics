# Day 04 — Exploring the Bruges Library for Geophysics

> **100 Days of Python for Oil & Gas Subsurface Analytics**  
> `#Day04` · `#Python` · `#Geophysics` · `#SeismicAnalysis` · `#Bruges`

---

## Overview

On **Day 04** of my *100 Days of Python for Oil & Gas Subsurface Analytics* journey, I explored **Bruges** — a Python library developed by [Agile Scientific](https://github.com/agilescientific) that provides clean, ready-to-use implementations of essential geophysical equations.

Bruges can be thought of as a **geoscience toolbox**: a curated collection of mathematical functions commonly used in seismic analysis, rock physics, and petrophysics. Instead of manually coding complex equations such as Aki–Richards or Zoeppritz approximations, Bruges offers vetted, reusable implementations that accelerate experimentation and analysis.

---

## What is Bruges?

Bruges is essentially a **bag of useful geoscience equations implemented in Python**. It is lightweight, well-documented, and designed to integrate seamlessly with the broader scientific Python ecosystem.

### Core Capabilities

| Category | Examples |
|---|---|
| **Seismic Reflectivity** | Aki–Richards, Zoeppritz approximations |
| **Wavelet Generation** | Ricker, Ormsby, Klauder wavelets |
| **Rock Physics** | Fluid substitution, elastic moduli |
| **Seismic Processing** | Convolution, filtering utilities |
| **Petrophysics** | Porosity-velocity relationships |

Bruges is widely used by students, researchers, and geoscientists working in seismic interpretation and subsurface modeling.

---

## Installation

```bash
pip install bruges
```

---

## Example: Generating a Seismic Wavelet

One of the most common tasks in seismic processing is generating a wavelet. Bruges provides several built-in wavelet generators, including the **Ormsby wavelet**.

```python
import bruges as bg

# Generate an Ormsby wavelet
w, t = bg.filters.ormsby(
    duration=0.256,   # Total duration in seconds
    dt=0.002,         # Sample interval in seconds
    f=[5, 10, 40, 80] # Frequency band: f1, f2, f3, f4 in Hz
)
```

### Output

| Variable | Description |
|---|---|
| `w` | Wavelet amplitude values |
| `t` | Corresponding time values (seconds) |

These arrays can be directly used for:
- Synthetic seismic modeling
- Convolution with a reflectivity series
- Wavelet visualization and QC

---

## Why Bruges is Useful in Geophysics

Bruges simplifies geophysical workflows by providing:

- ✅ **Ready implementations** of complex, well-known equations
- ✅ **Rapid prototyping** of seismic models without reinventing the wheel
- ✅ **Lightweight integration** with NumPy, SciPy, and Matplotlib
- ✅ **Academic credibility** — widely adopted in research and education

---

## Repository Information

| Attribute | Details |
|---|---|
| **Language** | Python |
| **License** | Apache-2.0 |
| **Developed by** | [Agile Scientific](https://github.com/agilescientific) |
| **Focus Areas** | Seismology · Geophysics · Petrophysics |

---

## Key Links

- � **Documentation:** [code.agilescientific.com/bruges](https://code.agilescientific.com/bruges)
- � **PyPI Package:** [pypi.org/project/bruges](https://pypi.org/project/bruges/)
- � **GitHub Repository:** [github.com/agilescientific/bruges](https://github.com/agilescientific/bruges)

---

## Learning Outcome

Through this exploration, I learned how Python libraries like Bruges can **significantly simplify seismic modeling and geophysical computation**. It provides a powerful and accessible starting point for implementing:

- Reflectivity modeling
- Wavelet analysis and visualization
- Rock physics calculations in Python-based workflows

This is exactly the kind of tool that bridges the gap between theoretical geophysics and practical, code-driven subsurface analysis.

---

## Series Navigation

| Day | Topic |
|---|---|
| ← Previous | Day 03 |
| **Current** | **Day 04 — Bruges Library for Geophysics** |
| → Next | Day 05 |

---

*Part of the [100 Days of Python for Oil & Gas Subsurface Analytics](#) series.*