import json
from unittest.mock import MagicMock
from unittest.mock import patch
from urllib.error import HTTPError

from ansel.github import fetch_repos


@patch("shutil.which", return_value=None)
@patch("urllib.request.urlopen")
@patch("urllib.request.Request")
def test_fetch_repos_org_success(mock_request, mock_urlopen, mock_which):
    mock_response_p1 = MagicMock()
    mock_response_p1.read.return_value = json.dumps(
        [{"full_name": "rebel-alliance/x-wing"}, {"full_name": "rebel-alliance/y-wing"}]
    ).encode()
    mock_response_p1.__enter__.return_value = mock_response_p1

    mock_response_p2 = MagicMock()
    mock_response_p2.read.return_value = b"[]"
    mock_response_p2.__enter__.return_value = mock_response_p2

    mock_urlopen.side_effect = [mock_response_p1, mock_response_p2]

    repos = fetch_repos("rebel-alliance")
    assert repos == ["rebel-alliance/x-wing", "rebel-alliance/y-wing"]
    assert mock_urlopen.call_count == 2
    args, _ = mock_request.call_args_list[0]
    assert "orgs/rebel-alliance/repos" in args[0]


@patch("shutil.which", return_value=None)
@patch("urllib.request.urlopen")
@patch("urllib.request.Request")
def test_fetch_repos_user_fallback(mock_request, mock_urlopen, mock_which):
    mock_response_user_p1 = MagicMock()
    mock_response_user_p1.read.return_value = json.dumps(
        [{"full_name": "luke/landspeeder"}]
    ).encode()
    mock_response_user_p1.__enter__.return_value = mock_response_user_p1

    mock_response_user_p2 = MagicMock()
    mock_response_user_p2.read.return_value = b"[]"
    mock_response_user_p2.__enter__.return_value = mock_response_user_p2

    mock_urlopen.side_effect = [
        HTTPError("url", 404, "Not Found", {}, None),
        mock_response_user_p1,
        mock_response_user_p2,
    ]

    repos = fetch_repos("luke")
    assert repos == ["luke/landspeeder"]
    assert mock_urlopen.call_count == 3
    args, _ = mock_request.call_args_list[1]
    assert "users/luke/repos" in args[0]


@patch("shutil.which", return_value=None)
@patch("urllib.request.urlopen")
def test_fetch_repos_empty_page1(mock_urlopen, mock_which):
    mock_response_empty = MagicMock()
    mock_response_empty.read.return_value = b"[]"
    mock_response_empty.__enter__.return_value = mock_response_empty
    mock_urlopen.return_value = mock_response_empty

    repos = fetch_repos("jar-jar")
    assert repos == []


@patch("shutil.which", return_value=None)
@patch("urllib.request.urlopen")
def test_fetch_repos_pagination(mock_urlopen, mock_which):
    mock_response_p1 = MagicMock()
    mock_response_p1.read.return_value = json.dumps(
        [{"full_name": "empire/tie-fighter"}]
    ).encode()
    mock_response_p1.__enter__.return_value = mock_response_p1

    mock_response_p2 = MagicMock()
    mock_response_p2.read.return_value = b"[]"
    mock_response_p2.__enter__.return_value = mock_response_p2

    mock_urlopen.side_effect = [mock_response_p1, mock_response_p2]

    repos = fetch_repos("empire")
    assert repos == ["empire/tie-fighter"]


@patch("shutil.which", return_value=None)
@patch("urllib.request.urlopen")
def test_fetch_repos_http_error_non_404(mock_urlopen, mock_which):
    mock_urlopen.side_effect = HTTPError("url", 500, "Death Star explosion", {}, None)

    try:
        fetch_repos("alderaan")
    except HTTPError as e:
        assert e.code == 500


@patch("subprocess.run")
@patch("shutil.which")
def test_fetch_repos_with_gh_already_logged_in(mock_which, mock_run):
    mock_which.return_value = "/usr/bin/gh"

    mock_run.side_effect = [
        MagicMock(returncode=0),
        MagicMock(
            returncode=0,
            stdout=json.dumps([{"nameWithOwner": "juventus/allianz"}]).encode(),
        ),
    ]

    repos = fetch_repos("juventus", use_gh_cli=True)
    assert repos == ["juventus/allianz"]
    assert mock_run.call_count == 2
    mock_run.assert_any_call(["gh", "auth", "status"], capture_output=True)


@patch("subprocess.run")
@patch("shutil.which")
def test_fetch_repos_with_gh_needs_login(mock_which, mock_run):
    mock_which.return_value = "/usr/bin/gh"

    mock_run.side_effect = [
        MagicMock(returncode=1),
        MagicMock(returncode=0),
        MagicMock(
            returncode=0,
            stdout=json.dumps([{"nameWithOwner": "stark/winterfell"}]).encode(),
        ),
        MagicMock(returncode=0),
    ]

    repos = fetch_repos("stark", use_gh_cli=True)
    assert repos == ["stark/winterfell"]
    assert mock_run.call_count == 4
    mock_run.assert_any_call(["gh", "auth", "login", "--web"], check=True)
    mock_run.assert_any_call(["gh", "auth", "logout", "--hostname", "github.com"])
