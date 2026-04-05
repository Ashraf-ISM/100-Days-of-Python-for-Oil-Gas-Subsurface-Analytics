"""Project save/load with JSON serialization."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
import pandas as pd
from datetime import datetime


class ProjectData:
    """In-memory project representation."""
    def __init__(self, name: str = "Untitled", path: str | None = None):
        self.name = name
        self.path = path
        self.created = datetime.now().isoformat()
        self.modified = datetime.now().isoformat()
        self.wells: Dict[str, Dict[str, Any]] = {}
        self.metadata: Dict[str, Any] = {
            "description": "",
            "field": "",
            "basin": "",
            "region": "",
            "country": ""
        }
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "created": self.created,
            "modified": self.modified,
            "metadata": self.metadata,
            "wells": self.wells
        }


def save_project(path: str, project_data: ProjectData | dict) -> bool:
    """Save project to JSON file with well data.
    
    Args:
        path: File path to save project
        project_data: ProjectData object or dict with project info
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if isinstance(project_data, ProjectData):
            data = project_data.to_dict()
        else:
            data = project_data
        
        data["modified"] = datetime.now().isoformat()
        
        # Create parent directory if it doesn't exist
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        
        return True
    except Exception as e:
        print(f"Error saving project: {e}")
        return False


def load_project(path: str) -> ProjectData | None:
    """Load project from JSON file.
    
    Args:
        path: File path to load project from
    
    Returns:
        ProjectData object or None if failed
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        project = ProjectData(
            name=data.get("name", "Untitled"),
            path=path
        )
        project.created = data.get("created", project.created)
        project.modified = data.get("modified", project.modified)
        project.metadata = data.get("metadata", {})
        project.wells = data.get("wells", {})
        
        return project
    except Exception as e:
        print(f"Error loading project: {e}")
        return None


def get_recent_projects(max_count: int = 5) -> list[str]:
    """Get list of recently used projects from config.
    
    Args:
        max_count: Maximum number of recent projects to return
    
    Returns:
        List of project file paths
    """
    config_file = Path.home() / ".petrovision" / "recent_projects.json"
    if not config_file.exists():
        return []
    
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        projects = data.get("projects", [])
        # Filter to existing files only
        projects = [p for p in projects if Path(p).exists()]
        return projects[:max_count]
    except Exception:
        return []


def add_recent_project(path: str) -> None:
    """Add project to recent projects list.
    
    Args:
        path: Project file path
    """
    config_dir = Path.home() / ".petrovision"
    config_file = config_dir / "recent_projects.json"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        projects = []
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                projects = data.get("projects", [])
        
        # Remove if already exists and add to front
        if path in projects:
            projects.remove(path)
        projects.insert(0, path)
        
        # Keep only last 10 projects
        projects = projects[:10]
        
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump({"projects": projects}, f, indent=2)
    except Exception as e:
        print(f"Error updating recent projects: {e}")
