# Day 03 – Exploring the `seisio` Library for Seismic Data

## Introduction

On Day 03 of my **100 Days of Python for Oil & Gas / Geophysics** journey, I explored the **`seisio` library**, a Python package designed for reading and writing seismic data in common geophysical formats.

In geophysics and seismic processing, data are usually stored in formats such as:

- **SEG-Y**
- **Seismic Unix (SU)**
- **SEG2**

The `seisio` library provides a **simple and flexible way to perform I/O operations on these seismic files using Python**.

The library was created mainly for **students and researchers in geophysics**, making it easier to experiment with seismic data without complicated dependencies.

---

## What is `seisio`?

`seisio` is a **pure Python seismic I/O module** that allows users to:

- Read seismic traces
- Access trace headers
- Write seismic data files
- Process seismic datasets efficiently

It supports both **2D and 3D seismic data** and does **not assume any fixed geometry**, making it flexible for many types of seismic datasets.

---

## Supported Seismic Data Formats

`seisio` can work with several standard seismic formats used in geophysical exploration:

| Format | Description |
|------|------|
| **SEG-Y** | Standard seismic data format used in exploration geophysics |
| **SU (Seismic Unix)** | Open seismic processing format widely used in research |
| **SEG2** | Often used for near-surface seismic surveys |

---

## Key Features of `seisio`

Some important capabilities of the library include:

- Read and write **SEG-Y files (including SEG-Y rev. 2.1)**
- Read and write **Seismic Unix (SU) files**
- Read **SEG2 seismic data**
- Supports **IBM and IEEE floating point formats**
- **Lazy loading** (data is loaded only when required)
- Automatic detection of:
  - **Endian byte order**
  - **Text header encoding (ASCII / EBCDIC)**
- Flexible **trace header customization**
- Ability to read traces in **any order**
- Efficient handling of **large seismic datasets**

---

## Installation

The library can be installed using pip.

```bash
pip install seisio