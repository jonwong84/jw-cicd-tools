import json
import urllib.error
import urllib.request


class GitHubApiError(RuntimeError):
    """Raised when the GitHub API request for open pull requests fails
    (see resolve_pr_number)."""


def resolve_pr_number(repo: str, branch: str, token: str) -> str:
    """Resolve the number of the open PR for `branch` in `repo`, or an
    empty string if no open PR exists for that branch.

    `repo` is "owner/name" (e.g. "jonwong84/jukebox-frontend"). `branch`
    is typically $CIRCLE_BRANCH. `token` needs at least read access to
    pull requests on the target repo.

    Uses only the standard library (json, urllib) deliberately, so this
    works unmodified on any CI image with Python installed — no extra
    package install step required, unlike e.g. jq on a minimal image.
    """
    owner = repo.split("/", 1)[0]
    url = f"https://api.github.com/repos/{repo}/pulls?state=open&head={owner}:{branch}"
    request = urllib.request.Request(url, headers={"Authorization": f"token {token}"})

    try:
        with urllib.request.urlopen(request) as response:
            data = json.load(response)
    except urllib.error.HTTPError as error:
        raise GitHubApiError(
            f"GitHub API request failed for {repo} (branch '{branch}'): "
            f"{error.code} {error.reason}"
        ) from error

    return str(data[0]["number"]) if data else ""