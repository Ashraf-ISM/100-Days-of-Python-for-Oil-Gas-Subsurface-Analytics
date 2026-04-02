"""
core/project_manager.py
=======================
Save and load PetroSight Pro projects as JSON files.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Tuple

from core.data_model import Project


def save_project(project: Project, filepath: str) -> Tuple[bool, str]:
    """Serialise project to JSON.  Returns (success, message)."""
    try:
        data = project.to_dict()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True, f"Project saved: {filepath}"
    except Exception as exc:
        return False, f"Save error: {exc}"


def load_project(filepath: str) -> Tuple[Project | None, str]:
    """Deserialise a JSON project file.  Returns (Project | None, message)."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        project = Project.from_dict(data)
        return project, f"Project loaded: {filepath} ({len(project.wells)} wells)"
    except Exception as exc:
        return None, f"Load error: {exc}"


def new_project(name: str = "New Project") -> Project:
    return Project(name=name)