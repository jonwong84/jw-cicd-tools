import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from jw_cicd_tools.pr import GitHubApiError, resolve_pr_number


def _make_response(payload: object) -> MagicMock:
    response = MagicMock()
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    response.read.return_value = json.dumps(payload).encode("utf-8")
    return response


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
def test_resolve_pr_number_uses_repo_owner_in_head_query(mock_urlopen):
    mock_urlopen.return_value = _make_response([{"number": 7}])

    resolve_pr_number("someorg/some-repo", "feature/x", "tok")

    requested = mock_urlopen.call_args[0][0]
    assert "head=someorg:feature/x" in requested.full_url
    assert "someorg/some-repo" in requested.full_url


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
