from pathlib import Path

import pytest

from jw_cicd_tools.version import resolve_version

SAMPLE_CHANGELOG = """\
# Changelog

All notable changes to this project will be documented in this file.

## [1.1.1] - 2026-06-18

### Updated
- Minor update to Readme

## [1.0.2] - 2026-06-03

### Updated
- CircleCI publishing corrected to generate datetime tag instead of hash

## [1.0.0] - 2026-06-02

### Added
- Initial release
"""


@pytest.fixture
def changelog(tmp_path: Path) -> Path:
    path = tmp_path / "CHANGELOG.md"
    path.write_text(SAMPLE_CHANGELOG, encoding="utf-8")
    return path


def test_resolve_version_on_main_returns_base_version(changelog: Path):
    assert resolve_version(changelog, branch="main") == "1.1.1"


def test_resolve_version_on_feature_branch_appends_beta_suffix(changelog: Path):
    result = resolve_version(changelog, branch="feature/some-work")

    assert result.startswith("1.1.1-beta.")
    # timestamp suffix should be 14 digits: YYYYMMDDHHMMSS
    suffix = result.split("beta.")[1]
    assert len(suffix) == 14
    assert suffix.isdigit()


def test_resolve_version_raises_if_no_version_heading(tmp_path: Path):
    path = tmp_path / "CHANGELOG.md"
    path.write_text("# Changelog\n\nNo versions yet.\n", encoding="utf-8")

    with pytest.raises(ValueError, match="No version heading found"):
        resolve_version(path, branch="main")
