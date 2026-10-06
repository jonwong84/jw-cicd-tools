from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

ALLOWED_SUBSECTIONS = (
    "Added",
    "Changed",
    "Deprecated",
    "Removed",
    "Fixed",
    "Security",
    "Breaking",
)

MAJOR_SUBSECTIONS = {"Breaking"}
MINOR_SUBSECTIONS = {"Added", "Changed", "Deprecated", "Removed"}
PATCH_SUBSECTIONS = {"Fixed", "Security"}

_OLD_STYLE_UNRELEASED_RE = re.compile(
    r"^##\s*(?:\\?\[)?v?(\d+\.\d+\.\d+)(?:\\?\])?\s*-\s*unreleased\s*$",
    re.IGNORECASE,
)
_UNRELEASED_HEADING_RE = re.compile(r"^##\s*\\?\[unreleased\\?\]\s*$", re.IGNORECASE)
_DATED_HEADING_RE = re.compile(
    r"^##\s*(?:\\?\[)?v?(\d+\.\d+\.\d+)(?:\\?\])?\s*-\s*(\d{4}-\d{2}-\d{2})\s*$"
)
_H2_HEADING_RE = re.compile(r"^##\s*\\?\[")
_H3_HEADING_RE = re.compile(r"^###\s+(\S.*)$")


class ChangelogError(ValueError):
    """Raised when CHANGELOG.md contains invalid syntax, an obsolete heading
    format, or is missing required version information."""


@dataclass(frozen=True)
class Changelog:
    base_version: str
    unreleased: dict[str, list[str]]


@dataclass
class _ParseState:
    in_unreleased: bool = False
    first_h2_seen: bool = False
    base_version: str | None = None
    current_subsection: str | None = None
    unreleased: dict[str, list[str]] = field(default_factory=dict)


def _handle_h2(stripped: str, state: _ParseState) -> None:
    """Update parsing state for a release heading with whitespace stripped.

    Reset the current subsection, enter or leave [Unreleased], and record
    the first dated version. Raise ChangelogError for an obsolete versioned
    Unreleased heading or an [Unreleased] heading after another release heading.
    """
    if _OLD_STYLE_UNRELEASED_RE.match(stripped):
        raise ChangelogError(
            f"Found '{stripped}'. This heading style is no longer supported. "
            "Rename it to '## [Unreleased]'; the version is now computed at release time."
        )

    if _UNRELEASED_HEADING_RE.match(stripped):
        if state.first_h2_seen:
            raise ChangelogError(
                "## [Unreleased] must be the first release heading in CHANGELOG.md"
            )
        state.first_h2_seen = True
        state.in_unreleased = True
        state.current_subsection = None
        return

    state.first_h2_seen = True
    state.in_unreleased = False
    state.current_subsection = None

    dated_match = _DATED_HEADING_RE.match(stripped)
    if dated_match and state.base_version is None:
        state.base_version = dated_match.group(1)


def _handle_unreleased_line(stripped: str, state: _ParseState) -> None:
    """Select a subsection or append a stripped '- ' or '* ' bullet to state.

    Raise ChangelogError for an unknown subsection or a bullet before any
    subsection. Ignore other lines.
    """
    h3_match = _H3_HEADING_RE.match(stripped)
    if h3_match:
        section_name = h3_match.group(1).strip()
        if section_name not in ALLOWED_SUBSECTIONS:
            allowed_str = ", ".join(ALLOWED_SUBSECTIONS)
            raise ChangelogError(
                f"Unknown subsection '### {section_name}' under [Unreleased]. "
                f"Allowed subsections are: {allowed_str}"
            )
        state.current_subsection = section_name
        return

    if stripped.startswith(("- ", "* ")):
        if state.current_subsection is None:
            raise ChangelogError("entries must be under a ### subsection")
        state.unreleased.setdefault(state.current_subsection, []).append(stripped)


def parse_changelog(text: str) -> Changelog:
    """Parse changelog text into a Changelog dataclass.

    Return the first dated heading's version and unreleased '- ' or '* '
    bullet lines, stripped of surrounding whitespace and grouped by subsection.
    Missing [Unreleased] or subsections without bullets contribute no entries.
    Heading brackets may be backslash-escaped; dates are checked for format,
    not calendar validity.

    Raise ChangelogError if any of these requirements are violated:
    - If present, `## [Unreleased]` must be the first `## [` heading.
    - Old-style `## [X.Y.Z] - Unreleased` headings raise a migration ChangelogError.
    - At least one dated heading `## [X.Y.Z] - YYYY-MM-DD` exists.
    - Subsections under `[Unreleased]` are in ALLOWED_SUBSECTIONS.
    - Any '- ' or '* ' bullet under `[Unreleased]` must be under a valid subsection.
    """
    state = _ParseState()

    for line in text.splitlines():
        stripped = line.strip()
        if _H2_HEADING_RE.match(stripped):
            _handle_h2(stripped, state)
        elif state.in_unreleased:
            _handle_unreleased_line(stripped, state)

    if state.base_version is None:
        raise ChangelogError("No dated version heading found in CHANGELOG.md")

    return Changelog(base_version=state.base_version, unreleased=state.unreleased)


def has_entries(changelog: Changelog) -> bool:
    """Return True if any unreleased subsection contains at least one bullet entry."""
    return any(bool(entries) for entries in changelog.unreleased.values())


def next_version(base: str, unreleased: dict[str, list[str]]) -> str:
    """Compute the next semantic version based on unreleased entry types.

    Rules:
    - Breaking gives major (or minor if base major is 0).
    - Added, Changed, Deprecated, Removed give minor.
    - Fixed, Security give patch.
    - Highest bump rule wins.

    Only nonempty recognized subsections count; lower version components
    reset to zero after a major or minor bump. Raise ChangelogError if no
    recognized subsection has entries or base is not three dot-separated
    integers.
    """
    has_breaking = any(bool(unreleased.get(k)) for k in MAJOR_SUBSECTIONS)
    has_minor = any(bool(unreleased.get(k)) for k in MINOR_SUBSECTIONS)
    has_patch = any(bool(unreleased.get(k)) for k in PATCH_SUBSECTIONS)

    if not (has_breaking or has_minor or has_patch):
        raise ChangelogError("No entries under [Unreleased] to compute next version")

    try:
        parts = [int(p) for p in base.split(".")]
        if len(parts) != 3:
            raise ValueError
        major, minor, patch = parts
    except ValueError as err:
        raise ChangelogError(f"Invalid base version '{base}'") from err

    if has_breaking:
        if major == 0:
            return f"0.{minor + 1}.0"
        return f"{major + 1}.0.0"

    if has_minor:
        return f"{major}.{minor + 1}.0"

    return f"{major}.{minor}.{patch + 1}"


def stamp(text: str, version: str, date: str) -> str:
    """Return text with `## [Unreleased]` renamed to `## [<version>] - <date>`
    and a fresh empty `## [Unreleased]` heading inserted above it.

    Insert version verbatim without validating it. Preserve text outside the
    replaced heading and its trailing whitespace. Inserted line endings use
    CRLF if any CRLF occurs in text, otherwise LF.

    Raise ChangelogError for an invalid calendar date or a date not formatted
    as YYYY-MM-DD, invalid changelog content, no unreleased entries, or no
    replaceable [Unreleased] heading starting at the beginning of a line.
    """
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise ChangelogError("Release date must be in YYYY-MM-DD format")
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError as error:
        raise ChangelogError("Release date must be a valid YYYY-MM-DD date") from error

    changelog = parse_changelog(text)
    if not has_entries(changelog):
        raise ChangelogError("No entries under [Unreleased] to stamp")

    match = re.search(
        r"^##[^\S\r\n]*\\?\[unreleased\\?\][^\S\r\n]*", text, re.MULTILINE | re.IGNORECASE
    )
    if not match:
        raise ChangelogError("No ## [Unreleased] heading found in changelog")

    newline = "\r\n" if "\r\n" in text else "\n"
    replacement = f"## [Unreleased]{newline}{newline}## [{version}] - {date}"

    return text[:match.start()] + replacement + text[match.end():]
