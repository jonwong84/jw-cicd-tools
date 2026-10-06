from datetime import datetime, timezone
from pathlib import Path

import typer

from jw_cicd_tools.changelog import (
    ChangelogError,
    has_entries,
    next_version,
    parse_changelog,
    stamp,
)
from jw_cicd_tools.pr import resolve_pr_number
from jw_cicd_tools.version import resolve_version

app = typer.Typer()

version_app = typer.Typer()
app.add_typer(version_app, name="version")

pr_app = typer.Typer()
app.add_typer(pr_app, name="pr")

release_app = typer.Typer()
app.add_typer(release_app, name="release")


@version_app.command("resolve")
def resolve(
    changelog: Path = typer.Option(Path("CHANGELOG.md"), help="Path to CHANGELOG.md"),
    branch: str = typer.Option(..., help="Current branch name (e.g. $CIRCLE_BRANCH)"),
):
    """Resolve and print the package/image version from the changelog and branch.

    Print a blank line on main when there are no unreleased entries.
    Report ChangelogError on stderr and raise typer.Exit with code 1.
    File access and UTF-8 decoding errors propagate unchanged.
    """
    try:
        typer.echo(resolve_version(changelog, branch))
    except ChangelogError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1)


@release_app.command("stamp")
def stamp_command(
    changelog: Path = typer.Option(Path("CHANGELOG.md"), help="Path to CHANGELOG.md"),
    date: str | None = typer.Option(
        None, help="Release date in YYYY-MM-DD format; defaults to UTC today"
    ),
):
    """Stamp the [Unreleased] heading with the computed next version and release date.

    Rewrite the UTF-8 changelog with a fresh empty [Unreleased] section and
    print the released version. An omitted or empty date defaults to today
    in UTC; otherwise it must be a valid YYYY-MM-DD date. If there are no
    unreleased entries, print a blank line without writing or validating date.

    Report ChangelogError on stderr and raise typer.Exit with code 1.
    File access and Unicode errors propagate unchanged.
    """
    try:
        text = changelog.read_text(encoding="utf-8")
        parsed = parse_changelog(text)
        if not has_entries(parsed):
            typer.echo("")
            return

        release_date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        version = next_version(parsed.base_version, parsed.unreleased)
        new_text = stamp(text, version=version, date=release_date)
        changelog.write_text(new_text, encoding="utf-8")
        typer.echo(version)
    except ChangelogError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1)


@pr_app.command("resolve")
def pr_resolve(
    repo: str = typer.Option(
        ...,
        help="GitHub repo as 'owner/name' (e.g. jonwong84/jukebox-frontend)",
    ),
    branch: str = typer.Option(..., help="Current branch name (e.g. $CIRCLE_BRANCH)"),
    token: str = typer.Option(
        ..., envvar="GITHUB_TOKEN", help="GitHub token; defaults to $GITHUB_TOKEN"
    ),
    head_owner: str = typer.Option(
        None,
        help="Owner of the source branch, if different from --repo's owner "
        "(needed for fork-based PRs). Defaults to --repo's own owner.",
    ),
):
    """Print the first matching open PR number, or a blank line if none exists.

    Errors from resolve_pr_number propagate without printing a result.
    """
    typer.echo(resolve_pr_number(repo, branch, token, head_owner=head_owner))


if __name__ == "__main__":
    app()