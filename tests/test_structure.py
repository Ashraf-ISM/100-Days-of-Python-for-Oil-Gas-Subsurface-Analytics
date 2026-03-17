from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_expected_directories_exist() -> None:
    expected = [
        "data/raw",
        "notebooks",
        "outputs",
        "src",
        "docs",
    ]
    for rel in expected:
        assert (ROOT / rel).exists(), f"Missing {rel}"


def test_notebooks_present() -> None:
    notebook_dir = ROOT / "notebooks"
    assert any(notebook_dir.rglob("*.ipynb")), "No notebooks found"
