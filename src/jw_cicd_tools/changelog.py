from __future__ import annotations

import re
from dataclasses import dataclass

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
_H3_HEADING_RE = re.compile(r"^###\s+(.+)$")


class ChangelogError(ValueError):
    """Raised when CHANGELOG.md contains invalid syntax, an obsolete heading
    format, or is missing required version information."""


@dataclass(frozen=True)
class Changelog:
    base_version: str
    unreleased: dict[str, list[str]]


def parse_changelog(text: str) -> Changelog:
    """Parse changelog text into a Changelog dataclass.

    Validates that:
    - If present, `## [Unreleased]` must be the first `## [` heading.
    - Old-style `## [X.Y.Z] - Unreleased` headings raise a migration ChangelogError.
    - At least one dated heading `## [X.Y.Z] - YYYY-MM-DD` exists.
    - Subsections under `[Unreleased]` are in ALLOWED_SUBSECTIONS.
    - Any bullet under `[Unreleased]` must appear under a valid subsection.
    """
    lines = text.splitlines()
    in_unreleased = False
    first_h2_bracket_seen = False
    base_version: str | None = None
    current_subsection: str | None = None
    unreleased: dict[str, list[str]] = {}

    for line in lines:
        stripped = line.strip()

        # Check for any level-2 bracket heading: ## [...]
        if _H2_HEADING_RE.match(stripped):
            if _OLD_STYLE_UNRELEASED_RE.match(stripped):
                raise ChangelogError(
                    f"Found '{stripped}'. This heading style is no longer supported. "
                    "Rename it to '## [Unreleased]'; the version is now computed at release time."
                )

            if _UNRELEASED_HEADING_RE.match(stripped):
                if first_h2_bracket_seen:
                    raise ChangelogError(
                        "## [Unreleased] must be the first release heading in CHANGELOG.md"
                    )
                first_h2_bracket_seen = True
                in_unreleased = True
                current_subsection = None
                continue

            first_h2_bracket_seen = True
            in_unreleased = False
            current_subsection = None

            dated_match = _DATED_HEADING_RE.match(stripped)
            if dated_match and base_version is None:
                base_version = dated_match.group(1)
            continue

        if in_unreleased:
            h3_match = _H3_HEADING_RE.match(stripped)
            if h3_match:
                section_name = h3_match.group(1).strip()
                if section_name not in ALLOWED_SUBSECTIONS:
                    allowed_str = ", ".join(ALLOWED_SUBSECTIONS)
                    raise ChangelogError(
                        f"Unknown subsection '### {section_name}' under [Unreleased]. "
                        f"Allowed subsections are: {allowed_str}"
                    )
                current_subsection = section_name
                continue

            if stripped.startswith(("- ", "* ")):
                if current_subsection is None:
                    raise ChangelogError("entries must be under a ### subsection")
                unreleased.setdefault(current_subsection, []).append(stripped)
                continue

    if base_version is None:
        raise ChangelogError("No dated version heading found in CHANGELOG.md")

    return Changelog(base_version=base_version, unreleased=unreleased)


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
    """Rename `## [Unreleased]` to `## [<version>] - <date>` and insert a fresh
    empty `## [Unreleased]` heading above it. Everything else is preserved byte for byte.

    Raises ChangelogError if the date is not YYYY-MM-DD or [Unreleased] has no entries.
    """
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise ChangelogError("Release date must be in YYYY-MM-DD format")

    changelog = parse_changelog(text)
    if not has_entries(changelog):
        raise ChangelogError("No entries under [Unreleased] to stamp")

    match = re.search(
        r"^##\s*\\?\[unreleased\\?\][^\S\r\n]*", text, re.MULTILINE | re.IGNORECASE
    )
    if not match:
        raise ChangelogError("No ## [Unreleased] heading found in changelog")

    newline = "\r\n" if "\r\n" in text else "\n"
    replacement = f"## [Unreleased]{newline}{newline}## [{version}] - {date}"

    return text[:match.start()] + replacement + text[match.end():]
