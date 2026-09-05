import re
from datetime import datetime, timezone
from pathlib import Path


def resolve_version(changelog_path: Path, branch: str) -> str:
    """Resolve a package/image version from CHANGELOG.md, appending a beta
    suffix with timestamp when not on the main branch.

    Assumes the changelog lists releases with the most recent entry first
    (standard Keep a Changelog convention) - the first version heading found
    is treated as the current/latest version.
    """
    base_version = _parse_latest_version(changelog_path)

    if branch == "main":
        return base_version

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{base_version}-beta.{timestamp}"


def _parse_latest_version(changelog_path: Path) -> str:
    text = changelog_path.read_text(encoding="utf-8")
    # Matches headings like "## [1.2.3] - 2026-09-05" or "## 1.2.3" or "## v1.2.3"
    match = re.search(r"^##\s*\[?v?(\d+\.\d+\.\d+)\]?", text, re.MULTILINE)
    if not match:
        raise ValueError(f"No version heading found in {changelog_path}")
    return match.group(1)
