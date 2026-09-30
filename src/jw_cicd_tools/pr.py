import json
import urllib.error
import urllib.parse
import urllib.request

_REQUEST_TIMEOUT_SECONDS = 10


class GitHubApiError(RuntimeError):
    """Raised when the GitHub API request for open pull requests fails
    (see resolve_pr_number)."""


def resolve_pr_number(repo: str, branch: str, token: str, head_owner: str | None = None) -> str:
    """Resolve the number of the open PR for `branch` in `repo`, or an
    empty string if no open PR exists for that branch.

    `repo` is "owner/name" (e.g. "jonwong84/jukebox-frontend") — the
    repository being searched. `branch` is typically $CIRCLE_BRANCH.
    `token` needs at least read access to pull requests on the target
    repo. `head_owner` is the owner of the *source* branch — for a PR
    opened from a fork, this is the contributor's account, not
    necessarily the target repo's owner, so it defaults to the target
    repo's own owner (correct for same-repo branches, which is the
    common case) but can be overridden for fork-based PRs.

    Uses only the standard library (json, urllib) deliberately, so this
    works unmodified on any CI image with Python installed — no extra
    package install step required, unlike e.g. jq on a minimal image.
    """
    repo_owner = repo.split("/", 1)[0]
    owner = head_owner or repo_owner

    query = urllib.parse.urlencode({"state": "open", "head": f"{owner}:{branch}"})
    url = f"https://api.github.com/repos/{repo}/pulls?{query}"
    request = urllib.request.Request(url, headers={"Authorization": f"token {token}"})

    try:
        with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
            data = json.load(response)
    except urllib.error.HTTPError as error:
        raise GitHubApiError(
            f"GitHub API request failed for {repo} (branch '{branch}'): "
            f"{error.code} {error.reason}"
        ) from error
    except (urllib.error.URLError, TimeoutError) as error:
        # Covers both a bare TimeoutError and a timeout wrapped inside
        # URLError — urlopen's actual behavior here varies depending on
        # where in the request the timeout occurs, so both are handled
        # the same way rather than assuming one or the other.
        raise GitHubApiError(
            f"GitHub API request failed for {repo} (branch '{branch}'): {error}"
        ) from error

    return str(data[0]["number"]) if data else ""