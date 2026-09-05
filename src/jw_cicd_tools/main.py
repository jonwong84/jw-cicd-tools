from pathlib import Path

import typer

from jw_cicd_tools.version import resolve_version

app = typer.Typer()
version_app = typer.Typer()
app.add_typer(version_app, name="version")


@version_app.command("resolve")
def resolve(
    changelog: Path = typer.Option(Path("CHANGELOG.md"), help="Path to CHANGELOG.md"),
    branch: str = typer.Option(..., help="Current branch name (e.g. $CIRCLE_BRANCH)"),
):
    """Resolve the package/image version from the changelog and branch."""
    typer.echo(resolve_version(changelog, branch))


if __name__ == "__main__":
    app()
