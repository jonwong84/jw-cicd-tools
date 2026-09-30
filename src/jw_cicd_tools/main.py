from pathlib import Path

import typer

from jw_cicd_tools.pr import resolve_pr_number
from jw_cicd_tools.version import resolve_version

app = typer.Typer()

version_app = typer.Typer()
app.add_typer(version_app, name="version")

pr_app = typer.Typer()
app.add_typer(pr_app, name="pr")


@version_app.command("resolve")
def resolve(
    changelog: Path = typer.Option(Path("CHANGELOG.md"), help="Path to CHANGELOG.md"),
    branch: str = typer.Option(..., help="Current branch name (e.g. $CIRCLE_BRANCH)"),
):
    """Resolve the package/image version from the changelog and branch."""
    typer.echo(resolve_version(changelog, branch))


@pr_app.command("resolve")
def pr_resolve(
    repo: str = typer.Option(..., help="GitHub repo as 'owner/name' (e.g. jonwong84/jukebox-frontend)"),
    branch: str = typer.Option(..., help="Current branch name (e.g. $CIRCLE_BRANCH)"),
    token: str = typer.Option(..., envvar="GITHUB_TOKEN", help="GitHub token; defaults to $GITHUB_TOKEN"),
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