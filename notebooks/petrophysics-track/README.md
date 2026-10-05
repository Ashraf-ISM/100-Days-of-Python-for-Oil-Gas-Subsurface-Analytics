# 🪨 Petrophysics Track — 12 Weeks

A petrophysics-first extension of the 100-days series, aimed at operator and service-company
petrophysicist roles. Each week has one notebook containing the theory recap, daily tasks
(markdown checklists) and empty code cells for you to fill in.

## How to use

1. Open the week's notebook, read **Theory recap**, write your notes.
2. Each day: tick the checklist, write code in the cell below it.
3. Move reusable functions into `notebooks/day-25-petrophysics/calculations/` and add tests.
4. Save the key figure to the week's `outputs/` folder and update the week README.
5. Commit and push. Change ⬜ to ✅ below.

## Progress

| Week | Topic | Why it matters | Status |
|---|---|---|---|
| 01 | [Shaly-Sand Water Saturation](week-01-shaly-sand-saturation/) | 'Which Sw model would you use in a shaly sand, and why?' is the single most common petrophysics interview question | ⬜ |
| 02 | [Deriving Rw, a, m and n](week-02-rw-and-archie-parameters/) | Senior petrophysicists judge you by how you justify parameters, not by the formula you type | ⬜ |
| 03 | [Core–Log Integration](week-03-core-log-integration/) | Operators trust log interpretations only when they are tied to core | ⬜ |
| 04 | [Rock Typing and Flow Units](week-04-rock-typing/) | Rock typing drives saturation-height, permeability prediction and the static model — central to reservoir characterisation roles | ⬜ |
| 05 | [NMR Petrophysics](week-05-nmr-petrophysics/) | NMR is a high-value specialist skill and SLB's CMR is a flagship tool | ⬜ |
| 06 | [Borehole Image Analysis](week-06-borehole-image-analysis/) | Image interpretation (bedding, fractures, breakouts) is a dedicated role at service companies and a big plus for operators | ⬜ |
| 07 | [Formation Pressure and Fluid Contacts](week-07-formation-pressure-analysis/) | Pressure-depth plots are asked in almost every operator interview and drive contacts in volumetrics | ⬜ |
| 08 | [Saturation-Height Modelling](week-08-saturation-height-modelling/) | SHF ties petrophysics to the 3D model | ⬜ |
| 09 | [Petrophysical Uncertainty and Volumetrics](week-09-uncertainty-and-volumetrics/) | Petrophysics feeds reserves | ⬜ |
| 10 | [Rock Physics and Geomechanics](week-10-rock-physics-and-geomechanics/) | Integrated teams expect petrophysicists to deliver elastic logs for seismic (QI) and rock strength for drilling/completions | ⬜ |
| 11 | [Cased-Hole Saturation Monitoring and CCS](week-11-cased-hole-and-ccs/) | Mature fields and carbon capture and storage (CCS) projects are hiring petrophysicists | ⬜ |
| 12 | [Capstone — Multi-Well Field Study (Volve)](week-12-capstone-field-study/) | One end-to-end project proves you can do the job | ⬜ |

## Data used

| File | Used in |
|---|---|
| `day-25-petrophysics/data/Well_1.las` | Weeks 1, 2, 11 |
| `day-55/Volve/volve_159-19A_LFP.las` | Weeks 2–4, 7–10 |
| `day-25-petrophysics/data/_Gorgonichthys_1_..._CMR.las` | Week 5 (NMR) |
| `day-25-petrophysics/data/P11-A-02_Composite_MEM_Image_NF.las` | Week 6 (images) |
| `day-25-petrophysics/data/volve_wells.csv` | Week 12 |

## Alongside the code

- Practise Techlog / IP at work; learn Techlog Python scripting.
- Join SPWLA and SPE; consider presenting the Week 5 or Week 4 work at a local chapter.
- Reading: Asquith & Krygowski; Ellis & Singer; Coates (NMR); Lucia (carbonates).
