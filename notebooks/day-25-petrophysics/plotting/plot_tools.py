"""All plots in one module (matplotlib-based)."""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import ticker

PALETTE = [
    "#0F4C81",
    "#D1495B",
    "#8C5E34",
    "#6B46C1",
    "#008B8B",
    "#C05621",
    "#1F2937",
]
TRACK_BACKGROUNDS = ["#FBFCFE", "#F5F8FC", "#FCFCFD", "#F8FAFC"]
RESISTIVITY_TOKENS = ["RT", "RDEP", "RILD", "LLD", "LLS", "RXO", "RES", "ILD", "ILM", "RS"]


def _curve_color(index: int) -> str:
    return PALETTE[index % len(PALETTE)]


def _find_first(columns: list[str], candidates: list[str]) -> str | None:
    upper_map = {c: c.upper() for c in columns}
    for cand in candidates:
        cand_upper = cand.upper()
        for col, col_upper in upper_map.items():
            if col_upper == cand_upper:
                return col
    for cand in candidates:
        cand_upper = cand.upper()
        for col, col_upper in upper_map.items():
            if cand_upper in col_upper:
                return col
    return None


def _find_all_matching(columns: list[str], tokens: list[str]) -> list[str]:
    matches: list[str] = []
    tokens_upper = [t.upper() for t in tokens]
    for col in columns:
        col_upper = col.upper()
        if any(tok in col_upper for tok in tokens_upper):
            matches.append(col)
    return matches


def _select_triple_combo_curves(columns: list[str]):
    gr = _find_first(columns, ["GR", "GRC", "SGR", "CGR", "GRD", "GAMMA"])
    cali = _find_first(columns, ["CALI", "CAL", "HCAL", "CALD"])

    resistivity = _find_all_matching(columns, RESISTIVITY_TOKENS)
    density = _find_all_matching(columns, ["RHOB", "RHOZ", "RHO", "DEN", "DENB"])
    porosity = _find_all_matching(columns, ["NPHI", "PHI", "PHIE", "PHIT", "DPHI", "NPOR", "POR"])

    track1 = [c for c in (gr, cali) if c]
    track2 = resistivity[:]
    track3 = density + porosity

    used = set(track1 + track2 + track3)
    if not track1:
        for col in columns:
            if col not in used:
                track1 = [col]
                used.add(col)
                break
    if not track2:
        for col in columns:
            if col not in used:
                track2 = [col]
                used.add(col)
                break
    if not track3:
        for col in columns:
            if col not in used:
                track3 = [col]
                used.add(col)
                break
    return track1, track2, track3


def _get_depth(df):
    if "DEPTH" in df.columns:
        return np.asarray(df["DEPTH"].values, dtype=float)
    return np.asarray(df.index.values, dtype=float)


def _get_depth_label(df, depth_col: str = "DEPTH") -> str:
    if depth_col in df.columns:
        return depth_col
    return getattr(df.index, "name", None) or "Depth"


def _get_curve_values(df, curve: str):
    return np.asarray(df[curve].values, dtype=float)


def _is_resistivity_curve(curve: str) -> bool:
    curve_upper = curve.upper()
    return any(token in curve_upper for token in RESISTIVITY_TOKENS)


def _can_use_log(values) -> bool:
    finite_values = values[np.isfinite(values)]
    return finite_values.size > 1 and np.all(finite_values > 0)


def _style_figure(fig, title: str):
    fig.patch.set_facecolor("#F7FAFD")
    fig.suptitle(title, fontsize=15, fontweight="bold", color="#18344F", y=0.985)


def _style_track_axis(
    ax,
    *,
    label: str,
    color: str,
    background: str,
    depth_label: str,
    show_ylabel: bool,
    use_log_scale: bool = False,
):
    ax.set_facecolor(background)
    ax.xaxis.set_label_position("top")
    ax.xaxis.tick_top()
    ax.tick_params(
        axis="x",
        top=True,
        labeltop=True,
        bottom=False,
        labelbottom=False,
        labelsize=8,
        colors=color,
        pad=3,
    )
    ax.tick_params(
        axis="y",
        labelsize=8,
        colors="#486581",
        labelleft=show_ylabel,
    )
    if use_log_scale:
        ax.set_xscale("log")
        ax.xaxis.set_major_locator(ticker.LogLocator(base=10))
        ax.xaxis.set_minor_locator(ticker.LogLocator(base=10, subs=np.arange(2, 10) * 0.1))
    ax.yaxis.set_major_locator(ticker.MaxNLocator(12))
    ax.grid(axis="y", color="#D9E2EC", linewidth=0.75)
    ax.grid(axis="x", color="#E8EEF5", linewidth=0.55)
    ax.invert_yaxis()
    ax.set_xlabel(label, color=color, fontsize=9, fontweight="bold", labelpad=8)
    ax.set_ylabel(depth_label if show_ylabel else "", color="#486581", fontsize=9, fontweight="bold")
    ax.spines["bottom"].set_visible(False)
    ax.spines["top"].set_color(color)
    ax.spines["top"].set_linewidth(1.2)
    for side in ("left", "right"):
        ax.spines[side].set_color("#C8D2DC")
        ax.spines[side].set_linewidth(0.9)


def _make_overlay_axis(base_ax, *, label: str, color: str, offset: int, use_log_scale: bool = False):
    overlay = base_ax.twiny()
    overlay.patch.set_alpha(0)
    overlay.xaxis.set_label_position("top")
    overlay.xaxis.tick_top()
    overlay.spines["top"].set_position(("outward", offset))
    overlay.spines["top"].set_color(color)
    overlay.spines["top"].set_linewidth(1.1)
    overlay.spines["bottom"].set_visible(False)
    overlay.spines["left"].set_visible(False)
    overlay.spines["right"].set_visible(False)
    overlay.tick_params(
        axis="x",
        top=True,
        labeltop=True,
        bottom=False,
        labelbottom=False,
        labelsize=8,
        colors=color,
        pad=3,
    )
    overlay.tick_params(axis="y", left=False, labelleft=False)
    if use_log_scale:
        overlay.set_xscale("log")
        overlay.xaxis.set_major_locator(ticker.LogLocator(base=10))
        overlay.xaxis.set_minor_locator(ticker.LogLocator(base=10, subs=np.arange(2, 10) * 0.1))
    overlay.set_xlabel(label, color=color, fontsize=9, fontweight="bold", labelpad=8)
    overlay.grid(False)
    return overlay


def _plot_curve(ax, df, depth, curve: str, color: str, *, linewidth: float = 1.5) -> bool:
    if curve not in df.columns:
        return False
    values = _get_curve_values(df, curve)
    mask = np.isfinite(values) & np.isfinite(depth)
    if not np.any(mask):
        return False
    ax.plot(values[mask], depth[mask], color=color, linewidth=linewidth, solid_capstyle="round")
    return True


def _empty_figure(title: str, message: str):
    fig = plt.figure(figsize=(8, 6))
    _style_figure(fig, title)
    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.text(
        0.5,
        0.5,
        message,
        ha="center",
        va="center",
        fontsize=12,
        color="#627D98",
        transform=ax.transAxes,
    )
    return fig


def _plot_track_group(
    ax,
    df,
    depth,
    curves: list[str],
    *,
    track_title: str,
    depth_label: str,
    show_ylabel: bool,
    background: str,
    prefer_log_scale: bool = False,
    fill_first_curve: bool = False,
) -> int:
    valid_curves = [curve for curve in curves if curve in df.columns]
    if track_title:
        ax.set_title(track_title, fontsize=10, fontweight="bold", color="#486581", pad=18)

    if not valid_curves:
        _style_track_axis(
            ax,
            label="No curves selected",
            color="#627D98",
            background=background,
            depth_label=depth_label,
            show_ylabel=show_ylabel,
        )
        ax.text(
            0.5,
            0.5,
            "Select one or more curves",
            ha="center",
            va="center",
            fontsize=10,
            color="#7B8794",
            transform=ax.transAxes,
        )
        return 0

    first_curve = valid_curves[0]
    first_values = _get_curve_values(df, first_curve)
    use_log_scale = prefer_log_scale and _can_use_log(first_values)
    _style_track_axis(
        ax,
        label=first_curve,
        color=_curve_color(0),
        background=background,
        depth_label=depth_label,
        show_ylabel=show_ylabel,
        use_log_scale=use_log_scale,
    )
    if _plot_curve(ax, df, depth, first_curve, _curve_color(0)) and fill_first_curve:
        mask = np.isfinite(first_values) & np.isfinite(depth)
        ax.fill_betweenx(
            depth[mask],
            np.nanmin(first_values[mask]),
            first_values[mask],
            color=_curve_color(0),
            alpha=0.08,
        )

    for index, curve in enumerate(valid_curves[1:], start=1):
        values = _get_curve_values(df, curve)
        overlay = _make_overlay_axis(
            ax,
            label=curve,
            color=_curve_color(index),
            offset=24 * index,
            use_log_scale=prefer_log_scale and _can_use_log(values),
        )
        _plot_curve(overlay, df, depth, curve, _curve_color(index), linewidth=1.35)

    ax.text(
        0.03,
        0.02,
        " | ".join(valid_curves),
        fontsize=8,
        color="#52606D",
        transform=ax.transAxes,
        va="bottom",
    )
    return len(valid_curves)

################### Multi track ########################
"""
multitrack_plot.py
==================
Professional publication-quality multi-track petrophysical log plot.
Schlumberger/Petrel-style layout with full petrophysical annotations.

Author  : PetroARX Engine
Version : 2.0.0
"""

from __future__ import annotations

import warnings
from typing import Any

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────────────────────────────
#  DESIGN TOKENS  (edit here to retheme globally)
# ──────────────────────────────────────────────────────────────────────────────

THEME = {
    # panel chrome
    "fig_bg":         "#F4F6F8",
    "header_bg":      "#0D1B2A",       # deep navy
    "header_fg":      "#E8EEF4",
    "subheader_bg":   "#1B3A5C",
    "subheader_fg":   "#A8C4DC",

    # track styling
    "track_bg_even":  "#FAFBFC",
    "track_bg_odd":   "#F0F4F8",
    "track_border":   "#B8C8D8",
    "track_header_bg":"#1B3A5C",
    "track_header_fg":"#FFFFFF",
    "scale_bar_bg":   "#E8EFF6",
    "grid_color":     "#D0DCE8",
    "grid_alpha":     0.55,
    "depth_bg":       "#0D1B2A",
    "depth_fg":       "#E8EEF4",

    # curve palettes (matched to log type)
    "gr_color":        "#2D8B57",      # forest green
    "gr_sand_fill":    "#F5C842",      # amber
    "gr_shale_fill":   "#8B7355",      # clay brown
    "res_color":       "#C0392B",      # deep red
    "rhob_color":      "#5C3D9E",      # purple
    "nphi_color":      "#1A7AB5",      # steel blue
    "dt_color":        "#D4691E",      # burnt orange
    "cali_color":      "#2176AE",      # slate blue
    "sp_color":        "#1A8C6B",      # teal
    "default_colors": [
        "#2176AE", "#D4691E", "#5C3D9E", "#2D8B57",
        "#A0522D", "#1A7AB5", "#B8860B", "#4B7BE5",
    ],

    # annotation
    "cutoff_color":    "#1A1A2E",
    "zone_alpha":      0.12,
    "stats_bg":        "white",
    "stats_alpha":     0.88,
}

# ──────────────────────────────────────────────────────────────────────────────
#  CURVE CLASSIFICATION MAPS
# ──────────────────────────────────────────────────────────────────────────────

GR_KEYS        = {"GR", "GAMMA", "GAMMA_RAY", "SGR", "CGR", "GRD", "GRC"}
RESISTIVITY_KEYS = {
    "RT", "RD", "RS", "RXO", "RILD", "RILM", "ILD", "ILM", "LLD", "LLS",
    "MSFL", "SFLA", "SFLU", "AT10", "AT20", "AT60", "AT90",
    "RLA1","RLA2","RLA3","RLA4","RLA5","RT_HRLT",
}
DENSITY_KEYS   = {"RHOB", "DEN", "ZDEN", "RHOZ", "DPHI"}
NEUTRON_KEYS   = {"NPHI", "TNPH", "NPOR", "CNPHI", "NEUT", "CMFF", "CMRP"}
SONIC_KEYS     = {"DT", "DTCO", "DTS", "DTC", "AC", "DTSM"}
CALIPER_KEYS   = {"CALI", "CAL", "C1", "C2", "HCAL"}
POROSITY_KEYS  = {"PHIE", "PHIT", "PHI", "POR"}
SW_KEYS        = {"SW", "SWT", "SWE", "SXO", "BFV", "CBW"}
VSH_KEYS       = {"VSH", "VCL", "VSHGR", "GRN"}
PERMEABILITY_KEYS = {"K", "KLOG", "PERM", "TPERM", "KAIR"}

# Natural overlay pairs: {primary: overlay_curve}
OVERLAY_PAIRS = {
    "NPHI":  "RHOB",
    "TNPH":  "RHOB",
    "RHOB":  "NPHI",
    "DT":    "DTCO",
    "DTCO":  "DTS",
}

# Track width weights (relative)
TRACK_WIDTH_MAP = {
    "DEPTH": 0.45,
    "GR": 1.0, "GAMMA": 1.0, "GAMMA_RAY": 1.0,
    "CALI": 0.75,
    "RT": 1.2, "ILD": 1.2, "LLD": 1.2,
    "RHOB": 1.1, "NPHI": 1.1, "TNPH": 1.1,
    "DT": 1.0, "DTCO": 1.0,
}

# ──────────────────────────────────────────────────────────────────────────────
#  FONT SETUP
# ──────────────────────────────────────────────────────────────────────────────

plt.rcParams.update({
    "font.family":        "DejaVu Sans",
    "axes.unicode_minus": False,
    "pdf.fonttype":       42,
    "ps.fonttype":        42,
})


# ──────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _classify(curve: str) -> str:
    cu = curve.upper()
    if any(cu.startswith(k) or cu == k for k in GR_KEYS):         return "GR"
    if any(cu.startswith(k) or cu == k for k in RESISTIVITY_KEYS): return "RES"
    if any(cu.startswith(k) or cu == k for k in DENSITY_KEYS):    return "RHOB"
    if any(cu.startswith(k) or cu == k for k in NEUTRON_KEYS):    return "NPHI"
    if any(cu.startswith(k) or cu == k for k in SONIC_KEYS):      return "SONIC"
    if any(cu.startswith(k) or cu == k for k in CALIPER_KEYS):    return "CALI"
    if any(cu.startswith(k) or cu == k for k in POROSITY_KEYS):   return "PHI"
    if any(cu.startswith(k) or cu == k for k in SW_KEYS):         return "SW"
    if any(cu.startswith(k) or cu == k for k in VSH_KEYS):        return "VSH"
    if any(cu.startswith(k) or cu == k for k in PERMEABILITY_KEYS): return "PERM"
    return "GENERIC"


def _curve_color(curve: str, idx: int) -> str:
    cls = _classify(curve)
    return {
        "GR":      THEME["gr_color"],
        "RES":     THEME["res_color"],
        "RHOB":    THEME["rhob_color"],
        "NPHI":    THEME["nphi_color"],
        "SONIC":   THEME["dt_color"],
        "CALI":    THEME["cali_color"],
        "SP":      THEME["sp_color"],
    }.get(cls, THEME["default_colors"][idx % len(THEME["default_colors"])])


def _is_log_scale(curve: str, values: pd.Series) -> bool:
    cls = _classify(curve)
    if cls != "RES":
        return False
    valid = values.dropna()
    return valid.min() > 0 and valid.max() / (valid.min() + 1e-9) > 5


def _safe_stats(values: pd.Series) -> dict:
    v = values.dropna()
    if len(v) == 0:
        return {"mean": np.nan, "p10": np.nan, "p50": np.nan, "p90": np.nan,
                "min": np.nan, "max": np.nan, "n": 0}
    return {
        "mean": v.mean(), "p10": v.quantile(0.10),
        "p50":  v.median(), "p90": v.quantile(0.90),
        "min":  v.min(),    "max": v.max(), "n": len(v),
    }


def _smart_lim(values: pd.Series, cls: str, log: bool) -> tuple[float, float]:
    """Return [left, right] x-limits for a curve track."""
    v = values.dropna()
    if len(v) == 0:
        return (0, 1)

    PRESETS = {
        "GR":    (0,   200),
        "RES":   (0.2, 2000),
        "RHOB":  (1.95, 2.95),
        "NPHI":  (0.45, -0.15),   # reversed (left > right)
        "SONIC": (140, 40),        # reversed (dt: 140→40)
        "SW":    (0,   1),
        "PHI":   (0,   0.50),
        "VSH":   (0,   1),
        "CALI":  (6,   16),
        "PERM":  (0.001, 10000),
    }
    if cls in PRESETS:
        return PRESETS[cls]
    # auto
    p2, p98 = v.quantile(0.02), v.quantile(0.98)
    rng = p98 - p2
    return (p2 - 0.05 * rng, p98 + 0.05 * rng)


# ──────────────────────────────────────────────────────────────────────────────
#  TRACK HEADER  (top box with curve name + scale)
# ──────────────────────────────────────────────────────────────────────────────

def _draw_track_header(
    ax,
    curve: str,
    xlim: tuple[float, float],
    color: str,
    unit: str = "",
    log_scale: bool = False,
    stats: dict | None = None,
    header_height_ratio: float = 0.16,
):
    """Draw a professional track header box above the curve panel."""
    ax.set_title("")  # clear matplotlib title

    # ── top bar: curve name ────────────────────────────────────────────────
    ax.text(
        0.5, 1.055, curve,
        transform=ax.transAxes,
        ha="center", va="bottom",
        fontsize=9.5, fontweight="bold",
        color=THEME["track_header_fg"],
        bbox=dict(
            boxstyle="round,pad=0.28",
            facecolor=color, edgecolor="none", alpha=0.92,
        ),
    )

    # ── scale line: left value ── // ── right value ────────────────────────
    left_val, right_val = xlim
    fmt = ".3g"
    scale_txt = f"{left_val:{fmt}}{'  [LOG]' if log_scale else ''}  ─────  {right_val:{fmt}}"
    if unit:
        scale_txt += f"  ({unit})"

    ax.text(
        0.5, 1.012, scale_txt,
        transform=ax.transAxes,
        ha="center", va="bottom",
        fontsize=6.5, color="#334455",
        fontfamily="monospace",
    )

    # ── stats row (P10 / mean / P90) ─────────────────────────────────────
    if stats:
        s = stats
        ok = not np.isnan(s["mean"])
        if ok:
            stats_str = (
                f"μ {s['mean']:.3g}   "
                f"P10 {s['p10']:.3g}   "
                f"P90 {s['p90']:.3g}"
            )
            ax.text(
                0.5, 0.978,
                stats_str,
                transform=ax.transAxes,
                ha="center", va="top",
                fontsize=6.0,
                color="#556677",
                fontfamily="monospace",
            )


# ──────────────────────────────────────────────────────────────────────────────
#  CURVE FILLS
# ──────────────────────────────────────────────────────────────────────────────

def _fill_gr(ax, depth, values, cutoff: float = 75.0):
    ax.fill_betweenx(depth, values, cutoff,
                     where=(values <= cutoff),
                     color=THEME["gr_sand_fill"], alpha=0.45,
                     linewidth=0, zorder=1, label="Sand")
    ax.fill_betweenx(depth, values, cutoff,
                     where=(values > cutoff),
                     color=THEME["gr_shale_fill"], alpha=0.30,
                     linewidth=0, zorder=1, label="Shale")


def _fill_nphi_rhob_crossover(ax_nphi, ax_rhob, depth, nphi_vals, rhob_vals,
                               nphi_xlim, rhob_xlim):
    """
    Normalise both curves to [0,1] axis space and shade crossover zones.
    Gas crossover: NPHI < RHOB (in normalised space).
    """
    def _norm(v, lim):
        return (v - lim[0]) / (lim[1] - lim[0] + 1e-12)

    nn = _norm(nphi_vals, nphi_xlim)
    nr = _norm(rhob_vals, rhob_xlim)

    # Gas crossover (gas effect: NPHI reads low, RHOB reads low)
    ax_nphi.fill_betweenx(depth, nn, nr,
                          where=(nn < nr),
                          transform=ax_nphi.get_yaxis_transform(),
                          color="#00C9FF", alpha=0.28, linewidth=0,
                          zorder=2, label="Gas crossover")
    # Liquid / tight
    ax_nphi.fill_betweenx(depth, nn, nr,
                          where=(nn >= nr),
                          transform=ax_nphi.get_yaxis_transform(),
                          color="#FF8C42", alpha=0.18, linewidth=0,
                          zorder=2, label="Liquid/Tight")


# ──────────────────────────────────────────────────────────────────────────────
#  DEPTH TRACK
# ──────────────────────────────────────────────────────────────────────────────

def _draw_depth_track(ax, depth: pd.Series, depth_label: str = "DEPTH (m)"):
    ax.set_facecolor(THEME["depth_bg"])

    for spine in ax.spines.values():
        spine.set_edgecolor(THEME["track_border"])
        spine.set_linewidth(0.8)

    ax.set_xlim(0, 1)
    ax.set_ylim(depth.max(), depth.min())

    step = _nice_depth_step(depth)
    ticks = np.arange(
        np.ceil(depth.min() / step) * step,
        np.floor(depth.max() / step) * step + 1,
        step,
    )
    ax.set_yticks(ticks)
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.0f"))
    ax.yaxis.set_tick_params(
        which="major", labelsize=8.0, labelcolor=THEME["depth_fg"],
        length=4, width=0.8, direction="in",
    )
    ax.set_xticks([])

    # Minor grid lines
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator(5))
    ax.tick_params(which="minor", length=2, color="#4A6FA5")

    ax.set_ylabel(depth_label, fontsize=8.5, color=THEME["depth_fg"],
                  fontweight="bold", labelpad=4)
    ax.yaxis.set_label_position("left")

    # Depth label header
    ax.text(0.5, 1.055, "DEPTH",
            transform=ax.transAxes,
            ha="center", va="bottom",
            fontsize=9.5, fontweight="bold",
            color=THEME["track_header_fg"],
            bbox=dict(boxstyle="round,pad=0.28",
                      facecolor=THEME["header_bg"],
                      edgecolor="none", alpha=0.92))
    ax.text(0.5, 1.012, depth_label,
            transform=ax.transAxes,
            ha="center", va="bottom",
            fontsize=6.5, color="#556677",
            fontfamily="monospace")


def _nice_depth_step(depth: pd.Series) -> float:
    span = depth.max() - depth.min()
    for step in [5, 10, 20, 25, 50, 100, 200, 250, 500, 1000]:
        if span / step <= 30:
            return float(step)
    return float(round(span / 20, -1))


# ──────────────────────────────────────────────────────────────────────────────
#  MAIN FUNCTION
# ──────────────────────────────────────────────────────────────────────────────

def plot_multitrack(
    df: pd.DataFrame,
    curves: list[str] | None = None,
    depth_col: str = "DEPTH",
    *,
    # ── meta ──────────────────────────────────────────────────────────────
    well_name: str = "WELL",
    field: str = "",
    depth_unit: str = "m",
    # ── curve control ─────────────────────────────────────────────────────
    max_curves: int = 10,
    units: dict[str, str] | None = None,
    # ── petrophysical parameters ──────────────────────────────────────────
    gr_cutoff: float = 75.0,
    overlay_pairs: dict[str, str] | None = None,
    cutoffs: dict[str, float] | None = None,
    zones: list[dict[str, Any]] | None = None,
    # ── display options ───────────────────────────────────────────────────
    show_fills: bool = True,
    show_crossover: bool = True,
    show_stats: bool = True,
    show_cutoffs: bool = True,
    show_depth_track: bool = True,
    show_zones: bool = True,
    # ── output ────────────────────────────────────────────────────────────
    figsize_width_per_track: float = 1.75,
    figsize_height: float = 13.0,
    dpi: int = 150,
    export_path: str | None = None,
    show: bool = True,
) -> plt.Figure:
    """
    Render a professional multi-track petrophysical log plot.

    Parameters
    ----------
    df              : DataFrame with depth + curve columns.
    curves          : List of curve names to plot. None → auto-select first 8.
    depth_col       : Column name for depth.
    well_name       : Well identifier for header.
    field           : Field/block name (optional).
    depth_unit      : 'm' or 'ft'.
    units           : Dict mapping curve name → unit string for header display.
    gr_cutoff       : GR sand/shale cutoff (API).
    overlay_pairs   : {primary_curve: overlay_curve} for dual-scale tracks.
                      Defaults to NPHI/RHOB crossover if both present.
    cutoffs         : {curve: value} vertical cutoff lines per track.
    zones           : List of dicts with keys: name, top, base, color.
    show_fills      : Enable GR sand/shale fill and crossover shading.
    show_crossover  : Enable NPHI–RHOB crossover shading.
    show_stats      : Show P10/mean/P90 in track header.
    show_cutoffs    : Draw cutoff vertical lines.
    show_depth_track: Include depth axis track on the left.
    show_zones      : Draw formation zone bands.
    export_path     : If set, save figure to this path at `dpi` resolution.
    show            : Call plt.show() at end.
    dpi             : Resolution for screen and export.

    Returns
    -------
    matplotlib.figure.Figure
    """

    # ── 0. Validate depth ─────────────────────────────────────────────────
    if depth_col not in df.columns:
        raise ValueError(f"Depth column '{depth_col}' not found in DataFrame.")

    depth = df[depth_col].astype(float)
    depth_label = f"DEPTH ({depth_unit})"

    # ── 1. Select curves ──────────────────────────────────────────────────
    available = [c for c in df.columns if c != depth_col]
    if curves is None:
        curves = available[:max_curves]
    else:
        curves = [c for c in curves if c in df.columns and c != depth_col]

    if not curves:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, "No curves available.", ha="center", va="center")
        return fig

    n_curves = len(curves)
    units = units or {}
    overlay_pairs = overlay_pairs if overlay_pairs is not None else OVERLAY_PAIRS
    cutoffs = cutoffs or {}

    # ── 2. Layout via GridSpec ────────────────────────────────────────────
    n_tracks = n_curves + (1 if show_depth_track else 0)

    widths = []
    if show_depth_track:
        widths.append(0.45)
    for c in curves:
        widths.append(TRACK_WIDTH_MAP.get(c.upper(), 1.0))

    total_w = max(sum(widths) * figsize_width_per_track + 0.5, 10)
    fig = plt.figure(figsize=(total_w, figsize_height), dpi=dpi,
                     facecolor=THEME["fig_bg"])

    gs = GridSpec(
        1, n_tracks,
        figure=fig,
        width_ratios=widths,
        left=0.05, right=0.99,
        bottom=0.04, top=0.87,
        wspace=0.04,
    )

    axes: list[plt.Axes] = []
    for i in range(n_tracks):
        sharey = axes[0] if i > 0 else None
        ax = fig.add_subplot(gs[0, i], sharey=sharey)
        axes.append(ax)

    depth_ax  = axes[0] if show_depth_track else None
    curve_axes = axes[1:] if show_depth_track else axes

    # ── 3. Global depth limits ────────────────────────────────────────────
    d_min, d_max = depth.min(), depth.max()
    axes[0].set_ylim(d_max, d_min)   # inverted (depth increases downward)

    # ── 4. Depth track ────────────────────────────────────────────────────
    if show_depth_track:
        _draw_depth_track(depth_ax, depth, depth_label)

    # ── 5. Curve tracks ───────────────────────────────────────────────────
    nphi_ax_ref   = None  # for crossover shading
    rhob_ax_ref   = None
    nphi_vals_ref = None
    rhob_vals_ref = None
    nphi_lim_ref  = None
    rhob_lim_ref  = None

    for track_idx, (ax, curve) in enumerate(zip(curve_axes, curves)):
        values = df[curve].astype(float)
        cls    = _classify(curve)
        color  = _curve_color(curve, track_idx)
        log_sc = _is_log_scale(curve, values)
        unit   = units.get(curve, "")
        stats  = _safe_stats(values) if show_stats else None
        xlim   = _smart_lim(values, cls, log_sc)

        # ── track background ──────────────────────────────────────────────
        bg = THEME["track_bg_even"] if track_idx % 2 == 0 else THEME["track_bg_odd"]
        ax.set_facecolor(bg)

        # ── spines ────────────────────────────────────────────────────────
        for spine in ax.spines.values():
            spine.set_edgecolor(THEME["track_border"])
            spine.set_linewidth(0.8)

        # ── grid ──────────────────────────────────────────────────────────
        ax.grid(True, axis="y", color=THEME["grid_color"],
                alpha=THEME["grid_alpha"], linewidth=0.5, linestyle="--")
        ax.grid(True, axis="x", color=THEME["grid_color"],
                alpha=THEME["grid_alpha"] * 0.6, linewidth=0.4, linestyle=":")
        ax.set_axisbelow(True)

        # ── x-axis scale ──────────────────────────────────────────────────
        if log_sc:
            ax.set_xscale("log")
        ax.set_xlim(*xlim)

        # ── depth ticks (only on depth track or left-most) ────────────────
        ax.tick_params(axis="y", which="both",
                       left=(not show_depth_track and track_idx == 0),
                       labelleft=(not show_depth_track and track_idx == 0),
                       labelsize=7.5)
        ax.tick_params(axis="x", labelsize=6.5,
                       color=THEME["track_border"],
                       direction="out", length=3)

        # ── X tick formatting ─────────────────────────────────────────────
        if log_sc:
            ax.xaxis.set_major_formatter(ticker.LogFormatter(labelOnlyBase=False))
        else:
            ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=4, prune="both"))
            ax.xaxis.set_major_formatter(ticker.FormatStrFormatter("%.4g"))

        ax.tick_params(axis="x", top=False, bottom=True, labelbottom=False)

        # ── PLOT CURVE ────────────────────────────────────────────────────
        ax.plot(values, depth, color=color,
                linewidth=1.4, alpha=0.93, zorder=3,
                solid_capstyle="round", solid_joinstyle="round")

        # ── GR sand/shale fill ────────────────────────────────────────────
        if show_fills and cls == "GR":
            _fill_gr(ax, depth, values, gr_cutoff)
            ax.axvline(gr_cutoff, color=THEME["cutoff_color"],
                       linewidth=0.8, linestyle=":", alpha=0.6, zorder=4)

        # ── Caliper bit-size reference ─────────────────────────────────────
        if cls == "CALI":
            bit = 8.5 if depth_unit == "m" else 8.5  # standard
            ax.axvline(bit, color="#FF5722", linewidth=0.9,
                       linestyle="--", alpha=0.7, zorder=4,
                       label=f"Bit {bit}\"")
            ax.text(bit, d_min + (d_max - d_min) * 0.02,
                    f" Bit\n {bit}\"", fontsize=5.5,
                    color="#FF5722", va="top", zorder=5)

        # ── User cutoff lines ─────────────────────────────────────────────
        if show_cutoffs and curve in cutoffs:
            cv = cutoffs[curve]
            ax.axvline(cv, color=THEME["cutoff_color"],
                       linewidth=1.0, linestyle="--",
                       alpha=0.80, zorder=5)
            ax.text(cv, d_min + (d_max - d_min) * 0.01,
                    f" {cv:.3g}", fontsize=5.5,
                    color=THEME["cutoff_color"], va="top", zorder=6)

        # ── Dual-scale overlay (e.g., NPHI over RHOB track) ──────────────
        overlay_curve = overlay_pairs.get(curve)
        if overlay_curve and overlay_curve in df.columns:
            ov_vals  = df[overlay_curve].astype(float)
            ov_cls   = _classify(overlay_curve)
            ov_color = _curve_color(overlay_curve, track_idx + 1)
            ov_xlim  = _smart_lim(ov_vals, ov_cls, False)

            ax2 = ax.twiny()
            ax2.set_xlim(*ov_xlim)
            ax2.plot(ov_vals, depth, color=ov_color,
                     linewidth=1.2, linestyle="--",
                     alpha=0.85, zorder=3)
            ax2.set_xlabel(overlay_curve, color=ov_color,
                           fontsize=6.5, labelpad=2)
            ax2.tick_params(axis="x", colors=ov_color,
                            labelsize=5.5, top=True,
                            direction="in", length=2)
            ax2.spines["top"].set_edgecolor(ov_color)
            ax2.spines["top"].set_linewidth(0.8)

        # ── Store NPHI/RHOB refs for crossover shading ────────────────────
        if cls == "NPHI":
            nphi_ax_ref, nphi_vals_ref, nphi_lim_ref = ax, values, xlim
        if cls == "RHOB":
            rhob_ax_ref, rhob_vals_ref, rhob_lim_ref = ax, values, xlim

        # ── Formation zone bands ──────────────────────────────────────────
        if show_zones and zones:
            for zone in zones:
                ax.axhspan(
                    zone["top"], zone["base"],
                    color=zone.get("color", "#FFD700"),
                    alpha=THEME["zone_alpha"], zorder=0
                )

        # ── Track header ──────────────────────────────────────────────────
        _draw_track_header(
            ax,
            curve=curve,
            xlim=xlim,
            color=color,
            unit=unit,
            log_scale=log_sc,
            stats=stats,
        )

    # ── 6. NPHI–RHOB crossover (post-loop, both axes exist) ──────────────
    if (
        show_crossover
        and nphi_ax_ref is not None
        and rhob_ax_ref is not None
        and nphi_vals_ref is not None
        and rhob_vals_ref is not None
    ):
        _fill_nphi_rhob_crossover(
            nphi_ax_ref, rhob_ax_ref,
            depth,
            nphi_vals_ref, rhob_vals_ref,
            nphi_lim_ref, rhob_lim_ref,
        )

    # ── 7. Formation zone labels (on depth track or first curve track) ────
    if show_zones and zones:
        label_ax = depth_ax if show_depth_track else curve_axes[0]
        for zone in zones:
            mid = (zone["top"] + zone["base"]) / 2
            label_ax.text(
                0.5, mid,
                zone["name"],
                transform=label_ax.get_yaxis_transform(),
                ha="center", va="center",
                fontsize=6.5, fontstyle="italic",
                fontweight="bold",
                color=zone.get("label_color", "#222222"),
                bbox=dict(boxstyle="round,pad=0.2",
                          facecolor="white", alpha=0.65, edgecolor="none"),
                zorder=10,
            )

    # ── 8. Main figure header ─────────────────────────────────────────────
    _draw_figure_header(fig, well_name=well_name, field=field,
                        depth=depth, depth_unit=depth_unit,
                        curves=curves, df=df)

    # ── 9. Legend strip (GR fill + zone colours) ──────────────────────────
    _draw_legend(fig, zones=zones if show_zones else None, show_fills=show_fills)

    # ── 10. Depth inversion (confirmed once) ──────────────────────────────
    axes[0].set_ylim(d_max, d_min)

    # ── 11. Export / show ─────────────────────────────────────────────────
    if export_path:
        fig.savefig(
            export_path,
            dpi=max(dpi, 300),
            bbox_inches="tight",
            facecolor=THEME["fig_bg"],
        )
        print(f"[PetroARX] Saved → {export_path}")

    if show:
        plt.show()

    return fig


# ──────────────────────────────────────────────────────────────────────────────
#  FIGURE HEADER
# ──────────────────────────────────────────────────────────────────────────────

def _draw_figure_header(fig, well_name, field, depth, depth_unit, curves, df):
    d_min, d_max = depth.min(), depth.max()

    # Dark navy banner
    header_ax = fig.add_axes([0.0, 0.895, 1.0, 0.105])
    header_ax.set_facecolor(THEME["header_bg"])
    header_ax.axis("off")

    # ── Left: Well identification ─────────────────────────────────────────
    header_ax.text(
        0.013, 0.80,
        f"WELL:  {well_name}" + (f"   |   FIELD:  {field}" if field else ""),
        transform=header_ax.transAxes,
        ha="left", va="top",
        fontsize=12.5, fontweight="bold",
        color=THEME["header_fg"],
    )

    depth_span_txt = (
        f"Depth Interval:  {d_min:.1f} – {d_max:.1f} {depth_unit}   "
        f"|   Span: {d_max - d_min:.1f} {depth_unit}   "
        f"|   Samples: {len(depth):,}"
    )
    header_ax.text(
        0.013, 0.40,
        depth_span_txt,
        transform=header_ax.transAxes,
        ha="left", va="top",
        fontsize=8.0,
        color=THEME["subheader_fg"],
    )

    # ── Right: Curve count badge ──────────────────────────────────────────
    header_ax.text(
        0.987, 0.80,
        f"MULTI-TRACK LOG PLOT",
        transform=header_ax.transAxes,
        ha="right", va="top",
        fontsize=11, fontweight="bold",
        color=THEME["header_fg"],
        alpha=0.85,
    )
    header_ax.text(
        0.987, 0.38,
        f"{len(curves)} tracks displayed   |   PetroARX v2.0",
        transform=header_ax.transAxes,
        ha="right", va="top",
        fontsize=7.5,
        color=THEME["subheader_fg"],
    )

    # Thin accent line under header
    accent = fig.add_axes([0.0, 0.893, 1.0, 0.003])
    accent.set_facecolor("#1A9EFF")
    accent.axis("off")


# ──────────────────────────────────────────────────────────────────────────────
#  LEGEND STRIP
# ──────────────────────────────────────────────────────────────────────────────

def _draw_legend(fig, zones=None, show_fills=True):
    handles = []
    if show_fills:
        handles += [
            mpatches.Patch(color=THEME["gr_sand_fill"], alpha=0.7, label="Sand (GR < cutoff)"),
            mpatches.Patch(color=THEME["gr_shale_fill"], alpha=0.6, label="Shale (GR ≥ cutoff)"),
            mpatches.Patch(color="#00C9FF",              alpha=0.55, label="Gas crossover (NPHI–RHOB)"),
            mpatches.Patch(color="#FF8C42",              alpha=0.45, label="Liquid / Tight"),
        ]

    if zones:
        for z in zones:
            handles.append(
                mpatches.Patch(
                    color=z.get("color", "#FFD700"),
                    alpha=0.6,
                    label=z.get("name", "Zone"),
                )
            )

    if not handles:
        return

    legend = fig.legend(
        handles=handles,
        loc="lower center",
        ncol=min(len(handles), 6),
        fontsize=7.5,
        frameon=True,
        framealpha=0.92,
        edgecolor=THEME["track_border"],
        facecolor="white",
        bbox_to_anchor=(0.5, 0.0),
        bbox_transform=fig.transFigure,
        borderpad=0.5,
        columnspacing=1.2,
        handlelength=1.4,
    )
    legend.get_frame().set_linewidth(0.8)


# ──────────────────────────────────────────────────────────────────────────────
#  DEMO  (run this file directly to see output)
# ──────────────────────────────────────────────────────────────────────────────

def _generate_synthetic_well(n: int = 800) -> pd.DataFrame:
    """Synthetic well log data for demonstration."""
    rng = np.random.default_rng(42)
    depth = np.linspace(3900, 4140, n)

    # Base GR with blocky shale/sand patterns
    gr_base  = rng.uniform(30, 180, n)
    zones_gr = np.where((depth > 3970) & (depth < 4010), 0.35,
               np.where((depth > 4060) & (depth < 4100), 0.25, 1.0))
    gr = np.clip(gr_base * zones_gr + rng.normal(0, 5, n), 5, 250)

    # RHOB
    rhob = np.clip(2.65 - 0.3 * (gr < 75).astype(float) + rng.normal(0, 0.025, n), 2.0, 2.95)

    # NPHI (reversed scale in plot, higher = more porous)
    nphi = np.clip(0.35 - 0.15 * (gr < 75).astype(float) + rng.normal(0, 0.02, n), -0.05, 0.60)

    # Resistivity (log-normal, spiky in reservoir)
    res_base = rng.lognormal(1.0, 1.2, n)
    res = np.where((depth > 3970) & (depth < 4010), res_base * 15,
          np.where((depth > 4060) & (depth < 4100), res_base * 8, res_base))
    res = np.clip(res, 0.2, 5000)

    # DT sonic
    dt = np.clip(90 - 25 * (gr < 75).astype(float) + rng.normal(0, 5, n), 40, 140)

    # CALI
    cali = np.clip(8.5 + rng.exponential(0.3, n) * (gr > 120), 8.0, 16.0)

    return pd.DataFrame({
        "DEPTH": depth,
        "GR":    gr,
        "CALI":  cali,
        "RHOB":  rhob,
        "RT":    res,
        "NPHI":  nphi,
        "DT":    dt,
    })


if __name__ == "__main__":
    df = _generate_synthetic_well(800)

    example_zones = [
        {"name": "Res A",  "top": 3970, "base": 4010, "color": "#27AE60", "label_color": "#145A32"},
        {"name": "Res B",  "top": 4060, "base": 4100, "color": "#2980B9", "label_color": "#154360"},
        {"name": "Shale",  "top": 4010, "base": 4060, "color": "#BDC3C7", "label_color": "#555"},
    ]

    fig = plot_multitrack(
        df,
        curves=["CALI", "GR", "RHOB", "RT", "NPHI", "DT"],
        depth_col="DEPTH",
        well_name="GORGON-1_SUPERCOMBO",
        field="Gorgon Field — NW Shelf",
        depth_unit="m",
        units={
            "GR": "API", "RHOB": "g/cc", "NPHI": "v/v",
            "RT": "Ω·m", "DT": "μs/ft", "CALI": "in",
        },
        gr_cutoff=75.0,
        cutoffs={"RHOB": 2.50, "NPHI": 0.10, "SW": 0.50},
        zones=example_zones,
        show_fills=True,
        show_crossover=True,
        show_stats=True,
        show_cutoffs=True,
        show_depth_track=True,
        show_zones=True,
        figsize_height=14,
        dpi=150,
        export_path="multitrack_professional.png",
        show=True,
    )

def plot_triple_combo(
    df,
    gr="GR",
    rt="LLD",
    nphi="NPHI",
    rhob="RHOB",
    depth_col="DEPTH",
    *,
    show: bool = True,
):
    track1 = [curve for curve in [gr] if curve in df.columns]
    track2 = [curve for curve in [rt] if curve in df.columns]
    track3 = [curve for curve in [nphi, rhob] if curve in df.columns]
    fig = plot_triple_combo_tracks(df, track1, track2, track3, show=False)
    if show:
        plt.show()
    return fig


def plot_triple_combo_auto(df, *, show: bool = True):
    columns = [curve for curve in df.columns if curve != "DEPTH"]
    track1, track2, track3 = _select_triple_combo_curves(columns)
    fig = plot_triple_combo_tracks(df, track1, track2, track3, show=False)
    if show:
        plt.show()
    return fig


def plot_triple_combo_tracks(
    df,
    track1: list[str],
    track2: list[str],
    track3: list[str],
    *,
    show: bool = True,
):
    depth = _get_depth(df)
    depth_label = _get_depth_label(df)
    fig, axes = plt.subplots(1, 3, figsize=(14, 10), sharey=True)
    _style_figure(fig, "Triple Combo")

    track_sizes = [
        _plot_track_group(
            axes[0],
            df,
            depth,
            track1,
            track_title="",
            depth_label=depth_label,
            show_ylabel=True,
            background=TRACK_BACKGROUNDS[0],
            fill_first_curve=True,
        ),
        _plot_track_group(
            axes[1],
            df,
            depth,
            track2,
            track_title="",
            depth_label=depth_label,
            show_ylabel=False,
            background=TRACK_BACKGROUNDS[1],
            prefer_log_scale=True,
        ),
        _plot_track_group(
            axes[2],
            df,
            depth,
            track3,
            track_title="",
            depth_label=depth_label,
            show_ylabel=False,
            background=TRACK_BACKGROUNDS[2],
        ),
    ]

    max_stack = max(track_sizes + [1])
    top_margin = max(0.72, 0.92 - 0.05 * max(0, max_stack - 1))
    fig.subplots_adjust(left=0.075, right=0.985, bottom=0.06, top=top_margin, wspace=0.12)
    if show:
        plt.show()
    return fig


def plot_crossplot(
    df,
    x_curve: str,
    y_curve: str,
    color_curve: str | None = None,
    *,
    show: bool = True,
):
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.invert_yaxis()
    _style_figure(fig, "Crossplot")
    x_values = _get_curve_values(df, x_curve)
    y_values = _get_curve_values(df, y_curve)
    mask = np.isfinite(x_values) & np.isfinite(y_values)
    if color_curve and color_curve in df.columns:
        color_values = _get_curve_values(df, color_curve)
        mask = mask & np.isfinite(color_values)
        scatter = ax.scatter(
            x_values[mask],
            y_values[mask],
            c=color_values[mask],
            cmap="viridis",
            s=18,
            alpha=0.72,
            edgecolors="white",
            linewidths=0.3,
        )
        colorbar = fig.colorbar(scatter, ax=ax, shrink=0.92, pad=0.02)
        colorbar.set_label(color_curve, fontsize=9, color="#18344F")
        colorbar.ax.tick_params(labelsize=8)
    else:
        ax.scatter(
            x_values[mask],
            y_values[mask],
            s=16,
            alpha=0.65,
            color=PALETTE[0],
            edgecolors="white",
            linewidths=0.35,
        )
    ax.set_xlabel(x_curve, fontsize=10, fontweight="bold", color="#18344F")
    ax.set_ylabel(y_curve, fontsize=10, fontweight="bold", color="#18344F")
    ax.set_facecolor("#FBFCFE")
    ax.grid(True, color="#D9E2EC", alpha=0.8, linewidth=0.7)
    for spine in ax.spines.values():
        spine.set_color("#C8D2DC")
    fig.subplots_adjust(left=0.12, right=0.97, bottom=0.12, top=0.90)
    if show:
        plt.show()
    return fig


def plot_histogram(df, curve: str, bins: int = 40, *, show: bool = True):
    fig, ax = plt.subplots(figsize=(7, 4.8))
    _style_figure(fig, "Histogram")
    values = _get_curve_values(df, curve)
    values = values[np.isfinite(values)]
    ax.hist(values, bins=bins, alpha=0.88, color=PALETTE[1], edgecolor="white", linewidth=0.55)
    ax.set_xlabel(curve, fontsize=10, fontweight="bold", color="#18344F")
    ax.set_ylabel("Count", fontsize=10, fontweight="bold", color="#18344F")
    ax.set_facecolor("#FBFCFE")
    ax.grid(True, axis="y", color="#D9E2EC", alpha=0.8, linewidth=0.7)
    for spine in ax.spines.values():
        spine.set_color("#C8D2DC")
    fig.subplots_adjust(left=0.12, right=0.97, bottom=0.16, top=0.88)
    if show:
        plt.show()
    return fig


def plot_pairplot(df, curves: list[str], *, show: bool = True):
    curves = [curve for curve in curves if curve in df.columns]
    unique_curves: list[str] = []
    for curve in curves:
        if curve not in unique_curves:
            unique_curves.append(curve)
    curves = unique_curves[:4]

    if len(curves) < 2:
        fig = _empty_figure("Pairplot", "Select at least two curves for a pairplot.")
        if show:
            plt.show()
        return fig

    count = len(curves)
    fig, axes = plt.subplots(count, count, figsize=(3.2 * count, 3.1 * count))
    _style_figure(fig, "Pairplot")

    for row_index, y_curve in enumerate(curves):
        for col_index, x_curve in enumerate(curves):
            ax = axes[row_index, col_index]
            ax.set_facecolor("#FBFCFE")
            for spine in ax.spines.values():
                spine.set_color("#D9E2EC")
            if row_index == col_index:
                values = _get_curve_values(df, x_curve)
                values = values[np.isfinite(values)]
                ax.hist(values, bins=24,
                    color=PALETTE[col_index % len(PALETTE)],
                    alpha=0.88,
                    edgecolor="white",
                    linewidth=0.45,
                )
            else:
                x_values = _get_curve_values(df, x_curve)
                y_values = _get_curve_values(df, y_curve)
                mask = np.isfinite(x_values) & np.isfinite(y_values)
                ax.scatter(
                    x_values[mask],
                    y_values[mask],
                    s=8,
                    alpha=0.45,
                    color=PALETTE[(row_index + col_index) % len(PALETTE)],
                    edgecolors="none",
                )

            if row_index == count - 1:
                ax.set_xlabel(x_curve, fontsize=8, fontweight="bold", color="#18344F")
            else:
                ax.set_xticklabels([])
            if col_index == 0:
                ax.set_ylabel(y_curve, fontsize=8, fontweight="bold", color="#18344F")
            else:
                ax.set_yticklabels([])
            ax.tick_params(axis="both", labelsize=7, colors="#52606D", length=2)
            ax.grid(True, color="#E6EDF5", linewidth=0.5, alpha=0.7)

    fig.subplots_adjust(left=0.09, right=0.98, bottom=0.08, top=0.93, wspace=0.14, hspace=0.14)
    if show:
        plt.show()
    return fig
