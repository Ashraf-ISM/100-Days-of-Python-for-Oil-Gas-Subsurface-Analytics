"""All plots in one module (matplotlib-based)."""
from __future__ import annotations

import matplotlib.pyplot as plt


def _get_depth(df):
    if "DEPTH" in df.columns:
        return df["DEPTH"].values
    return df.index.values


def plot_multitrack(df, curves: list[str] | None = None, depth_col: str = "DEPTH"):
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
    plt.show()


def plot_triple_combo(df, gr="GR", rt="LLD", nphi="NPHI", rhob="RHOB", depth_col="DEPTH"):
    depth = _get_depth(df)
    fig, axes = plt.subplots(1, 3, figsize=(12, 8), sharey=True)
    axes[0].plot(df[gr], depth, color="green")
    axes[0].set_xlabel(gr)
    axes[0].invert_yaxis()
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(df[rt], depth, color="red")
    axes[1].set_xlabel(rt)
    axes[1].set_xscale("log")
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(df[nphi], depth, color="blue", label=nphi)
    if rhob in df.columns:
        axes[2].plot(df[rhob], depth, color="black", label=rhob)
    axes[2].set_xlabel("NPHI / RHOB")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()

    axes[0].set_ylabel(depth_col)
    fig.suptitle("Triple Combo")
    plt.show()


def plot_crossplot(df, x_curve: str, y_curve: str):
    plt.figure(figsize=(6, 6))
    plt.scatter(df[x_curve], df[y_curve], s=6, alpha=0.6)
    plt.xlabel(x_curve)
    plt.ylabel(y_curve)
    plt.grid(True, alpha=0.3)
    plt.title("Crossplot")
    plt.show()


def plot_histogram(df, curve: str):
    plt.figure(figsize=(6, 4))
    plt.hist(df[curve].dropna(), bins=40, alpha=0.8)
    plt.xlabel(curve)
    plt.ylabel("Count")
    plt.title("Histogram")
    plt.grid(True, alpha=0.3)
    plt.show()
