"""PetroARX project persistence engine — .ash archive format.

File layout inside the ZIP archive
────────────────────────────────────
  manifest.json          Human-readable project metadata + well list 
  state.pkl              Pickled AppState (all UI / panel parameters)
  wells/<name>.pkl       One pickled Well object per well
                         (preserves full DataFrame including computed curves)

The extension is .ash  ("Ashraf Session / Hydrocarbon").  Archives are produced
by Python's zipfile module so they can be inspected with any ZIP utility even
though the individual entries are binary pickles.
"""
from __future__ import annotations

import io
import json
import pickle
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from core.app_state import AppState

# ── Format version written to every manifest ──────────────────────────────────
FORMAT_VERSION = "1.0" 


# ─────────────────────────────────────────────────────────────────────────────
#  In-memory project representation
# ─────────────────────────────────────────────────────────────────────────────

class ProjectData:
    """Lightweight container for project metadata (not the heavy well data)."""

    def __init__(self, name: str = "Untitled", path: str | None = None) -> None:
        self.name: str = name
        self.path: str | None = path
        self.created: str = datetime.now().isoformat()
        self.modified: str = datetime.now().isoformat()
        self.metadata: Dict[str, Any] = {
            "description": "",
            "field": "",
            "basin": "",
            "region": "",
            "country": "",
            "operator": "",
        }
        # Names of wells encoded in the archive (populated on load)
        self.well_names: list[str] = []

    # ── Serialisation helpers ─────────────────────────────────────────────────

    def to_manifest(self) -> dict:
        """Return a JSON-serialisable dict for the manifest entry."""
        return {
            "format_version": FORMAT_VERSION,
            "name": self.name,
            "created": self.created,
            "modified": self.modified,
            "metadata": self.metadata,
            "wells": self.well_names,
        }

    @classmethod
    def from_manifest(cls, data: dict, path: str) -> "ProjectData":
        project = cls(name=data.get("name", "Untitled"), path=path)
        project.created = data.get("created", project.created)
        project.modified = data.get("modified", project.modified)
        project.metadata = data.get("metadata", project.metadata)
        project.well_names = data.get("wells", [])
        return project


# ─────────────────────────────────────────────────────────────────────────────
#  Save
# ─────────────────────────────────────────────────────────────────────────────

def save_ash(
    path: str,
    project: ProjectData,
    wells: Dict[str, Any],
    app_state: AppState,
) -> bool:
    """Serialise project to an .ash ZIP archive.

    Args:
        path:       Destination file path (will be created / overwritten).
        project:    ProjectData with name / metadata.
        wells:      Dict of {well_name: Well} objects from DataService._wells.
        app_state:  AppState snapshot of all UI parameters.

    Returns:
        True on success, False on error.
    """
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        # Update project bookkeeping
        project.path = path
        project.modified = datetime.now().isoformat()
        project.well_names = list(wells.keys())

        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:

            # 1. manifest.json
            manifest_bytes = json.dumps(
                project.to_manifest(), indent=2, ensure_ascii=False
            ).encode("utf-8")
            zf.writestr("manifest.json", manifest_bytes)

            # 2. state.pkl  — AppState
            state_buf = io.BytesIO()
            pickle.dump(app_state, state_buf, protocol=pickle.HIGHEST_PROTOCOL)
            zf.writestr("state.pkl", state_buf.getvalue())

            # 3. wells/<name>.pkl  — one file per well
            for well_name, well in wells.items():
                safe_name = _safe_filename(well_name)
                well_buf = io.BytesIO()
                pickle.dump(well, well_buf, protocol=pickle.HIGHEST_PROTOCOL)
                zf.writestr(f"wells/{safe_name}.pkl", well_buf.getvalue())

        return True

    except Exception as exc:
        print(f"[ProjectManager] save_ash error: {exc}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  Load
# ─────────────────────────────────────────────────────────────────────────────

def load_ash(
    path: str,
) -> Tuple[Optional[ProjectData], Dict[str, Any], AppState]:
    """Deserialise an .ash archive.

    Returns:
        (ProjectData, wells_dict, AppState)
        On failure: (None, {}, AppState.default())
    """
    try:
        with zipfile.ZipFile(path, "r") as zf:
            namelist = zf.namelist()

            # ── manifest ──────────────────────────────────────────────────────
            if "manifest.json" not in namelist:
                print("[ProjectManager] load_ash: manifest.json missing")
                return None, {}, AppState.default()

            manifest_data = json.loads(zf.read("manifest.json").decode("utf-8"))
            project = ProjectData.from_manifest(manifest_data, path)

            # ── app state ─────────────────────────────────────────────────────
            app_state: AppState
            if "state.pkl" in namelist:
                raw = zf.read("state.pkl")
                loaded = pickle.loads(raw)  # noqa: S301
                # Upgrade: if the file stored a plain dict, wrap in AppState
                if isinstance(loaded, AppState):
                    app_state = loaded
                elif isinstance(loaded, dict):
                    app_state = AppState(**{
                        k: v for k, v in loaded.items()
                        if k in AppState.__dataclass_fields__
                    })
                else:
                    app_state = AppState.default()
            else:
                app_state = AppState.default()

            # ── wells ────────────────────────────────────────────────────────
            wells: Dict[str, Any] = {}
            well_entries = [n for n in namelist if n.startswith("wells/") and n.endswith(".pkl")]
            for entry in well_entries:
                raw = zf.read(entry)
                well_obj = pickle.loads(raw)  # noqa: S301
                well_name = getattr(well_obj, "name", Path(entry).stem)
                wells[well_name] = well_obj

        return project, wells, app_state

    except Exception as exc:
        print(f"[ProjectManager] load_ash error: {exc}")
        return None, {}, AppState.default()


# ─────────────────────────────────────────────────────────────────────────────
#  Recent projects registry 
# ─────────────────────────────────────────────────────────────────────────────

_CONFIG_DIR = Path.home() / ".petroarx"
_RECENT_FILE = _CONFIG_DIR / "recent_projects.json"


def get_recent_projects(max_count: int = 10) -> list[str]:
    """Return list of recently-used .ash project paths (existing files only)."""
    if not _RECENT_FILE.exists():
        return []
    try:
        data = json.loads(_RECENT_FILE.read_text(encoding="utf-8"))
        projects = [p for p in data.get("projects", []) if Path(p).exists()]
        return projects[:max_count]
    except Exception:
        return []


def add_recent_project(path: str) -> None:
    """Prepend *path* to the recent-projects registry (keeps last 15 entries)."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        projects: list[str] = []
        if _RECENT_FILE.exists():
            data = json.loads(_RECENT_FILE.read_text(encoding="utf-8"))
            projects = data.get("projects", [])

        if path in projects:
            projects.remove(path)
        projects.insert(0, path)
        projects = projects[:15]

        _RECENT_FILE.write_text(
            json.dumps({"projects": projects}, indent=2), encoding="utf-8"
        )
    except Exception as exc:
        print(f"[ProjectManager] add_recent_project error: {exc}")


def remove_recent_project(path: str) -> None:
    """Remove a stale path from the recent-projects registry."""
    if not _RECENT_FILE.exists():
        return
    try:
        data = json.loads(_RECENT_FILE.read_text(encoding="utf-8"))
        projects = [p for p in data.get("projects", []) if p != path]
        _RECENT_FILE.write_text(
            json.dumps({"projects": projects}, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe_filename(name: str) -> str:
    """Convert an arbitrary well name to a safe ZIP entry filename."""
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
    return safe or "well"
