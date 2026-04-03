"""QC report helpers (stub)."""
from __future__ import annotations


def to_csv(rows):
    lines = ["check,status,count,details"]
    for row in rows:
        lines.append(",".join([
            str(row.get("check", "")),
            str(row.get("status", "")),
            str(row.get("count", "")),
            str(row.get("details", "")),
        ]))
    return "\n".join(lines)
