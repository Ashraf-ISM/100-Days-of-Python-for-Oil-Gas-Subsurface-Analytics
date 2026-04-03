"""QC report helpers (export to CSV, summary)."""
from __future__ import annotations

from typing import Iterable


def to_csv(rows: Iterable[dict]) -> str:
    lines = ["check,status,count,details"]
    for row in rows:
        lines.append(",".join([
            str(row.get("check", "")),
            str(row.get("status", "")),
            str(row.get("count", "")),
            str(row.get("details", "")),
        ]))
    return "\n".join(lines)
