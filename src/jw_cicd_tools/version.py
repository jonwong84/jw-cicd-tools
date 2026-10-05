from datetime import datetime, timezone
from pathlib import Path

from jw_cicd_tools.changelog import (
    ChangelogError,
    has_entries,
    next_version,
    parse_changelog,
)

__all__ = ["ChangelogError", "resolve_version"]


def resolve_version(changelog_path: Path, branch: str) -> str:
    """Resolve a package/image version from CHANGELOG.md.

    On 'main':
    - Returns the clean computed next version if [Unreleased] has entries.
    - Returns an empty string if [Unreleased] has no entries (nothing to release).

    On other branches:
    - Appends a 14-digit UTC beta suffix (YYYYMMDDHHMMSS).
    - If [Unreleased] has entries, uses the computed next version.
    - If [Unreleased] has no entries, uses base patch+1 as a build identifier.
    """
    text = changelog_path.read_text(encoding="utf-8")
    changelog = parse_changelog(text)

    if branch == "main":
        if has_entries(changelog):
            return next_version(changelog.base_version, changelog.unreleased)
        return ""

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    if has_entries(changelog):
        ver = next_version(changelog.base_version, changelog.unreleased)
    else:
        parts = [int(p) for p in changelog.base_version.split(".")]
        major, minor, patch = parts
        ver = f"{major}.{minor}.{patch + 1}"

    return f"{ver}-beta.{timestamp}"
