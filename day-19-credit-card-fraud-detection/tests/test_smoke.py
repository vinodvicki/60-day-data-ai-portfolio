"""Day 19 smoke tests — README embeds, referenced files, no secrets.

These tests read only the committed tree (README, processed tables,
charts, screenshot). They never touch the raw file or train a model.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Files the day README references (charts + dashboard preview).
README_REFERENCED = [
    "outputs/charts/01_class_imbalance.png",
    "outputs/charts/02_pr_curves.png",
    "outputs/charts/03_threshold_tradeoff.png",
    "outputs/charts/04_cost_curve.png",
    "screenshots/dashboard.png",
]


def test_readme_embeds_all_charts() -> None:
    """The README Visuals section embeds all 4 charts as images."""
    readme = (ROOT / "README.md").read_text()
    for path in README_REFERENCED[:4]:
        assert re.search(rf"!\[.*\]\({re.escape(path)}\)", readme), path


def test_readme_references_dashboard_preview() -> None:
    """The README links the dashboard screenshot."""
    readme = (ROOT / "README.md").read_text()
    assert "screenshots/dashboard.png" in readme


def test_all_referenced_files_exist() -> None:
    """Every file the README references exists on disk."""
    for path in README_REFERENCED:
        assert (ROOT / path).exists(), f"missing {path}"
        assert (ROOT / path).stat().st_size > 0, f"empty {path}"


def test_charts_are_real_pngs() -> None:
    """Chart files start with the PNG magic bytes."""
    for path in README_REFERENCED:
        with (ROOT / path).open("rb") as handle:
            assert handle.read(8) == b"\x89PNG\r\n\x1a\n", path


def test_no_secrets_in_tree() -> None:
    """No credential-looking material in the committed text files."""
    secret_patterns = [
        re.compile(r"api[_-]?key\s*=\s*['\"][^'\"]{8,}['\"]", re.IGNORECASE),
        re.compile(r"password\s*=\s*['\"][^'\"]{4,}['\"]", re.IGNORECASE),
        re.compile(r"sk-[A-Za-z0-9]{16,}"),
    ]
    for path in ROOT.rglob("*"):
        if path.is_dir() or path.suffix not in {
            ".py",
            ".md",
            ".txt",
            ".toml",
            ".json",
            ".yaml",
            ".ipynb",
        }:
            continue
        if ".venv" in path.parts or "__pycache__" in path.parts:
            continue
        text = path.read_text(errors="ignore")
        for pattern in secret_patterns:
            assert not pattern.search(text), f"{path}: {pattern.pattern}"


def test_gitignore_excludes_raw_cache() -> None:
    """The 144 MB raw file is git-ignored and data/ itself is not."""
    gitignore = (ROOT / ".gitignore").read_text()
    assert "data/raw/creditcard.csv" in gitignore
    assert "data/" not in [
        line.strip() for line in gitignore.splitlines() if line.strip()
    ]


def test_data_readme_and_insights_exist() -> None:
    """Provenance and findings docs exist and are non-empty."""
    for path in ("data/README.md", "outputs/insights_summary.md"):
        text = (ROOT / path).read_text().strip()
        assert len(text) > 200, path
