from pathlib import Path

import pytest

from jw_cicd_tools.version import ChangelogError, resolve_version

CHANGELOG_WITH_UNRELEASED_TOP = """\
# Changelog

All notable changes to this project will be documented in this file.

## [1.1.2] - Unreleased

### Added
- Work in progress

## [1.1.1] - 2026-06-18

### Updated
- Minor update to Readme

## [1.0.2] - 2026-06-03

### Updated
- CircleCI publishing corrected to generate datetime tag instead of hash
"""

CHANGELOG_ALREADY_RELEASED_TOP = """\
# Changelog

All notable changes to this project will be documented in this file.

## [1.1.1] - 2026-06-18

### Updated
- Minor update to Readme

## [1.0.2] - 2026-06-03

### Updated
- CircleCI publishing corrected to generate datetime tag instead of hash
"""


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "CHANGELOG.md"
    path.write_text(content, encoding="utf-8")
    return path


def test_resolve_version_on_main_returns_base_version_when_finalized(tmp_path: Path):
    changelog = _write(tmp_path, CHANGELOG_ALREADY_RELEASED_TOP)
    assert resolve_version(changelog, branch="main") == "1.1.1"


def test_resolve_version_on_main_raises_if_top_entry_still_unreleased(tmp_path: Path):
    changelog = _write(tmp_path, CHANGELOG_WITH_UNRELEASED_TOP)
    with pytest.raises(ChangelogError, match="still marked 'Unreleased' on main"):
        resolve_version(changelog, branch="main")


def test_resolve_version_on_feature_branch_appends_beta_suffix_when_unreleased(tmp_path: Path):
    changelog = _write(tmp_path, CHANGELOG_WITH_UNRELEASED_TOP)
    result = resolve_version(changelog, branch="feature/some-work")

    assert result.startswith("1.1.2-beta.")
    suffix = result.split("beta.")[1]
    assert len(suffix) == 14
    assert suffix.isdigit()


def test_resolve_version_on_feature_branch_raises_if_top_entry_already_released(tmp_path: Path):
    changelog = _write(tmp_path, CHANGELOG_ALREADY_RELEASED_TOP)
    with pytest.raises(ChangelogError, match="already released"):
        resolve_version(changelog, branch="feature/some-work")


def test_resolve_version_raises_if_no_version_heading(tmp_path: Path):
    path = tmp_path / "CHANGELOG.md"
    path.write_text("# Changelog\n\nNo versions yet.\n", encoding="utf-8")

    with pytest.raises(ValueError, match="No version heading found"):
        resolve_version(path, branch="main")
