# jw-cicd-tools

Personal, reusable CI/CD tooling — shared logic (version resolution, build/test/publish
helpers) callable from any CircleCI pipeline via a single CLI, instead of duplicating
bash across repos.

Not tied to any one project — install and use from any repo's `config.yml`.

## Install

```bash
pip install git+https://github.com/<you>/jw-cicd-tools.git@v0.2.0
```

## Usage

```bash
jw_cicd version resolve --changelog CHANGELOG.md --branch "$CIRCLE_BRANCH"
```

Resolves the current version from a `CHANGELOG.md` (Keep a Changelog format,
newest entry first). On `main`, returns the base version as-is (e.g. `1.1.1`).
On any other branch, appends a UTC timestamp beta suffix (e.g.
`1.1.1-beta.20260905143000`).

### Changelog convention (required as of v0.2.0)

The top-most entry in `CHANGELOG.md` must carry an explicit status instead of
just a date, so the tool can tell whether it's safe to build a beta of it:

```md
## [1.1.2] - Unreleased

### Added
- Work in progress goes here

## [1.1.1] - 2026-06-18

### Updated
- Already-shipped work
```

- **On a feature branch**, the top entry must say `Unreleased`. Add a new
  `## [X.Y.Z] - Unreleased` entry as soon as you start new work — don't wait
  until it's done. If the top entry already has a real date instead, the
  tool raises a `ChangelogError` rather than silently building a beta of a
  version that's already shipped.
- **On `main`**, the top entry must carry a real release date, not
  `Unreleased` — the tool raises a `ChangelogError` if you try to merge
  without finalizing the changelog first.

## Development

```bash
pip install -e ".[dev]"
pytest
```
