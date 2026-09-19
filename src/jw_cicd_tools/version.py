import re
from datetime import datetime, timezone
from pathlib import Path

# Matches headings like "## [1.2.3] - 2026-09-05" or "## [1.2.3] - Unreleased"
_HEADING_RE = re.compile(r"^##\s*\[?v?(\d+\.\d+\.\d+)\]?\s*-\s*(.+?)\s*$", re.MULTILINE)


class ChangelogError(ValueError):
    """Raised when CHANGELOG.md's top entry doesn't match what's expected
    for the branch being built (see resolve_version)."""


def resolve_version(changelog_path: Path, branch: str) -> str:
    """Resolve a package/image version from CHANGELOG.md, appending a beta
    suffix with timestamp when not on the main branch.

    Convention: the top-most changelog entry's status field must read
    "Unreleased" for any non-main branch, and must carry a real release date
    on main. This prevents building a beta of a version that has already
    been released (the top entry is stale), and prevents merging to main
    with an unfinalized changelog entry.
    """
    version, status = _parse_latest_entry(changelog_path)
    is_unreleased = status.strip().lower() == "unreleased"

    if branch == "main":
        if is_unreleased:
            raise ChangelogError(
                f"CHANGELOG.md's top entry ({version}) is still marked "
                "'Unreleased' on main. Finalize it with a real release date "
                "before merging."
            )
        return version

    if not is_unreleased:
        raise ChangelogError(
            f"CHANGELOG.md's top entry ({version}) is already released "
            f"(dated '{status}'). Add a new '## [X.Y.Z] - Unreleased' entry "
            "for the current work before building a beta."
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{version}-beta.{timestamp}"


def _parse_latest_entry(changelog_path: Path) -> tuple[str, str]:
    text = changelog_path.read_text(encoding="utf-8")
    match = _HEADING_RE.search(text)
    if not match:
        raise ValueError(f"No version heading found in {changelog_path}")
    return match.group(1), match.group(2)
