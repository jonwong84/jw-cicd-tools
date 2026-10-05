from pathlib import Path

import pytest
from typer.testing import CliRunner

from jw_cicd_tools.changelog import (
    ChangelogError,
    has_entries,
    next_version,
    parse_changelog,
    stamp,
)
from jw_cicd_tools.main import app
from jw_cicd_tools.version import resolve_version

CHANGELOG_WITH_UNRELEASED_ENTRIES = """\
# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Breaking
- Significant breaking change

### Added
- New feature A

## [0.3.0] - 2026-10-01

### Added
- Old feature

## [0.2.0] - 2026-09-18

### Changed
- Old change
"""

CHANGELOG_WITH_EMPTY_UNRELEASED = """\
# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.3.0] - 2026-10-01

### Added
- Old feature
"""

CHANGELOG_WITHOUT_UNRELEASED = """\
# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2026-10-01

### Added
- Old feature
"""


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "CHANGELOG.md"
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Parsing Tests (Section 3.1 & Section 5)
# ---------------------------------------------------------------------------


def test_parse_entries_detected_with_hyphen_and_asterisk():
    text = """\
# Changelog

## [Unreleased]

### Added
- Hyphen item
* Asterisk item

## [1.0.0] - 2026-01-01
"""
    parsed = parse_changelog(text)
    assert parsed.base_version == "1.0.0"
    assert parsed.unreleased["Added"] == ["- Hyphen item", "* Asterisk item"]
    assert has_entries(parsed) is True


def test_parse_empty_subsection_yields_no_entries():
    text = """\
# Changelog

## [Unreleased]

### Added
### Fixed

## [1.0.0] - 2026-01-01
"""
    parsed = parse_changelog(text)
    assert has_entries(parsed) is False


def test_parse_unknown_subsection_raises():
    text = """\
# Changelog

## [Unreleased]

### Updated
- Some update

## [1.0.0] - 2026-01-01
"""
    with pytest.raises(
        ChangelogError,
        match=r"Unknown subsection '### Updated' under \[Unreleased\]",
    ):
        parse_changelog(text)


def test_parse_bullet_before_any_subsection_raises():
    text = """\
# Changelog

## [Unreleased]
- Rogue bullet before subsection

### Added
- Normal bullet

## [1.0.0] - 2026-01-01
"""
    with pytest.raises(
        ChangelogError, match="entries must be under a ### subsection"
    ):
        parse_changelog(text)


def test_parse_unreleased_not_first_raises():
    text = """\
# Changelog

## [1.0.0] - 2026-01-01

## [Unreleased]

### Added
- Late unreleased
"""
    with pytest.raises(
        ChangelogError,
        match=r"## \[Unreleased\] must be the first release heading",
    ):
        parse_changelog(text)


def test_parse_old_style_unreleased_raises_migration_text():
    text = """\
# Changelog

## [0.3.0] - Unreleased

### Added
- Old style work
"""
    with pytest.raises(
        ChangelogError,
        match=r"Found '## \[0.3.0\] - Unreleased'\. This heading style is no longer supported\. "
        r"Rename it to '## \[Unreleased\]'; the version is now computed at release time\.",
    ):
        parse_changelog(text)


def test_parse_missing_unreleased_means_no_entries():
    text = """\
# Changelog

## [1.0.0] - 2026-01-01

### Added
- Existing work
"""
    parsed = parse_changelog(text)
    assert parsed.base_version == "1.0.0"
    assert has_entries(parsed) is False


def test_parse_no_dated_heading_raises():
    text = """\
# Changelog

## [Unreleased]

### Added
- New stuff
"""
    with pytest.raises(
        ChangelogError, match="No dated version heading found in CHANGELOG.md"
    ):
        parse_changelog(text)


def test_parse_subsection_names_validated_only_under_unreleased():
    text = """\
# Changelog

## [Unreleased]

### Added
- New valid item

## [1.0.0] - 2026-01-01

### Updated
- Legacy subsection name in dated entry
"""
    parsed = parse_changelog(text)
    assert parsed.base_version == "1.0.0"
    assert parsed.unreleased["Added"] == ["- New valid item"]


# ---------------------------------------------------------------------------
# Bump Rules Tests (Section 3.1 & Section 5)
# ---------------------------------------------------------------------------


def test_bump_added_or_changed_or_deprecated_or_removed_gives_minor():
    assert next_version("1.0.0", {"Added": ["- feat"]}) == "1.1.0"
    assert next_version("1.0.0", {"Changed": ["- feat"]}) == "1.1.0"
    assert next_version("1.0.0", {"Deprecated": ["- feat"]}) == "1.1.0"
    assert next_version("1.0.0", {"Removed": ["- feat"]}) == "1.1.0"


def test_bump_fixed_alone_gives_patch():
    assert next_version("1.0.0", {"Fixed": ["- fix"]}) == "1.0.1"


def test_bump_fixed_plus_added_gives_minor():
    assert (
        next_version("1.0.0", {"Fixed": ["- fix"], "Added": ["- feat"]})
        == "1.1.0"
    )


def test_bump_security_gives_patch():
    assert next_version("1.0.0", {"Security": ["- sec"]}) == "1.0.1"


def test_bump_breaking_gives_major_at_1x_and_minor_at_0x():
    assert next_version("1.2.3", {"Breaking": ["- break"]}) == "2.0.0"
    assert next_version("0.3.0", {"Breaking": ["- break"]}) == "0.4.0"
    assert next_version("0.1.2", {"Breaking": ["- break"]}) == "0.2.0"


# ---------------------------------------------------------------------------
# resolve_version Tests (Section 3.2 & Section 5)
# ---------------------------------------------------------------------------


def test_resolve_version_main_with_entries(tmp_path: Path):
    # Row 1: main, [Unreleased] has entries -> clean computed next version
    changelog = _write(tmp_path, CHANGELOG_WITH_UNRELEASED_ENTRIES)
    # Base is 0.3.0, with Breaking + Added -> bump is minor on 0.x -> 0.4.0
    assert resolve_version(changelog, branch="main") == "0.4.0"


def test_resolve_version_main_without_entries(tmp_path: Path):
    # Row 2: main, [Unreleased] has no entries -> empty string
    changelog_empty = _write(tmp_path, CHANGELOG_WITH_EMPTY_UNRELEASED)
    assert resolve_version(changelog_empty, branch="main") == ""

    changelog_none = _write(tmp_path, CHANGELOG_WITHOUT_UNRELEASED)
    assert resolve_version(changelog_none, branch="main") == ""


def test_resolve_version_feature_branch_with_entries(tmp_path: Path):
    # Row 3: other branch, [Unreleased] has entries -> X.Y.Z-beta.<ts>
    changelog = _write(tmp_path, CHANGELOG_WITH_UNRELEASED_ENTRIES)
    result = resolve_version(changelog, branch="feature/some-work")

    assert result.startswith("0.4.0-beta.")
    suffix = result.split("beta.")[1]
    assert len(suffix) == 14
    assert suffix.isdigit()


def test_resolve_version_feature_branch_without_entries(tmp_path: Path):
    # Row 4: other branch, [Unreleased] has no entries -> <base patch+1>-beta.<ts>
    changelog = _write(tmp_path, CHANGELOG_WITH_EMPTY_UNRELEASED)
    result = resolve_version(changelog, branch="feature/some-work")

    # Base is 0.3.0 -> patch+1 is 0.3.1
    assert result.startswith("0.3.1-beta.")
    suffix = result.split("beta.")[1]
    assert len(suffix) == 14
    assert suffix.isdigit()


def test_resolve_version_raises_if_no_version_heading(tmp_path: Path):
    path = tmp_path / "CHANGELOG.md"
    path.write_text("# Changelog\n\nNo versions yet.\n", encoding="utf-8")

    with pytest.raises(
        ChangelogError, match="No dated version heading found in CHANGELOG.md"
    ):
        resolve_version(path, branch="main")


# ---------------------------------------------------------------------------
# Stamp Tests (Section 3.1, 3.3 & Section 5)
# ---------------------------------------------------------------------------


def test_stamp_renames_heading_inserts_fresh_unreleased_and_preserves_content():
    content = (
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "### Breaking\n"
        "- Big change\n\n"
        "## [0.3.0] - 2026-10-01\n"
    )
    result = stamp(content, version="0.4.0", date="2026-10-05")
    expected = (
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "## [0.4.0] - 2026-10-05\n\n"
        "### Breaking\n"
        "- Big change\n\n"
        "## [0.3.0] - 2026-10-01\n"
    )
    assert result == expected


def test_stamp_raises_with_no_entries():
    content = (
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "## [0.3.0] - 2026-10-01\n"
    )
    with pytest.raises(
        ChangelogError, match=r"No entries under \[Unreleased\] to stamp"
    ):
        stamp(content, version="0.4.0", date="2026-10-05")


# ---------------------------------------------------------------------------
# CLI Tests (Section 3.3 & Section 5)
# ---------------------------------------------------------------------------


def test_cli_changelog_error_exits_1_without_traceback(tmp_path: Path):
    runner = CliRunner()
    bad_changelog = _write(
        tmp_path, "# Changelog\n\n## [0.3.0] - Unreleased\n\n### Added\n- Work\n"
    )

    # Test version resolve command
    result = runner.invoke(
        app,
        [
            "version",
            "resolve",
            "--changelog",
            str(bad_changelog),
            "--branch",
            "main",
        ],
    )
    assert result.exit_code == 1
    assert "Traceback" not in (result.output + (result.stderr or ""))
    assert "Found '## [0.3.0] - Unreleased'" in (
        result.output + (result.stderr or "")
    )

    # Test release stamp command
    result_stamp = runner.invoke(
        app,
        [
            "release",
            "stamp",
            "--changelog",
            str(bad_changelog),
        ],
    )
    assert result_stamp.exit_code == 1
    assert "Traceback" not in (
        result_stamp.output + (result_stamp.stderr or "")
    )
    assert "Found '## [0.3.0] - Unreleased'" in (
        result_stamp.output + (result_stamp.stderr or "")
    )


def test_cli_release_stamp_success_and_idempotence(tmp_path: Path):
    runner = CliRunner()
    changelog = _write(tmp_path, CHANGELOG_WITH_UNRELEASED_ENTRIES)

    # First stamp: computes 0.4.0 and rewrites file
    result1 = runner.invoke(
        app,
        [
            "release",
            "stamp",
            "--changelog",
            str(changelog),
            "--date",
            "2026-10-05",
        ],
    )
    assert result1.exit_code == 0
    assert result1.output.strip() == "0.4.0"

    content_after_first = changelog.read_text(encoding="utf-8")
    assert "## [0.4.0] - 2026-10-05" in content_after_first
    assert "## [Unreleased]" in content_after_first

    # Second stamp on output: no unreleased entries -> prints blank line, leaves file unchanged, exit 0
    result2 = runner.invoke(
        app,
        [
            "release",
            "stamp",
            "--changelog",
            str(changelog),
            "--date",
            "2026-10-05",
        ],
    )
    assert result2.exit_code == 0
    assert result2.output.strip() == ""
    assert changelog.read_text(encoding="utf-8") == content_after_first
