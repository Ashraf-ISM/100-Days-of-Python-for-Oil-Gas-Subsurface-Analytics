"""All plots in one module (matplotlib-based)."""
from __future__ import annotations

import matplotlib.pyplot as plt


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

    resistivity = _find_all_matching(
        columns, ["RT", "RDEP", "RILD", "LLD", "LLS", "RXO", "RES", "ILD", "ILM", "RS"]
    )
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
        return df["DEPTH"].values
    return df.index.values


def plot_multitrack(
    df,
    curves: list[str] | None = None,
    depth_col: str = "DEPTH",
    *,
    show: bool = True,
):
    if curves is None:
        curves = [c for c in df.columns if c != depth_col][:3]
    depth = _get_depth(df)
    n = len(curves)
    fig, axes = plt.subplots(1, n, figsize=(4 * n, 8), sharey=True)
    if n == 1:
        axes = [axes]
    for ax, curve in zip(axes, curves):
        ax.plot(df[curve], depth, label=curve)
        ax.set_xlabel(curve)
        ax.invert_yaxis()
        ax.grid(True, alpha=0.3)
    axes[0].set_ylabel(depth_col)
    fig.suptitle("Multi-Track Log Plot")
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
    depth = _get_depth(df)
    fig, axes = plt.subplots(1, 3, figsize=(12, 8), sharey=True)
    if gr in df.columns:
        axes[0].plot(df[gr], depth, color="green", label=gr)
    axes[0].set_xlabel(gr if gr in df.columns else "Track 1")
    axes[0].invert_yaxis()
    axes[0].grid(True, alpha=0.3)

    if rt in df.columns:
        axes[1].plot(df[rt], depth, color="red", label=rt)
        axes[1].set_xscale("log")
    axes[1].set_xlabel(rt if rt in df.columns else "Track 2")
    axes[1].grid(True, alpha=0.3)

    if nphi in df.columns:
        axes[2].plot(df[nphi], depth, color="blue", label=nphi)
    if rhob in df.columns:
        axes[2].plot(df[rhob], depth, color="black", label=rhob)
    axes[2].set_xlabel("NPHI / RHOB")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()

    axes[0].set_ylabel(depth_col)
    fig.suptitle("Triple Combo")
    if show:
        plt.show()
    return fig


def plot_triple_combo_auto(df, *, show: bool = True):
    columns = list(df.columns)
    track1, track2, track3 = _select_triple_combo_curves(columns)
    depth = _get_depth(df)
    fig, axes = plt.subplots(1, 3, figsize=(12, 8), sharey=True)

    # Track 1: GR + CALI if present
    if track1:
        main = track1[0]
        if main in df.columns:
            axes[0].plot(df[main], depth, color="green", label=main)
        if len(track1) > 1:
            cali = track1[1]
            if cali in df.columns:
                ax_tw = axes[0].twiny()
                ax_tw.plot(df[cali], depth, color="orange", label=cali)
                ax_tw.set_xlabel(cali)
        axes[0].set_xlabel(main)
    axes[0].invert_yaxis()
    axes[0].grid(True, alpha=0.3)

    # Track 2: Resistivity (log scale)
    if track2:
        for curve in track2:
            if curve in df.columns:
                axes[1].plot(df[curve], depth, label=curve)
        axes[1].set_xscale("log")
        axes[1].set_xlabel("Resistivity")
        axes[1].legend(fontsize=8)
    axes[1].grid(True, alpha=0.3)

    # Track 3: Density + Porosity
    if track3:
        for curve in track3:
            if curve in df.columns:
                axes[2].plot(df[curve], depth, label=curve)
        axes[2].set_xlabel("Density / Porosity")
        axes[2].legend(fontsize=8)
    axes[2].grid(True, alpha=0.3)

    axes[0].set_ylabel("DEPTH")
    fig.suptitle("Triple Combo")
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
    fig, axes = plt.subplots(1, 3, figsize=(12, 8), sharey=True)

    # Track 1
    if track1:
        main = track1[0]
        if main in df.columns:
            axes[0].plot(df[main], depth, color="green", label=main)
        if len(track1) > 1:
            ax_tw = axes[0].twiny()
            for extra in track1[1:]:
                if extra in df.columns:
                    ax_tw.plot(df[extra], depth, label=extra)
            ax_tw.set_xlabel("Track 1 (Extra)")
            ax_tw.legend(fontsize=8)
        axes[0].set_xlabel(main)
    axes[0].invert_yaxis()
    axes[0].grid(True, alpha=0.3)

    # Track 2: Resistivity
    if track2:
        for curve in track2:
            if curve in df.columns:
                axes[1].plot(df[curve], depth, label=curve)
        axes[1].set_xscale("log")
        axes[1].set_xlabel("Resistivity")
        axes[1].legend(fontsize=8)
    axes[1].grid(True, alpha=0.3)

    # Track 3: Density + Porosity
    if track3:
        for curve in track3:
            if curve in df.columns:
                axes[2].plot(df[curve], depth, label=curve)
        axes[2].set_xlabel("Density / Porosity")
        axes[2].legend(fontsize=8)
    axes[2].grid(True, alpha=0.3)

    axes[0].set_ylabel("DEPTH")
    fig.suptitle("Triple Combo")
    if show:
        plt.show()
    return fig


def plot_crossplot(df, x_curve: str, y_curve: str, *, show: bool = True):
    fig = plt.figure(figsize=(6, 6))
    plt.scatter(df[x_curve], df[y_curve], s=6, alpha=0.6)
    plt.xlabel(x_curve)
    plt.ylabel(y_curve)
    plt.grid(True, alpha=0.3)
    plt.title("Crossplot")
    if show:
        plt.show()
    return fig


def plot_histogram(df, curve: str, *, show: bool = True):
    fig = plt.figure(figsize=(6, 4))
    plt.hist(df[curve].dropna(), bins=40, alpha=0.8)
    plt.xlabel(curve)
    plt.ylabel("Count")
    plt.title("Histogram")
    plt.grid(True, alpha=0.3)
    if show:
        plt.show()
    return fig
