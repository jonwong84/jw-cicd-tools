# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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