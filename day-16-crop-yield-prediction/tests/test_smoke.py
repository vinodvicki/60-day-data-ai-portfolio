"""Scaffold smoke test — replaced by the coder with real tests."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_exists() -> None:
    assert (ROOT / "README.md").read_text().strip() != ""


def test_data_readme_exists() -> None:
    assert (ROOT / "data" / "README.md").exists()
