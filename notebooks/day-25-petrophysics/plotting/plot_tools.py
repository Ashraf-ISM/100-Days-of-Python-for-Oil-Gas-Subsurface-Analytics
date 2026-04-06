"""All plots in one module (matplotlib-based)."""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import ticker

PALETTE = [
    "#0F4C81",
    "#D1495B",
    "#2F855A",
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


def plot_multitrack(
    df,
    curves: list[str] | None = None,
    depth_col: str = "DEPTH",
    *,
    show: bool = True,
):
    available_curves = [curve for curve in df.columns if curve != depth_col]
    if curves is None:
        curves = available_curves[:4]
    else:
        curves = [curve for curve in curves if curve in df.columns and curve != depth_col]

    if not curves:
        fig = _empty_figure("Multi-Track Log Plot", "No curves available for multi-track plotting.")
        if show:
            plt.show()
        return fig

    depth = _get_depth(df)
    depth_label = _get_depth_label(df, depth_col)
    n_tracks = len(curves)
    fig, axes = plt.subplots(
        1,
        n_tracks,
        figsize=(max(3.2 * n_tracks, 10), 9.5),
        sharey=True,
    )
    if n_tracks == 1:
        axes = [axes]

    _style_figure(fig, "Multi-Track Log Plot")
    for index, (ax, curve) in enumerate(zip(axes, curves)):
        color = _curve_color(index)
        values = _get_curve_values(df, curve)
        use_log_scale = _is_resistivity_curve(curve) and _can_use_log(values)
        _style_track_axis(
            ax,
            label=curve,
            color=color,
            background=TRACK_BACKGROUNDS[index % len(TRACK_BACKGROUNDS)],
            depth_label=depth_label,
            show_ylabel=index == 0,
            use_log_scale=use_log_scale,
        )
        _plot_curve(ax, df, depth, curve, color, linewidth=1.55)
        ax.text(
            0.03,
            0.02,
            curve,
            fontsize=8,
            color="#52606D",
            transform=ax.transAxes,
            va="bottom",
        )

    fig.subplots_adjust(left=0.07, right=0.985, bottom=0.06, top=0.90, wspace=0.1)
    if show:
        plt.show()
    return fig


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
                ax.hist(
                    values,
                    bins=24,
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
