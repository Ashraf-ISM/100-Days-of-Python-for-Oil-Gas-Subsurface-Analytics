"""QC engine: run checks and return a report structure."""
from __future__ import annotations

from typing import Any, Dict, List

from qc.qc_rules import DEFAULT_RULES


def run_qc(well: Any, curve_name: str | None = None, rules: dict | None = None) -> List[Dict[str, Any]]:
    """Return a list of QC rows with status and counts.

    This is a placeholder; plug in real checks later.
    """
    _ = (well, curve_name)
    rules = rules or DEFAULT_RULES
    return [
        {"check": "missing_values", "status": "PASS", "count": 0, "details": f"max_pct={rules['missing_values']['max_pct']}"},
        {"check": "spike_detection", "status": "PASS", "count": 0, "details": f"zscore={rules['spike_detection']['zscore']}"},
        {"check": "depth_gaps", "status": "PASS", "count": 0, "details": f"max_gap={rules['depth_gaps']['max_gap']}"},
    ]
