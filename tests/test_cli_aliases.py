from unittest.mock import MagicMock
from unittest.mock import patch

from ansel.cli import cli


@patch("ansel.cli.load_config")
@patch("ansel.cli.get_version", return_value="0.2.0")
def test_repos_default_list(mock_version, mock_load, cli_runner):
    mock_config = MagicMock()
    mock_config.repositories = {
        "winterfell": MagicMock(url="u1", groups=[], branch="m")
    }
    mock_config.general.workdir = None
    mock_config.general.default_branch = "main"
    mock_load.return_value = mock_config

    result = cli_runner.invoke(cli, ["repos"])
    assert result.exit_code == 0
    assert "ansel v0.2.0 — don't leave crumbs in the woods" in result.output
    assert "NAME" in result.output
    assert "winterfell" in result.output


@patch("ansel.cli.load_config")
@patch("ansel.cli.get_version", return_value="0.2.0")
def test_repo_alias_default_list(mock_version, mock_load, cli_runner):
    mock_config = MagicMock()
    mock_config.repositories = {
        "casterly-rock": MagicMock(url="u1", groups=[], branch="m")
    }
    mock_config.general.workdir = None
    mock_config.general.default_branch = "main"
    mock_load.return_value = mock_config

    result = cli_runner.invoke(cli, ["repo"])
    assert result.exit_code == 0
    assert "ansel v0.2.0 — don't leave crumbs in the woods" in result.output
    assert "NAME" in result.output
    assert "casterly-rock" in result.output


@patch("ansel.cli.load_config")
@patch("ansel.cli.get_version", return_value="0.2.0")
def test_templates_default_list(mock_version, mock_load, cli_runner):
    mock_config = MagicMock()
    mock_config.templates = {
        "dragons.yaml": MagicMock(description="d", vars={}, groups=[], repos=[])
    }
    mock_config.general.workdir = None
    mock_load.return_value = mock_config

    result = cli_runner.invoke(cli, ["templates"])
    assert result.exit_code == 0
    assert "NAME" in result.output
    assert "dragons.yaml" in result.output


@patch("ansel.cli.load_config")
@patch("ansel.cli.get_version", return_value="0.2.0")
def test_template_alias_default_list(mock_version, mock_load, cli_runner):
    mock_config = MagicMock()
    mock_config.templates = {
        "direwolf.yaml": MagicMock(description="d", vars={}, groups=[], repos=[])
    }
    mock_config.general.workdir = None
    mock_load.return_value = mock_config

    result = cli_runner.invoke(cli, ["template"])
    assert result.exit_code == 0
    assert "NAME" in result.output
    assert "direwolf.yaml" in result.output
