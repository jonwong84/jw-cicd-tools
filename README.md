# jw-cicd-tools

Personal, reusable CI/CD tooling — shared logic (version resolution, build/test/publish
helpers) callable from any CircleCI pipeline via a single CLI, instead of duplicating
bash across repos.

Not tied to any one project — install and use from any repo's `config.yml`.

## Install

Pin to the commit a release tag points at, not to the tag itself. A tag can be moved,
and CI jobs that run this tool hold repository tokens. A commit SHA cannot be moved.

```bash
# v0.4.0
pip install git+https://github.com/jonwong84/jw-cicd-tools.git@d2b8915ab74ca83b5e9410181133b99ce56294b4
```

Find a release's commit with `git rev-parse "v0.4.0^{commit}"`.

## Usage

### Resolve a version

```bash
jw_cicd version resolve --changelog CHANGELOG.md --branch "$CIRCLE_BRANCH"
```

Computes the next version from a `CHANGELOG.md` (Keep a Changelog format with an
unversioned `## [Unreleased]` heading; see
[Releases and versioning](#releases-and-versioning)).

- On `main`, prints the version that will be released (e.g. `1.2.0`), or a blank line
  when there is nothing to release.
- On any other branch, appends a UTC timestamp beta suffix (e.g.
  `1.2.0-beta.20260905143000`).

### Stamp the changelog

```bash
jw_cicd release stamp --changelog CHANGELOG.md [--date YYYY-MM-DD]
```

Rewrites the changelog in place: renames `## [Unreleased]` to `## [X.Y.Z] - <date>` (UTC
today by default) and inserts a fresh, empty `## [Unreleased]` above it. Prints the
version, or a blank line (and leaves the file untouched) when `[Unreleased]` has no
entries. It runs no git commands; committing, tagging, and pushing belong to the CI job.

If the changelog is invalid, both commands print the problem to stderr and exit 1
(no traceback).

### PR resolution (added in v0.3.0)

```bash
jw_cicd pr resolve --repo jonwong84/jukebox-frontend --branch "$CIRCLE_BRANCH"
```

Resolves the number of the open PR for a branch, or prints nothing if no
open PR exists yet.

- `--repo` is `owner/name` — this is what makes the command reusable across
  every repo, not just one.
- `--branch` is typically `$CIRCLE_BRANCH`.
- `--token` defaults to reading `$GITHUB_TOKEN` from the environment, so it
  usually doesn't need to be passed explicitly. Reading it from the
  environment rather than accepting it only as a CLI flag avoids the token
  showing up in process-list output (`ps aux`) on some systems.

If the GitHub API request itself fails (bad token, rate limit, network
issue), the command raises `GitHubApiError` and exits non-zero — a real
failure is never silently treated the same as "no open PR found."

## Releases and versioning

Repos that use this tool follow trunk-based development: short-lived branches, small PRs,
and **a release on every merge to `main` that has changelog entries**. You never choose a
version number; CI computes it from `CHANGELOG.md`.

> **Upgrading from v0.3.0 or earlier:** v0.4.0 replaced the old
> `## [X.Y.Z] - Unreleased` heading convention. The old style is now rejected with a
> migration message. See [Adopting it in a repo](#adopting-it-in-a-repo).

Two operating rules keep releases safe:

- Only the newest commit on `main` should release. A `release` job should skip when `main`
  has moved past its pipeline's commit, because a newer pipeline's tree includes the older
  changes. If that newer pipeline fails, the older entries wait in `[Unreleased]` for the
  next successful release. The reference `release` job in this repo's
  `.circleci/config.yml` does this.
- After a failed release, use "Rerun workflow from failed" instead of a full rerun.

### What you do in a PR

Add bullets under an unversioned `## [Unreleased]` heading at the top of `CHANGELOG.md`,
grouped into subsections:

```md
## [Unreleased]

### Added
- Short description of the change

## [1.2.3] - 2026-10-01

### Fixed
- Already-shipped work
```

Rules the tool enforces:

- `## [Unreleased]` must be the **first** `## [` heading in the file.
- Allowed subsections under `[Unreleased]`: `Added`, `Changed`, `Deprecated`, `Removed`,
  `Fixed`, `Security`, `Breaking`. Any other name (for example `### Updated`) is an error.
  Subsection names in older, dated entries are not checked.
- Every bullet (`- ` or `* `) must sit under one of those subsections.
- The old `## [X.Y.Z] - Unreleased` heading style is rejected with a migration message.
- Headings with escaped brackets (`## \[Unreleased\]`, which some markdown formatters
  produce) are accepted.
- At least one dated heading (`## [X.Y.Z] - YYYY-MM-DD`) must exist.

### How the version is chosen

Two inputs, and nothing else (not the PR title, commit messages, git tags, or changed
files):

1. **Base version:** the first dated heading in the file, which is the latest release.
2. **Bump:** the highest-ranking subsection under `[Unreleased]` that has at least one
   bullet. A subsection heading with no bullets counts as nothing.

| Subsection with entries | Bump |
|---|---|
| `Breaking` | major (minor while the base version is `0.x`) |
| `Added`, `Changed`, `Deprecated`, `Removed` | minor |
| `Fixed`, `Security` | patch |

If several subsections have entries, the highest wins. For example, `Fixed` plus `Added`
is a minor bump. Choosing the subsection is the judgment call: the tool cannot tell
whether a change really is a fix or a feature.

### What happens on a feature branch

`jw_cicd version resolve` computes the same version and appends `-beta.<UTC timestamp>`
(for example `1.2.0-beta.20261006123456`). If `[Unreleased]` has no entries, it uses the
base version's next patch number with the same suffix. This is a build identifier, not a
promise of a release.

### What happens on merge to `main`

1. If `[Unreleased]` has no entries (for example a docs-only change), nothing is released
   and the job succeeds with `Nothing to release.`
2. Otherwise the `release` job:
   - renames `## [Unreleased]` to `## [X.Y.Z] - <UTC date>` and inserts a fresh, empty
     `## [Unreleased]` above it,
   - commits that change as `Release vX.Y.Z [skip ci]`,
   - tags the commit `vX.Y.Z`,
   - pushes the commit and the tag **atomically**, so they land together or not at all.
3. In repos that publish artifacts (for example container images), the publish job runs
   only after the release succeeds and uses the released version.

The date is the UTC date when the release job runs, so a late-evening merge in a US time
zone can be dated the next day. A delayed or rerun job can also be dated after the merge
date.

### Adopting it in a repo

In a single PR:

1. Pin `jw-cicd-tools` to the commit SHA of a release tag (for example `v0.4.0`; see
   [Install](#install)). The pin and the heading must change together: older tool versions
   skip a bare `## [Unreleased]` heading and misread the file.
2. Add `## [Unreleased]` above the top dated entry, with your entries under it. The pin and
   the heading must change together: older tool versions skip a bare `## [Unreleased]`
   heading and misread the file.
3. Add a `release` job that runs only on `main`, after tests (see `.circleci/config.yml`
   in this repo for the reference implementation), and make any publish job depend on it.

CI prerequisites:

- The `main` ruleset must let the CI identity push directly to `main` (for example a
  Repository admin bypass with mode **Always**). Without it, the release job fails at the
  push, and nothing is tagged or published.
- A `GITHUB_TOKEN` with push access, supplied through a CircleCI context.

### Known limits

- **There is no PR check for missing changelog entries yet.** A PR with no entries simply
  releases nothing.

## Development

```bash
pip install -e ".[dev]"
pytest
```