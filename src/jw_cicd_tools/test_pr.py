import json
import urllib.error
import urllib.parse
from unittest.mock import MagicMock, patch

import pytest

from jw_cicd_tools.pr import GitHubApiError, resolve_pr_number


def _make_response(payload: object) -> MagicMock:
    response = MagicMock()
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    response.read.return_value = json.dumps(payload).encode("utf-8")
    return response


def _requested_head(mock_urlopen) -> str:
    """Extract the decoded 'head' query param from the last urlopen call,
    regardless of how it was encoded — avoids asserting on raw URL text,
    which breaks the moment encoding changes (e.g. '#' becomes '%23')."""
    requested = mock_urlopen.call_args[0][0]
    query = urllib.parse.urlparse(requested.full_url).query
    return urllib.parse.parse_qs(query)["head"][0]


@patch("jw_cicd_tools.pr.urllib.request.urlopen")
def test_resolve_pr_number_returns_number_when_open_pr_exists(mock_urlopen):
    mock_urlopen.return_value = _make_response([{"number": 42}])

    result = resolve_pr_number("jonwong84/jukebox-frontend", "feature/some-work", "tok")

    assert result == "42"


@patch("jw_cicd_tools.pr.urllib.request.urlopen")
def test_resolve_pr_number_returns_empty_string_when_no_open_pr(mock_urlopen):
    mock_urlopen.return_value = _make_response([])

    result = resolve_pr_number("jonwong84/jukebox-frontend", "feature/some-work", "tok")

    assert result == ""


@patch("jw_cicd_tools.pr.urllib.request.urlopen")
def test_resolve_pr_number_defaults_head_owner_to_repo_owner(mock_urlopen):
    mock_urlopen.return_value = _make_response([{"number": 7}])

    resolve_pr_number("someorg/some-repo", "feature/x", "tok")

    assert _requested_head(mock_urlopen) == "someorg:feature/x"


@patch("jw_cicd_tools.pr.urllib.request.urlopen")
def test_resolve_pr_number_uses_explicit_head_owner_for_fork_prs(mock_urlopen):
    mock_urlopen.return_value = _make_response([{"number": 9}])

    resolve_pr_number("someorg/some-repo", "feature/x", "tok", head_owner="alice")

    # The repo being searched stays someorg/some-repo, but the head owner
    # reflects the fork contributor, not the target repo's owner.
    requested = mock_urlopen.call_args[0][0]
    assert "someorg/some-repo" in requested.full_url
    assert _requested_head(mock_urlopen) == "alice:feature/x"


@patch("jw_cicd_tools.pr.urllib.request.urlopen")
def test_resolve_pr_number_url_encodes_special_characters_in_branch(mock_urlopen):
    mock_urlopen.return_value = _make_response([{"number": 3}])

    resolve_pr_number("jonwong84/jukebox-frontend", "feature/a#b&c", "tok")

    # Decoded back out, the branch name must survive intact — this is what
    # actually proves the query was encoded rather than raw-interpolated.
    assert _requested_head(mock_urlopen) == "jonwong84:feature/a#b&c"


@patch("jw_cicd_tools.pr.urllib.request.urlopen")
def test_resolve_pr_number_raises_github_api_error_on_http_error(mock_urlopen):
    mock_urlopen.side_effect = urllib.error.HTTPError(
        url="https://api.github.com/repos/jonwong84/jukebox-frontend/pulls",
        code=401,
        msg="Unauthorized",
        hdrs=None,
        fp=None,
    )

    with pytest.raises(GitHubApiError, match="401"):
        resolve_pr_number("jonwong84/jukebox-frontend", "feature/some-work", "bad-token")


@patch("jw_cicd_tools.pr.urllib.request.urlopen")
def test_resolve_pr_number_raises_github_api_error_on_timeout(mock_urlopen):
    mock_urlopen.side_effect = TimeoutError("timed out")

    with pytest.raises(GitHubApiError, match="timed out"):
        resolve_pr_number("jonwong84/jukebox-frontend", "feature/some-work", "tok")


@patch("jw_cicd_tools.pr.urllib.request.urlopen")
def test_resolve_pr_number_passes_finite_timeout_to_urlopen(mock_urlopen):
    mock_urlopen.return_value = _make_response([{"number": 1}])

    resolve_pr_number("jonwong84/jukebox-frontend", "feature/x", "tok")

    _, kwargs = mock_urlopen.call_args
    assert kwargs.get("timeout") is not None
    assert kwargs["timeout"] > 0