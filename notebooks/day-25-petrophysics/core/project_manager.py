"""Project save/load stubs (extend)."""
from __future__ import annotations


def save_project(path: str, project: dict):
    # TODO: serialize real project data
    with open(path, "w", encoding="utf-8") as f:
        f.write("# PetroVision Project\n")
        f.write(str(project))


def load_project(path: str) -> dict:
    # TODO: parse real project data
    with open(path, "r", encoding="utf-8") as f:
        _ = f.read()
    return {"path": path}
