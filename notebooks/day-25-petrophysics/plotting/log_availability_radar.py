from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

STANDARD_LOG_ALIASES: dict[str, tuple[str, ...]] = {
    "GR": ("GR", "GAMMA", "GAMMA_RAY", "GAMMARAY", "SGR", "CGR", "GAPI", "API"),
    "RHOB": ("RHOB", "RHOZ", "RHO", "DEN", "DENS", "DENB"),
    "NPHI": ("NPHI", "TNPH", "NEU", "NPHI_LS", "NPHI"),
    "DT": ("DT", "DTC", "SONIC", "AC"),
    "RT": ("RT", "ILD", "LLD", "LLS", "RES", "RESD", "AT90", "RDEP", "RILD"),
    "CALI": ("CALI", "CAL", "CALIPER", "HCAL", "CALD"),
    "SP": ("SP", "SPONT", "SPONTANEOUS"),
    "PEF": ("PEF", "PE", "PEFZ"),
}

DEPTH_TOKENS = {
    "DEPTH",
    "DEPT",
    "MD",
    "TVD",
    "TVDSS",
    "TIME",
    "DATE",
    "DATETIME",
}


def _empty_figure(message: str):
    fig, ax = plt.subplots(figsize=(4.8, 3.3), constrained_layout=True)
    fig.patch.set_facecolor("#FFFFFF")
    ax.axis("off")
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=11, color="#5C718A", wrap=True)
    return fig


def _normalize_name(value: Any) -> str:
    return str(value).strip().upper()


def _is_depth_like(column_name: str) -> bool:
    normalized = _normalize_name(column_name)
    if normalized in DEPTH_TOKENS:
        return True
    return any(token in normalized for token in ("DEPTH", "TVD", "DATETIME"))


def _find_matching_column(
    numeric_columns: list[str],
    normalized_lookup: dict[str, str],
    aliases: tuple[str, ...],
    used_columns: set[str],
) -> str | None:
    for alias in aliases:
        candidate = normalized_lookup.get(alias)
        if candidate is not None and candidate not in used_columns:
            return candidate

    alias_tokens = tuple(alias.upper() for alias in aliases)
    for column in numeric_columns:
        if column in used_columns:
            continue
        normalized = _normalize_name(column)
        if any(token in normalized for token in alias_tokens):
            return column
    return None


def _display_label(column_name: str) -> str:
    label = str(column_name).strip().upper().replace("_", " ")
    return label if len(label) <= 12 else f"{label[:9]}..."


def compute_log_availability(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df is None or getattr(df, "empty", True):
        return []

    numeric_columns = [
        str(column)
        for column in df.columns
        if pd.api.types.is_numeric_dtype(df[column])
    ]
    if not numeric_columns:
        return []

    normalized_lookup = {
        _normalize_name(column): column
        for column in numeric_columns
    }

    used_columns: set[str] = set()
    availability_items: list[dict[str, Any]] = []

    for label, aliases in STANDARD_LOG_ALIASES.items():
        matched_column = _find_matching_column(numeric_columns, normalized_lookup, aliases, used_columns)
        if matched_column is None:
            continue

        values = pd.to_numeric(df[matched_column], errors="coerce")
        availability = float(values.notna().mean() * 100.0)
        if availability <= 0:
            continue

        used_columns.add(matched_column)
        availability_items.append(
            {
                "label": label,
                "column": matched_column,
                "availability": availability,
                "is_standard": True,
            }
        )

    for column in numeric_columns:
        if column in used_columns or _is_depth_like(column):
            continue

        values = pd.to_numeric(df[column], errors="coerce")
        availability = float(values.notna().mean() * 100.0)
        if availability <= 0:
            continue

        availability_items.append(
            {
                "label": _display_label(column),
                "column": column,
                "availability": availability,
                "is_standard": False,
            }
        )

    return availability_items


def build_log_availability_radar_figure(df: pd.DataFrame, title: str = "Log Intelligence (Availability Radar)"):
    availability_items = compute_log_availability(df)
    if not availability_items:
        return _empty_figure("No valid log curves available for the radar chart.")

    labels = [item["label"] for item in availability_items]
    availability = [float(item["availability"]) for item in availability_items]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    closed_angles = angles + angles[:1]
    closed_values = availability + availability[:1]

    fig, ax = plt.subplots(
        figsize=(4.8, 3.3),
        subplot_kw={"projection": "polar"},
        constrained_layout=True,
    )
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(["25", "50", "75", "100"], fontsize=7, color="#7A8BA4")
    ax.set_rlabel_position(0)
    ax.grid(color="#DDE8F2", linewidth=0.8)
    ax.spines["polar"].set_color("#DDE8F2")
    ax.spines["polar"].set_linewidth(1.0)

    ax.plot(closed_angles, closed_values, color="#2F80FF", linewidth=2.0)
    ax.fill(closed_angles, closed_values, color="#2F80FF", alpha=0.18)
    ax.scatter(angles, availability, s=22, color="#2F80FF", edgecolors="#FFFFFF", linewidths=0.9, zorder=3)

    ax.set_xticks(angles)
    ax.set_xticklabels(
        [f"{label}\n{int(round(value))}%" for label, value in zip(labels, availability)],
        fontsize=8,
        fontweight="600",
        color="#274B72",
    )
    ax.tick_params(axis="x", pad=12)
    ax.set_title(title, fontsize=12, fontweight="600", color="#274B72", pad=18)
    return fig
