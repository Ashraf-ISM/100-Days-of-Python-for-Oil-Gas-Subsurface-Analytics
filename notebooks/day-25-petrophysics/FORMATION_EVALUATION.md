# Formation Evaluation Tab — Code Structure & Frontend/Backend Connection

This document describes every component of the **Formation Evaluation** tab in
`PetroVisionPro`, how the UI widgets are wired to the Python back-end, and
exactly what happens when the user presses **Run Evaluation**.

---

## 1. Repository layout (relevant files)

```
notebooks/day-25-petrophysics/
├── app/
│   └── petrovision_main.py          # QMainWindow subclass; loads mainwindow.ui
├── controllers/
│   └── main_controller.py           # Wires every signal → service method
├── services/
│   └── formation_evaluation_service.py  # All FE business logic
├── calculations/
│   ├── vshale.py                    # Vsh methods (linear, Larionov, Clavier, Steiber)
│   ├── porosity.py                  # Density / combo porosity
│   ├── saturation.py                # Archie water saturation
│   ├── permeability.py              # Timur permeability
│   └── net_pay.py                   # Multi-cutoff net-pay flag
└── ui/
    └── mainwindow.ui                # Qt Designer XML; defines all widgets
```

---

## 2. Application startup

```
PetroVisionMainWindow.__init__()   (app/petrovision_main.py)
  │
  ├── uic.loadUi("mainwindow.ui", self)   ← parses XML, creates all QWidgets
  │     Every widget described in Section 3 is attached directly to `self`
  │     (the QMainWindow), e.g. self.btnRunFE, self.spinFEGRMin, …
  │
  ├── _embed_data_analysis_tab()          ← embeds dock into tab (unrelated)
  ├── _connect_tab_switches()             ← menu/toolbar → tab index jumps
  └── MainController(self)               ← wires all signals (Section 4)
```

---

## 3. Formation Evaluation UI widgets (`mainwindow.ui`)

The tab is defined as a `QWidget` named **`tabFormationevaluation`** inside
the central `QTabWidget` (`centralTabWidget`).  Its top-level layout is a
horizontal split: a narrow left **control panel** and a wide right **workspace**.

### 3.1 Left panel — `frameFEControls`

| Widget name | Type | Purpose |
|---|---|---|
| `lblFEControlsTitle` | QLabel | "Input Parameters" heading |
| **Well Selection group** (`groupFEWellSelection`) | | |
| `comboFeWell` | QComboBox | Active well selector; populated on data import |
| **Logs group** (`groupFELogs`) | | |
| `checkFEGR` | QCheckBox | Visual indicator — GR curve presence |
| `checkFERHOB` | QCheckBox | Visual indicator — RHOB curve presence |
| `checkFENPHI` | QCheckBox | Visual indicator — NPHI curve presence |
| `checkFERT` | QCheckBox | Visual indicator — RT curve presence |
| **Parameters group** (`groupFEVsh`) | | |
| `checkFEVsh` | QCheckBox | Enables Vsh computation |
| `spinFEGRMin` | QDoubleSpinBox | Clean-sand GR baseline (API) |
| `spinFEGRMax` | QDoubleSpinBox | Shale GR baseline (API) |
| `vshTypeComboBox` | QComboBox | Vsh calculation method (see §5.1) |
| **Porosity group** (`groupFEPorosity`) | | |
| `spinFERhoMa` | QDoubleSpinBox | Matrix density ρ_ma (g/cc) |
| `spinFERhoF` | QDoubleSpinBox | Fluid density ρ_f (g/cc) |
| **Water Saturation group** (`groupFESw`) | | |
| `spinFEArchieA` | QDoubleSpinBox | Archie tortuosity factor *a* |
| `spinFEArchieM` | QDoubleSpinBox | Archie cementation exponent *m* |
| `spinFEArchieN` | QDoubleSpinBox | Archie saturation exponent *n* |
| `spinFERw` | QDoubleSpinBox | Formation water resistivity *Rw* (ohm·m) |
| **Action buttons** | | |
| `btnRunFE` | QPushButton | Trigger full evaluation |
| `btnResetFE` | QPushButton | Clear results and placeholders |

### 3.2 Right panel — `frameFEWorkspace`

The workspace contains a nested `QTabWidget` (`tabFEViews`) with three sub-tabs:

#### Sub-tab 1 — **Log Tracks** (`tabFELogTracks`)

Top bar (`frameFETopControls`):

| Widget | Type | Purpose |
|---|---|---|
| `comboFEDepthPreset` | QComboBox | Full Well / Reservoir Window / Custom |
| `comboFEDepthUnit` | QComboBox | m / ft |
| `spinFEFrom` | QDoubleSpinBox | Depth-range start |
| `spinFETo` | QDoubleSpinBox | Depth-range end |
| `btnFERender` | QPushButton | Re-render plots for current depth range |

Four track frames rendered side-by-side:

| Frame | Placeholder label | Track rendered |
|---|---|---|
| `frameFEGammaTrack` | `lblFEGammaPlaceholder` | GR depth track |
| `frameFEVshTrack` | `lblFEVshPlaceholder` | Computed Vsh |
| `frameFEPorosityTrack` | `lblFEPorosityPlaceholder` | Porosity (PHI) |
| `frameFESwTrack` | `lblFESwPlaceholder` | Water saturation (Sw) |

Pay summary strip (`frameFEPaySummary`):

| Widget | Type | Purpose |
|---|---|---|
| `lblFENetIntervalValue` | QLabel | Net pay thickness (m) |
| `lblFEAvgPhiValue` | QLabel | Average porosity in pay |
| `lblFEAvgSwValue` | QLabel | Average Sw in pay |
| `tableFEPaySummary` | QTableWidget | Sampled rows: Depth, Vsh, phi, Sw, Flag |
| `frameFEPayChart` / `lblFEPayChartPlaceholder` | QFrame / QLabel | Net pay flag strip chart |

#### Sub-tab 2 — **Computed Logs** (`tabFEComputedLogs`)

| Widget | Purpose |
|---|---|
| `lblFEComputedPlaceholder` | Shows average stats after evaluation |

#### Sub-tab 3 — **Crossplots** (`tabFECrossplots`)

| Widget | Purpose |
|---|---|
| `lblFECrossplotPlaceholder` | Reserved for future phi-Vsh-Sw overlays |

---

## 4. Signal → slot wiring (`controllers/main_controller.py`)

`MainController.__init__` calls `_wire_actions()` which connects every relevant
Qt signal to a service method.  For the FE tab the wiring is:

```python
# Left-panel action buttons
btnRunFE.clicked   → FormationEvaluationService.run_evaluation()
btnFERender.clicked → FormationEvaluationService.run_evaluation()   # same handler
btnResetFE.clicked  → FormationEvaluationService.reset_evaluation()

# Well selector (shared with other tabs)
comboFeWell.currentTextChanged → DataService.set_current_well()
```

The helper `_connect_widget(name, signal, handler)` uses `getattr` so missing
widgets are silently skipped — no crash if a widget was removed from the .ui.

---

## 5. Back-end execution flow (`services/formation_evaluation_service.py`)

### 5.1 `run_evaluation()` — top-level orchestrator

```
run_evaluation()
  └── _build_result()          ← compute everything; returns dict or None
        ├── DataService._get_current_well() → well.data (pandas DataFrame)
        ├── depth range filter (spinFEFrom / spinFETo)
        ├── curve auto-detection (_first_available_curve)
        │     GR  : GR | SGR | GAMMA
        │     RHOB: RHOB | RHOZ | DEN
        │     NPHI: NPHI | NEU | PHIN
        │     RT  : RT | LLD | ILD | RESD | RDEP
        ├── read parameters (spinFEGRMin, spinFEGRMax, spinFERhoMa, …)
        ├── read Vsh method  ← vshTypeComboBox  (NEW — see §5.2)
        ├── calculations.vshale.compute_vsh_from_gr(…, method=…)
        ├── calculations.porosity.compute_phi_combo / compute_phi_from_density
        ├── calculations.saturation.compute_sw_archie
        ├── calculations.permeability.compute_perm_timur
        └── calculations.net_pay.compute_net_pay
              → returns DataFrame {depth, GR, VSH, PHI, SW, PERM, NET_PAY}

  (if result is not None)
  ├── _update_summary(result)         → lblFENetIntervalValue / Phi / Sw
  ├── _fill_pay_table(result)         → tableFEPaySummary rows
  ├── _render_tracks(result)          → matplotlib canvases embedded in frames
  └── _update_secondary_placeholders  → lblFEComputedPlaceholder / Crossplot
```

### 5.2 Vsh method selection (`vshTypeComboBox`)

The `vshTypeComboBox` combo-box (in `groupFEVsh`) lets the user pick one of
five industry-standard Vsh methods.  The selection is read via
`_combo_text("vshTypeComboBox")` and mapped through `VSH_METHOD_MAP`
(defined in `calculations/vshale.py`) to a method key:

| Combo text | Method key | Formula |
|---|---|---|
| Linear | `linear` | `IGR` |
| Larionov (Tertiary Rocks) | `larionov_tertiary` | `0.083 × (2^(3.7·IGR) − 1)` |
| Larionov (Older Rocks) | `larionov_older` | `0.33 × (2^(2·IGR) − 1)` |
| Clavier Model (Most Accurate) | `clavier` | `1.7 − √(3.38 − (IGR + 0.7)²)` |
| Steiber Model | `steiber` | `IGR / (3 − 2·IGR)` |

Where `IGR = (GR − GR_min) / (GR_max − GR_min)` is the linear gamma-ray index.

All non-linear methods produce *lower* Vsh than the linear method for
intermediate GR values — they assume a non-linear clay content response.

### 5.3 Plot rendering (`_render_tracks`)

Each track frame (`frameFEGammaTrack`, etc.) receives an embedded matplotlib
`FigureCanvasQTAgg` widget.  The helper `_ensure_plot_host` lazily creates a
child `QWidget` with a `QVBoxLayout` inside the frame, caches it, and
re-uses it on subsequent renders (clearing old canvases first).  Pay-zone rows
(`NET_PAY == 1`) are highlighted with a green `fill_betweenx` band.

### 5.4 `reset_evaluation()`

Sets all result labels back to `"--"`, clears `tableFEPaySummary`, restores
placeholder label text, and hides all embedded plot widgets.

---

## 6. Calculation module reference

| Module | Function | Inputs | Output |
|---|---|---|---|
| `vshale` | `compute_vsh_from_gr` | GR array, GR_min, GR_max, method | Vsh [0, 1] |
| `porosity` | `compute_phi_from_density` | RHOB, ρ_ma, ρ_f | PHI [0, 1] |
| `porosity` | `compute_phi_combo` | NPHI, RHOB, ρ_ma, ρ_f | PHI [0, 1] (avg of density & neutron) |
| `saturation` | `compute_sw_archie` | PHI, RT, Rw, a, m, n | Sw [0, 1] |
| `permeability` | `compute_perm_timur` | PHI, Sw | k (mD) |
| `net_pay` | `compute_net_pay` | Vsh, PHI, Sw, k + cutoffs | 0/1 flag |

Default cutoffs used in `_build_result`:

| Property | Cutoff | Direction |
|---|---|---|
| Vsh | 0.40 | ≤ |
| PHI | 0.08 | ≥ |
| Sw | 0.65 | ≤ |
| Perm | 0.10 mD | ≥ |

---

## 7. Data flow summary (end-to-end)

```
User action
  │
  ▼
Qt signal (btnRunFE.clicked)
  │
  ▼
MainController._wire_actions
  → FormationEvaluationService.run_evaluation()
      │
      ▼
      DataService._get_current_well()     ← shared well store
          └─ well.data  (pandas DataFrame from loaded LAS/CSV/…)
      │
      ▼
      Read UI parameters
        spinFEGRMin / spinFEGRMax / vshTypeComboBox
        spinFERhoMa / spinFERhoF
        spinFEArchieA/M/N / spinFERw
        spinFEFrom / spinFETo
      │
      ▼
      calculations/ modules
        vshale  → VSH
        porosity → PHI
        saturation → SW
        permeability → PERM
        net_pay → NET_PAY flag
      │
      ▼
      Update UI output widgets
        lblFENetIntervalValue / lblFEAvgPhiValue / lblFEAvgSwValue
        tableFEPaySummary
        Matplotlib canvases inside frameFEGammaTrack / VshTrack / …
        lblFEComputedPlaceholder / lblFECrossplotPlaceholder
```
