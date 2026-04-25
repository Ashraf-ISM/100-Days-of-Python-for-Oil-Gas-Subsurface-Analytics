"""
log_availability_radar.py
=========================

Features
--------
* Rich alias registry covering modern LWD / wireline mnemonics
* Structured data models (LogAvailabilityItem, AvailabilityReport)
* Dual visual themes  (DARK_THEME, LIGHT_THEME)
* Configurable quality thresholds with automatic grade colouring
* Radar chart  – per-log availability spider plot with zone bands
* Availability bar chart – fallback for < 3 logs or as standalone
* Multi-well heatmap  – log-vs-well availability matrix
* PetroARX branding strip on every figure

Public API
----------
    compute_log_availability(df, well_name, thresholds) -> AvailabilityReport
    build_log_availability_radar_figure(...)            -> Figure
    build_log_availability_bar_figure(...)              -> Figure
    build_multi_well_availability_figure(...)           -> Figure
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

# ── Mnemonic / alias registry ─────────────────────────────────────────────────

STANDARD_LOG_ALIASES: dict[str, tuple[str, ...]] = {
    # Gamma Ray
    "GR":    ("GR", "GAMMA", "GAMMA_RAY", "GAMMARAY", "SGR", "CGR", "GAPI", "API", "GRC", "NGR"),
    # Bulk Density
    "RHOB":  ("RHOB", "RHOZ", "RHO", "DEN", "DENS", "DENB", "DENSITY", "ROHB"),
    # Neutron Porosity
    "NPHI":  ("NPHI", "TNPH", "NEU", "NPHI_LS", "NEUTRON", "HNPO", "NPOR"),
    # Compressional Slowness
    "DTC":   ("DT", "DTC", "SONIC", "AC", "DTCO", "DT4P", "DTLF", "DTLN"),
    # Shear Slowness
    "DTS":   ("DTS", "DTSM", "DTSH", "DT4S", "DTS1", "DTS2"),
    # Deep Resistivity
    "RT":    ("RT", "ILD", "LLD", "RES", "RESD", "AT90", "RDEP", "RILD", "RDEEP", "ILM"),
    # Shallow / Micro Resistivity
    "RXOZ":  ("RXOZ", "RXO", "MSFL", "SFL", "RMLL", "RLA1", "RLA2"),
    # Caliper
    "CALI":  ("CALI", "CAL", "CALIPER", "HCAL", "CALD", "DCAL", "C1", "C2"),
    # Spontaneous Potential
    "SP":    ("SP", "SPONT", "SPONTANEOUS", "SPPD", "SPR"),
    # Photoelectric Factor
    "PEF":   ("PEF", "PE", "PEFZ", "PEPH", "PEFL"),
    # Delta-Rho (density correction)
    "DRHO":  ("DRHO", "DRHOB", "HDRS", "DRHOZ"),
    # Borehole Temperature
    "TEMP":  ("TEMP", "BHT", "TEMPERATURE", "WTEP"),
    # Nuclear Magnetic Resonance
    "NMR":   ("CMR", "NMR", "T2LM", "MPHE", "MFFI"),
    # Formation Tester
    "MDT":   ("MDT", "FMT", "RFT", "WFT", "PRESSURE"),
    # Image Logs
    "FMI":   ("FMI", "FMS", "EMI", "OBI", "UBI", "OBMI"),
    # Magnetic Susceptibility / Spectral GR
    "SPEC":  ("CGR", "URAN", "THOR", "POTA", "K40", "SPECGR"),
}

DEPTH_TOKENS: frozenset[str] = frozenset({
    "DEPTH", "DEPT", "MD", "TVD", "TVDSS", "MDRKB", "TVDRKB",
    "TIME", "DATE", "DATETIME", "INDEX", "SAMPLE", "ROW",})


# ── Quality configuration ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class QualityThresholds:
    """Availability thresholds that map percentage to a quality grade."""

    excellent: float = 90.0
    good: float = 70.0
    fair: float = 50.0

    def grade(self, availability: float) -> str:
        if availability >= self.excellent:
            return "EXCELLENT"
        if availability >= self.good:
            return "GOOD"
        if availability >= self.fair:
            return "FAIR"
        return "POOR"


# ── Visual theme ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RadarTheme:
    """All colour / typography tokens for the chart family."""

    # Canvas
    fig_bg: str = "#0A1628"
    panel_bg: str = "#0E1E35"

    # Radar polygon
    primary_color: str = "#4DCFFF"
    fill_alpha: float = 0.16
    line_width: float = 2.0
    marker_size: float = 44.0

    # Grid
    grid_color: str = "#182B45"
    spoke_color: str = "#16284096"
    ring_label_color: str = "#3F607E"

    # Availability zone colours
    zone_excellent: str = "#00D4A4"
    zone_good: str = "#4DCFFF"
    zone_fair: str = "#FFB347"
    zone_poor: str = "#FF5E6C"

    # Text
    title_color: str = "#E4F3FF"
    label_color: str = "#96B8D4"
    accent_color: str = "#4DCFFF"
    muted_color: str = "#3F607E"

    # Info-panel accent strip
    accent_strip: str = "#4DCFFF"

    def zone_color(self, availability: float, thresholds: QualityThresholds) -> str:
        return {
            "EXCELLENT": self.zone_excellent,
            "GOOD":      self.zone_good,
            "FAIR":      self.zone_fair,
            "POOR":      self.zone_poor,
        }[thresholds.grade(availability)]


DARK_THEME = RadarTheme()

LIGHT_THEME = RadarTheme(
    fig_bg="#F0F5FA",
    panel_bg="#FFFFFF",
    primary_color="#0066CC",
    fill_alpha=0.12,
    line_width=2.0,
    marker_size=44.0,
    grid_color="#D0DDE8",
    spoke_color="#C0D0DE",
    ring_label_color="#8FA8C0",
    zone_excellent="#00936F",
    zone_good="#0066CC",
    zone_fair="#C46B00",
    zone_poor="#C0202E",
    title_color="#0D2137",
    label_color="#2A4A65",
    accent_color="#0066CC",
    muted_color="#8FA8C0",
    accent_strip="#0066CC",
)


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class LogAvailabilityItem:
    """Per-curve availability statistics."""

    label: str          # Canonical mnemonic or display name 
    column: str         # Original DataFrame column name
    availability: float # 0–100 % 
    is_standard: bool   # True if matched against STANDARD_LOG_ALIASES
    valid_count: int    # Non-null sample count
    total_count: int    # Total depth samples

    @property
    def missing_count(self) -> int:
        return self.total_count - self.valid_count

    @property
    def missing_pct(self) -> float:
        return 100.0 - self.availability

    def __repr__(self) -> str:
        return (
            f"LogAvailabilityItem({self.label!r}, "
            f"avail={self.availability:.1f}%, "
            f"valid={self.valid_count}/{self.total_count})"
        )


@dataclass
class AvailabilityReport:
    """Aggregated well-level availability report."""

    items: list[LogAvailabilityItem]
    well_name: str = "Unknown Well"
    thresholds: QualityThresholds = field(default_factory=QualityThresholds)

    # ------------------------------------------------------------------

    @property
    def overall_score(self) -> float:
        if not self.items:
            return 0.0
        return float(np.mean([item.availability for item in self.items]))

    @property
    def grade(self) -> str:
        return self.thresholds.grade(self.overall_score)

    @property
    def standard_items(self) -> list[LogAvailabilityItem]:
        return [i for i in self.items if i.is_standard]

    @property
    def non_standard_items(self) -> list[LogAvailabilityItem]:
        return [i for i in self.items if not i.is_standard]

    @property
    def missing_standard_logs(self) -> list[str]:
        found = {i.label for i in self.standard_items}
        return [k for k in STANDARD_LOG_ALIASES if k not in found]

    def to_dataframe(self) -> pd.DataFrame:
        """Return a tidy summary DataFrame for export or further analysis."""
        return pd.DataFrame(
            [
                {
                    "Label":        item.label,
                    "Column":       item.column,
                    "Availability": round(item.availability, 2),
                    "Valid":        item.valid_count,
                    "Total":        item.total_count,
                    "Missing":      item.missing_count,
                    "Standard":     item.is_standard,
                    "Grade":        self.thresholds.grade(item.availability),
                }
                for item in self.items
            ]
        )

    def __repr__(self) -> str:
        return (
            f"AvailabilityReport(well={self.well_name!r}, "
            f"logs={len(self.items)}, score={self.overall_score:.1f}%, "
            f"grade={self.grade!r})"
        )


# ── Internal helpers ──────────────────────────────────────────────────────────

def _empty_figure(message: str, theme: RadarTheme = DARK_THEME) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(7.0, 5.0), facecolor=theme.fig_bg)
    ax.set_facecolor(theme.fig_bg)
    ax.axis("off")
    ax.text(
        0.5, 0.5, message,
        ha="center", va="center",
        fontsize=12, color=theme.label_color,
        fontfamily="monospace",
        transform=ax.transAxes,
    )
    _stamp(fig, theme)
    return fig


def _stamp(fig: plt.Figure, theme: RadarTheme) -> None:
    """Add PetroARX branding strip along the bottom."""
    fig.text(
        0.012, 0.008,
        "PetroARX  ·  Log QC Module  ·  Availability Intelligence",
        ha="left", va="bottom",
        fontsize=6.0, color=theme.muted_color,
        fontfamily="monospace", alpha=0.8,
    )


def _normalize(value: Any) -> str:
    return str(value).strip().upper()


def _is_depth_like(column: str) -> bool:
    norm = _normalize(column)
    if norm in DEPTH_TOKENS:
        return True
    return any(tok in norm for tok in DEPTH_TOKENS)


def _find_column(
    numeric_cols: list[str],
    norm_lookup: dict[str, str],
    aliases: tuple[str, ...],
    used: set[str],
) -> str | None:
    """Exact match first, then token-containment fallback."""
    for alias in aliases:
        candidate = norm_lookup.get(alias.upper())
        if candidate and candidate not in used:
            return candidate
    tokens = tuple(a.upper() for a in aliases)
    for col in numeric_cols:
        if col in used:
            continue
        if any(tok in _normalize(col) for tok in tokens):
            return col
    return None


def _short_label(column: str) -> str:
    lbl = _normalize(column).replace("_", " ")
    return lbl if len(lbl) <= 10 else lbl[:9] + "…"


# ── Core computation ──────────────────────────────────────────────────────────

def compute_log_availability(
    df: pd.DataFrame,
    well_name: str = "Unknown Well",
    thresholds: QualityThresholds | None = None,
) -> AvailabilityReport:
    """
    Analyse a well-log DataFrame and return a structured availability report.

    Parameters
    ----------
    df:
        DataFrame whose columns represent log curves (depth as index or column).
    well_name:
        Well identifier used in reports and figure labels.
    thresholds:
        Quality thresholds; defaults to ``QualityThresholds()``.

    Returns
    -------
    AvailabilityReport
    """
    thresholds = thresholds or QualityThresholds()
    empty = AvailabilityReport(items=[], well_name=well_name, thresholds=thresholds)

    if df is None or df.empty:
        return empty

    num_cols = [str(c) for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not num_cols:
        return empty

    norm_lookup: dict[str, str] = {_normalize(c): c for c in num_cols}
    used: set[str] = set()
    items: list[LogAvailabilityItem] = []
    n_rows = len(df)

    # ── Standard aliases ──────────────────────────────────────────────────────
    for label, aliases in STANDARD_LOG_ALIASES.items():
        matched = _find_column(num_cols, norm_lookup, aliases, used)
        if matched is None:
            continue
        values = pd.to_numeric(df[matched], errors="coerce")
        valid = int(values.notna().sum())
        avail = valid / n_rows * 100.0 if n_rows else 0.0
        if avail <= 0:
            continue
        used.add(matched)
        items.append(LogAvailabilityItem(
            label=label, column=matched,
            availability=avail, is_standard=True,
            valid_count=valid, total_count=n_rows,
        ))

    # ── Extra / non-standard curves ───────────────────────────────────────────
    for col in num_cols:
        if col in used or _is_depth_like(col):
            continue
        values = pd.to_numeric(df[col], errors="coerce")
        valid = int(values.notna().sum())
        avail = valid / n_rows * 100.0 if n_rows else 0.0
        if avail <= 0:
            continue
        items.append(LogAvailabilityItem(
            label=_short_label(col), column=col,
            availability=avail, is_standard=False,
            valid_count=valid, total_count=n_rows,
        ))

    return AvailabilityReport(items=items, well_name=well_name, thresholds=thresholds)


# ── Private drawing helpers ───────────────────────────────────────────────────

def _quality_ring_bands(ax, thresholds: QualityThresholds, theme: RadarTheme) -> None:
    """Fill coloured concentric bands corresponding to quality zones."""
    angles_full = np.linspace(0, 2 * np.pi, 360, endpoint=True)
    bands = [
        (0,                    thresholds.fair,      theme.zone_poor,      0.05),
        (thresholds.fair,      thresholds.good,      theme.zone_fair,      0.045),
        (thresholds.good,      thresholds.excellent, theme.zone_good,      0.04),
        (thresholds.excellent, 100,                  theme.zone_excellent, 0.055),
    ]
    for r_lo, r_hi, color, alpha in bands:
        ax.fill_between(
            angles_full,
            np.full_like(angles_full, r_lo),
            np.full_like(angles_full, r_hi),
            color=color, alpha=alpha, linewidth=0, zorder=1,
        )


def _draw_info_panel(
    fig: plt.Figure,
    report: AvailabilityReport,
    theme: RadarTheme,
    rect: tuple[float, float, float, float] = (0.83, 0.10, 0.15, 0.80),
) -> None:
    """Render the right-side statistics / legend panel."""
    iax = fig.add_axes(rect)
    iax.set_facecolor(theme.panel_bg)
    iax.set_xlim(0, 1)
    iax.set_ylim(0, 1)
    iax.axis("off")

    # Accent strip on the left edge
    iax.add_patch(mpatches.FancyBboxPatch(
        (0.0, 0.0), 0.025, 1.0,
        boxstyle="square,pad=0",
        facecolor=theme.accent_strip, edgecolor="none",
        transform=iax.transAxes,
    ))

    # ── Overall score ──────────────────────────────────────────────────────────
    score = report.overall_score
    grade_color = theme.zone_color(score, report.thresholds)

    iax.text(0.55, 0.96, "OVERALL", ha="center", va="top",
             fontsize=6.5, color=theme.muted_color,
             fontfamily="monospace", fontweight="700")
    iax.text(0.55, 0.89, f"{score:.1f}%", ha="center", va="top",
             fontsize=20, color=grade_color,
             fontfamily="monospace", fontweight="900")
    iax.text(0.55, 0.82, report.grade, ha="center", va="top",
             fontsize=8.5, color=grade_color,
             fontfamily="monospace", fontweight="700")

    _divider(iax, 0.79, theme)

    # ── Statistics block ──────────────────────────────────────────────────────
    n_std   = len(report.standard_items)
    n_extra = len(report.non_standard_items)
    n_miss  = len(report.missing_standard_logs)

    stats = [
        ("LOGS",     f"{n_std + n_extra}"),
        ("STANDARD", f"{n_std}"),
        ("EXTRA",    f"{n_extra}"),
        ("ABSENT",   f"{n_miss}"),
        ("ROWS",     f"{report.items[0].total_count:,}" if report.items else "—"),
    ]
    for k, (lbl, val) in enumerate(stats):
        y = 0.76 - k * 0.078
        iax.text(0.10, y, lbl, ha="left", va="center",
                 fontsize=6.0, color=theme.muted_color,
                 fontfamily="monospace")
        iax.text(0.94, y, val, ha="right", va="center",
                 fontsize=7.5, color=theme.label_color,
                 fontfamily="monospace", fontweight="700")

    _divider(iax, 0.36, theme)

    # ── Zone legend ───────────────────────────────────────────────────────────
    iax.text(0.55, 0.34, "ZONES", ha="center", va="top",
             fontsize=6.5, color=theme.muted_color,
             fontfamily="monospace", fontweight="700")

    thresholds = report.thresholds
    zone_rows = [
        (theme.zone_excellent, f"≥{thresholds.excellent:.0f}%  EXCELLENT"),
        (theme.zone_good,      f"≥{thresholds.good:.0f}%  GOOD"),
        (theme.zone_fair,      f"≥{thresholds.fair:.0f}%  FAIR"),
        (theme.zone_poor,      f" <{thresholds.fair:.0f}%  POOR"),
    ]
    for k, (color, lbl) in enumerate(zone_rows):
        y = 0.29 - k * 0.068
        iax.add_patch(mpatches.FancyBboxPatch(
            (0.08, y - 0.016), 0.14, 0.030,
            boxstyle="round,pad=0.003",
            facecolor=color, edgecolor="none",
        ))
        iax.text(0.28, y, lbl, ha="left", va="center",
                 fontsize=5.8, color=theme.label_color,
                 fontfamily="monospace")

    _divider(iax, 0.02, theme)

    # ── Well name ─────────────────────────────────────────────────────────────
    iax.text(0.55, 0.01, report.well_name, ha="center", va="bottom",
             fontsize=6.0, color=theme.accent_color,
             fontfamily="monospace", fontweight="700",
             clip_on=True)


def _divider(ax, y: float, theme: RadarTheme) -> None:
    ax.axhline(y, xmin=0.04, xmax=0.98, color=theme.grid_color, linewidth=0.6)


# ── Public figure builders ────────────────────────────────────────────────────

def build_log_availability_radar_figure(
    df: pd.DataFrame,
    title: str = "Log Intelligence — Availability Radar",
    well_name: str = "Unknown Well",
    theme: RadarTheme = DARK_THEME,
    thresholds: QualityThresholds | None = None,
    figsize: tuple[float, float] = (9.5, 7.5),
    show_non_standard: bool = True,
    max_logs: int = 16,
) -> plt.Figure:
    """
    Render a professional polar radar chart of well-log availability.

    If fewer than 3 logs are detected the function automatically falls back
    to ``build_log_availability_bar_figure``.

    Parameters
    ----------
    df:
        Well-log DataFrame.
    title:
        Main figure title.
    well_name:
        Well identifier displayed in the side panel and branding strip.
    theme:
        ``DARK_THEME`` (default) or ``LIGHT_THEME``, or a custom ``RadarTheme``.
    thresholds:
        Availability quality thresholds.
    figsize:
        Figure size in inches ``(width, height)``.
    show_non_standard:
        Include extra/non-standard log curves beyond the alias registry.
    max_logs:
        Maximum spoke count; excess logs are silently truncated.

    Returns
    -------
    matplotlib.figure.Figure
    """
    thresholds = thresholds or QualityThresholds()
    report = compute_log_availability(df, well_name=well_name, thresholds=thresholds)

    display_items = report.standard_items + (
        report.non_standard_items if show_non_standard else []
    )
    if not display_items:
        return _empty_figure("No valid log curves found in the DataFrame.", theme)

    # Graceful fallback for very few logs
    if len(display_items) < 3:
        return build_log_availability_bar_figure(
            df, title=title, well_name=well_name,
            theme=theme, thresholds=thresholds,
        )

    items = display_items[:max_logs]
    n = len(items)
    labels = [i.label for i in items]
    values = [i.availability for i in items]

    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    closed_angles = angles + angles[:1]
    closed_values  = values + values[:1]

    # ── Layout ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=figsize, facecolor=theme.fig_bg)
    ax  = fig.add_axes([0.04, 0.06, 0.77, 0.88], projection="polar")
    ax.set_facecolor(theme.panel_bg)

    # ── Polar configuration ───────────────────────────────────────────────────
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 112)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(
        ["25%", "50%", "75%", "100%"],
        fontsize=6.5, color=theme.ring_label_color,
        fontfamily="monospace",
    )
    ax.set_rlabel_position(8)

    # Grid
    ax.grid(color=theme.grid_color, linewidth=0.65, linestyle="--", alpha=0.7)
    ax.spines["polar"].set_color(theme.grid_color)
    ax.spines["polar"].set_linewidth(0.7)

    # Quality zone colour bands
    _quality_ring_bands(ax, thresholds, theme)

    # Custom spoke lines
    for angle in angles:
        ax.plot(
            [angle, angle], [0, 100],
            color=theme.spoke_color, linewidth=0.55, alpha=0.7, zorder=1,
        )

    # ── Radar polygon ─────────────────────────────────────────────────────────
    glow_fx = [
        pe.Stroke(linewidth=theme.line_width + 3.5,
                  foreground=theme.primary_color, alpha=0.18),
        pe.Normal(),
    ]
    ax.plot(
        closed_angles, closed_values,
        color=theme.primary_color,
        linewidth=theme.line_width,
        linestyle="-",
        zorder=4,
        path_effects=glow_fx,
    )
    ax.fill(
        closed_angles, closed_values,
        color=theme.primary_color,
        alpha=theme.fill_alpha,
        zorder=3,
    )

    # ── Per-spoke dot markers ──────────────────────────────────────────────────
    for angle, value, item in zip(angles, values, items):
        dot_color = theme.zone_color(value, thresholds)
        marker    = "o" if item.is_standard else "D"
        ax.scatter(
            [angle], [value],
            s=theme.marker_size,
            color=dot_color,
            edgecolors=theme.fig_bg,
            linewidths=1.1,
            marker=marker,
            zorder=6,
        )

    # ── Spoke tick labels  ─────────────────────────────────────────────────────
    ax.set_xticks(angles)
    tick_lbls = [f"{lbl}\n{v:.0f}%" for lbl, v in zip(labels, values)]
    ax.set_xticklabels(
        tick_lbls,
        fontsize=7.5,
        fontweight="700",
        color=theme.label_color,
        fontfamily="monospace",
    )
    ax.tick_params(axis="x", pad=13)

    # ── Title ─────────────────────────────────────────────────────────────────
    ax.set_title(
        title,
        fontsize=12.5,
        fontweight="800",
        color=theme.title_color,
        fontfamily="monospace",
        pad=26,
    )

    # ── Info panel ────────────────────────────────────────────────────────────
    # Rebuild report with full data so the panel shows correct totals
    full_report = compute_log_availability(df, well_name=well_name, thresholds=thresholds)
    _draw_info_panel(fig, full_report, theme, rect=(0.83, 0.06, 0.155, 0.88))

    _stamp(fig, theme)
    return fig


# ── Standalone bar chart ──────────────────────────────────────────────────────

def build_log_availability_bar_figure(
    df: pd.DataFrame,
    title: str = "Log Availability — Quality Summary",
    well_name: str = "Unknown Well",
    theme: RadarTheme = DARK_THEME,
    thresholds: QualityThresholds | None = None,
    figsize: tuple[float, float] = (9.5, 5.5),
    show_non_standard: bool = True,
    max_logs: int = 24,
) -> plt.Figure:
    """
    Render a horizontal bar chart of per-log availability.

    Useful as a companion view, a fallback for sparse datasets, or when an
    exact numeric comparison is preferred over the radar overview.

    Parameters
    ----------
    df, title, well_name, theme, thresholds, show_non_standard, max_logs:
        Same semantics as ``build_log_availability_radar_figure``.
    figsize:
        Figure size in inches ``(width, height)``.

    Returns
    -------
    matplotlib.figure.Figure
    """
    thresholds = thresholds or QualityThresholds()
    report = compute_log_availability(df, well_name=well_name, thresholds=thresholds)

    display_items = report.standard_items + (
        report.non_standard_items if show_non_standard else []
    )
    if not display_items:
        return _empty_figure("No valid log curves found in the DataFrame.", theme)

    items = display_items[:max_logs]
    labels = [i.label for i in items]
    values = [i.availability for i in items]
    colors = [theme.zone_color(v, thresholds) for v in values]

    n = len(items)
    fig_h = max(figsize[1], n * 0.42 + 1.8)
    fig, ax = plt.subplots(figsize=(figsize[0], fig_h), facecolor=theme.fig_bg)
    ax.set_facecolor(theme.panel_bg)

    y_pos = np.arange(n)

    # Background track
    ax.barh(y_pos, [100] * n, height=0.62,
            color=theme.grid_color, alpha=0.45, linewidth=0)

    # Availability bars
    bars = ax.barh(y_pos, values, height=0.62,
                   color=colors, linewidth=0, zorder=3)

    # Zone threshold lines
    for threshold, label_txt in [
        (thresholds.fair,      f"FAIR {thresholds.fair:.0f}%"),
        (thresholds.good,      f"GOOD {thresholds.good:.0f}%"),
        (thresholds.excellent, f"EXC {thresholds.excellent:.0f}%"),
    ]:
        ax.axvline(threshold, color=theme.muted_color,
                   linewidth=0.65, linestyle="--", alpha=0.6, zorder=2)
        ax.text(threshold + 0.5, n - 0.15, label_txt,
                ha="left", va="top", fontsize=5.5,
                color=theme.muted_color, fontfamily="monospace")

    # Value annotations
    for bar, value, item in zip(bars, values, items):
        inside = value > 15
        x_pos  = value - 1.0 if inside else value + 1.0
        ha     = "right" if inside else "left"
        color  = theme.panel_bg if inside else theme.label_color
        ax.text(x_pos, bar.get_y() + bar.get_height() / 2,
                f"{value:.1f}%",
                ha=ha, va="center",
                fontsize=7.0, fontweight="700",
                color=color, fontfamily="monospace")

    # Axes styling
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=8.5, fontweight="700",
                       color=theme.label_color, fontfamily="monospace")
    ax.set_xlim(0, 105)
    ax.set_xlabel("Availability  (%)", fontsize=8,
                  color=theme.muted_color, fontfamily="monospace")
    ax.tick_params(axis="x", colors=theme.muted_color, labelsize=7.5)
    ax.tick_params(axis="y", length=0)
    ax.invert_yaxis()

    for spine in ax.spines.values():
        spine.set_color(theme.grid_color)
    ax.xaxis.label.set_color(theme.muted_color)
    ax.tick_params(axis="x", colors=theme.ring_label_color)

    # Non-standard marker legend
    has_extra = any(not i.is_standard for i in items)
    if has_extra:
        ax.scatter([], [], marker="o", s=30, color=theme.label_color, label="Standard")
        ax.scatter([], [], marker="D", s=28, color=theme.label_color, label="Extra")

    # Overall score annotation
    score = report.overall_score
    grade_color = theme.zone_color(score, thresholds)
    ax.text(0.99, 0.98,
            f"Overall  {score:.1f}%  [{report.grade}]",
            ha="right", va="top",
            fontsize=9, fontweight="800",
            color=grade_color, fontfamily="monospace",
            transform=ax.transAxes)

    ax.set_title(
        f"{title}\n{well_name}",
        fontsize=11.5, fontweight="800",
        color=theme.title_color, fontfamily="monospace",
        loc="left", pad=10,
    )

    plt.tight_layout()
    _stamp(fig, theme)
    return fig


# ── Multi-well comparison heatmap ─────────────────────────────────────────────

def build_multi_well_availability_figure(
    well_data: dict[str, pd.DataFrame],
    title: str = "Multi-Well Log Availability Matrix",
    theme: RadarTheme = DARK_THEME,
    thresholds: QualityThresholds | None = None,
    figsize: tuple[float, float] | None = None,
    show_non_standard: bool = False,
) -> plt.Figure:
    """
    Render a heatmap-style log × well availability matrix.

    Useful for QC across an entire well programme at a glance.

    Parameters
    ----------
    well_data:
        ``{well_name: DataFrame}`` mapping.
    title:
        Figure title.
    theme:
        Visual theme.
    thresholds:
        Quality thresholds.
    figsize:
        Auto-computed from dataset dimensions if ``None``.
    show_non_standard:
        Include non-standard curves (disabled by default to keep the matrix clean).

    Returns
    -------
    matplotlib.figure.Figure
    """
    thresholds = thresholds or QualityThresholds()

    reports: dict[str, AvailabilityReport] = {
        name: compute_log_availability(df, well_name=name, thresholds=thresholds)
        for name, df in well_data.items()
    }

    # Collect ordered unique log labels
    seen: set[str] = set()
    all_labels: list[str] = []
    for report in reports.values():
        src = report.standard_items + (report.non_standard_items if show_non_standard else [])
        for item in src:
            if item.label not in seen:
                all_labels.append(item.label)
                seen.add(item.label)

    well_names = list(reports.keys())
    n_wells = len(well_names)
    n_logs  = len(all_labels)

    if n_logs == 0 or n_wells == 0:
        return _empty_figure("No data available for multi-well comparison.", theme)

    # Build matrix (rows = logs, cols = wells)
    matrix = np.full((n_logs, n_wells), np.nan)
    for j, wname in enumerate(well_names):
        lmap = {i.label: i.availability for i in reports[wname].items}
        for k, lbl in enumerate(all_labels):
            if lbl in lmap:
                matrix[k, j] = lmap[lbl]

    if figsize is None:
        figsize = (
            max(8.0, n_wells * 2.0 + 2.5),
            max(5.0, n_logs  * 0.48 + 2.8),
        )

    fig, ax = plt.subplots(figsize=figsize, facecolor=theme.fig_bg)
    ax.set_facecolor(theme.panel_bg)

    cmap = LinearSegmentedColormap.from_list(
        "petro_qc",
        [
            theme.panel_bg,       # absent / NaN
            theme.zone_poor,
            theme.zone_fair,
            theme.zone_good,
            theme.zone_excellent,
        ],
        N=512,
    )
    cmap.set_bad(theme.panel_bg)

    im = ax.imshow(
        matrix, aspect="auto",
        cmap=cmap, vmin=0, vmax=100,
        interpolation="nearest",
    )

    # Cell text annotations
    for k in range(n_logs):
        for j in range(n_wells):
            val = matrix[k, j]
            if np.isnan(val):
                ax.text(j, k, "—", ha="center", va="center",
                        fontsize=8, color=theme.muted_color,
                        fontfamily="monospace")
            else:
                txt_color = "#FFFFFF" if val < 65 else "#090F1C"
                ax.text(j, k, f"{val:.0f}%", ha="center", va="center",
                        fontsize=7.5, fontweight="700",
                        color=txt_color, fontfamily="monospace")

    # Axes
    ax.set_xticks(range(n_wells))
    ax.set_xticklabels(
        well_names, rotation=38, ha="right",
        fontsize=8.5, fontweight="700",
        color=theme.label_color, fontfamily="monospace",
    )
    ax.set_yticks(range(n_logs))
    ax.set_yticklabels(
        all_labels,
        fontsize=8.5, fontweight="700",
        color=theme.label_color, fontfamily="monospace",
    )
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_color(theme.grid_color)
        spine.set_linewidth(0.7)

    # Minor grid (cell separators)
    ax.set_xticks(np.arange(-0.5, n_wells, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, n_logs,  1), minor=True)
    ax.grid(which="minor", color=theme.fig_bg, linewidth=1.4)
    ax.tick_params(which="minor", length=0)

    # Per-well overall score below column headers
    for j, wname in enumerate(well_names):
        sc    = reports[wname].overall_score
        gcol  = theme.zone_color(sc, thresholds)
        ax.text(j, -0.9, f"{sc:.0f}%",
                ha="center", va="center",
                fontsize=7.5, fontweight="800",
                color=gcol, fontfamily="monospace",
                transform=ax.transData, clip_on=False)

    # Colour bar
    cbar = fig.colorbar(im, ax=ax, fraction=0.018, pad=0.015)
    cbar.ax.tick_params(colors=theme.label_color, labelsize=7)
    cbar.set_label("Availability  (%)", fontsize=7.5,
                   color=theme.label_color, fontfamily="monospace")
    cbar.outline.set_color(theme.grid_color)

    ax.set_title(
        title,
        fontsize=13, fontweight="800",
        color=theme.title_color, fontfamily="monospace",
        pad=14,
    )

    plt.tight_layout()
    _stamp(fig, theme)
    return fig