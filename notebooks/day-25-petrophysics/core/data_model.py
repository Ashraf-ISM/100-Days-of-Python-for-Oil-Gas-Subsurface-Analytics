"""Simple data models (extend as needed)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Well:
    name: str
    header: Dict[str, Any] = field(default_factory=dict)
    log_info: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    data: Any | None = None  # pandas DataFrame or dict
