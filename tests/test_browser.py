from unittest.mock import patch

from ansel.browser import build_pr_url
from ansel.browser import open_pr


def test_build_pr_url_github():
    assert (
        build_pr_url("https://github.com/vader/death-star", "trench-run")
        == "https://github.com/vader/death-star/compare/trench-run"
    )
    assert (
        build_pr_url("git@github.com:luke/x-wing.git", "force-fix")
        == "https://github.com/luke/x-wing/compare/force-fix"
    )


def test_build_pr_url_generic():
    assert (
        build_pr_url("git@gitea.internal:stark/winterfell.git", "winter-is-coming")
        == "https://gitea.internal/stark/winterfell/compare/winter-is-coming"
    )
    assert (
        build_pr_url("https://gitea.internal/lannister/gold.git", "debt-paid")
        == "https://gitea.internal/lannister/gold/compare/debt-paid"
    )


def test_build_pr_url_ssh_port():
    url = "git@gitea.internal.juventus.com:4444/del-piero/goals.git"
    expected = "https://gitea.internal.juventus.com/del-piero/goals/compare/legend"
    assert build_pr_url(url, "legend") == expected


@patch("webbrowser.open")
def test_open_pr(mock_open):
    url = open_pr("https://github.com/han/falcon", "kessel-run")
    assert url == "https://github.com/han/falcon/compare/kessel-run"
    mock_open.assert_called_once_with(url)
