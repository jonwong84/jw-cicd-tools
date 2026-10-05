# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Breaking
- Changelog convention: PRs now add entries under an unversioned `## [Unreleased]` heading. The old `## [X.Y.Z] - Unreleased` heading style is rejected with a migration message. The version is computed at release time from the entry types, and the heading is stamped with the version and UTC date when a change merges to `main`.

### Added
- `release stamp` command: stamps the `[Unreleased]` heading with the computed version and a release date, and inserts a fresh empty `[Unreleased]` section.
- `release` CircleCI job on `main`: stamps the changelog, commits it with `[skip ci]`, tags the release, and pushes both atomically.

### Changed
- `version resolve` computes the next version from the entry types under `[Unreleased]`, and prints a blank line on `main` when there is nothing to release.
- Command errors print a message and exit 1 without a traceback.

## [0.3.0] - 2026-10-01

### Added
- `pr resolve` command: resolves the open PR number for a branch via
  GitHub's API, for use in CI steps that need to conditionally run
  PR-scoped tooling (e.g. SonarCloud PR decoration). Stdlib-only —
  no new dependency.

## [0.2.0] - 2026-09-18

### Changed
- `version resolve` now requires the changelog's top entry to be explicitly
  marked `## [X.Y.Z] - Unreleased` on non-main branches, and to carry a real
  release date on `main`. Previously the tool trusted whatever version
  heading sat at the top of the file, which meant a stale, already-released
  entry could silently produce a beta tag for a version that had already
  shipped. This is now a loud `ChangelogError` instead of a silent bad tag.

## [0.1.0] - 2026-09-05

### Added
- Initial release of jw-cicd-tools
- `version resolve` — resolves a package/image version from `CHANGELOG.md`, appending a beta + timestamp suffix on non-main branches