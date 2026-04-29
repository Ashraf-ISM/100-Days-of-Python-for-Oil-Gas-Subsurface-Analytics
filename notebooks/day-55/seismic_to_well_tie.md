# Day 55 — Seismic to Well Tie Using Python

## Project Overview

Seismic-to-well tie is one of the most important workflows in subsurface exploration because seismic data is recorded in **time domain**, while well logs are measured in **depth domain**.

This project builds a complete seismic-to-well tie workflow from scratch using Python:

- Read well logs (Sonic + Density)
- Compute acoustic impedance
- Calculate reflection coefficients
- Generate synthetic seismogram
- Extract seismic trace near well location
- Perform time-depth conversion
- Match synthetic with real seismic
- Evaluate tie quality

This workflow helps in:

- Horizon interpretation
- Reservoir characterization
- Stratigraphic correlation
- Well placement
- Seismic inversion preparation
- Reducing uncertainty in subsurface interpretation

---

# Why Seismic-Well Tie is Needed?

Seismic interpreters work in **Two Way Travel Time (TWT)**.

Well logs are recorded in **Depth (meters/feet)**.

Without tying both:

- Reservoir picked on seismic may not match actual reservoir depth
- Horizon mapping becomes inaccurate
- Fault interpretation may be wrong
- Inversion outputs become unreliable

Seismic-to-well tie bridges:

```text
Well Logs (Depth Domain)
        ↓
Rock Physics
        ↓
Synthetic Seismogram
        ↓
Time Domain Conversion
        ↓
Real Seismic Trace
        ↓
Correlation