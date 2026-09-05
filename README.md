# jw-cicd-tools

Personal, reusable CI/CD tooling — shared logic (version resolution, build/test/publish
helpers) callable from any CircleCI pipeline via a single CLI, instead of duplicating
bash across repos.

Not tied to any one project — install and use from any repo's `config.yml`.

## Install

```bash
pip install git+https://github.com/<you>/jw-cicd-tools.git@v0.1.0
```

## Usage

```bash
jw_cicd version resolve --changelog CHANGELOG.md --branch "$CIRCLE_BRANCH"
```

Resolves the current version from a `CHANGELOG.md` (Keep a Changelog format,
newest entry first). On `main`, returns the base version as-is (e.g. `1.1.1`).
On any other branch, appends a UTC timestamp beta suffix (e.g.
`1.1.1-beta.20260905143000`).

## Development

```bash
pip install -e ".[dev]"
pytest
```
