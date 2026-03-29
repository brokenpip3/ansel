from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

from ansel.cli import cli


def setup_mock_config(tmp_path, dump_yaml_func):
    config_file = tmp_path / "ansel.yaml"
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "dragons.yaml").touch()

    config_data = {
        "repositories": {"iron-throne": {"url": "https://westeros.gov/throne.git"}},
        "templates": {"dragons.yaml": {}},
    }
    dump_yaml_func(config_data, config_file)
    return config_file


@patch("ansel.cli.load_config")
@patch("ansel.cli.clone_or_pull")
@patch("ansel.cli.create_branch")
@patch("ansel.cli.apply_template")
@patch("ansel.cli.commit_and_push")
@patch("ansel.cli.open_pr")
def test_sync_calls_all_steps(
    mock_open,
    mock_commit,
    mock_apply,
    mock_branch,
    mock_clone,
    mock_load,
    tmp_path,
    cli_runner,
):
    mock_config = MagicMock()
    mock_config.repositories = {
        "iron-throne": MagicMock(url="url1", groups=["westeros"], branch="main")
    }
    mock_config.templates = {
        "dragons.yaml": MagicMock(
            name="dragons.yaml",
            path="path1",
            vars={},
            groups=["westeros"],
            repos=[],
            skip_groups=[],
            skip_repos=[],
            type="template",
        )
    }
    mock_config.general.vars = {}
    mock_config.general.commit_message = "msg"
    mock_config.general.workdir = None
    mock_config.general.default_branch = "main"
    mock_config.general.use_pre_commit = False
    mock_config.general.hooks = []
    mock_load.return_value = mock_config

    mock_repo = MagicMock()
    repo_dir = tmp_path / "iron-throne"
    repo_dir.mkdir()
    (repo_dir / "dragons.yaml").write_text("dracarys")
    mock_repo.working_tree_dir = str(repo_dir)
    mock_clone.return_value = mock_repo

    mock_apply.return_value = ["dragons.yaml"]
    mock_commit.return_value = True

    with cli_runner.isolated_filesystem(temp_dir=tmp_path):
        Path("ansel.yaml").touch()
        result = cli_runner.invoke(cli, ["sync"])

        assert result.exit_code == 0
        assert "◌ iron-throne" in result.output
        assert "cloning..." in result.output
        assert "applied: dragons.yaml" in result.output
        assert "✓ iron-throne: updated" in result.output


@patch("ansel.cli.load_config")
def test_repos_list(mock_load, cli_runner):
    mock_config = MagicMock()
    mock_repo = MagicMock(
        url="https://westeros.gov/throne.git", groups=["westeros"], branch="main"
    )
    mock_config.repositories = {"iron-throne": mock_repo}
    mock_config.general.workdir = None
    mock_config.general.default_branch = "main"
    mock_load.return_value = mock_config

    result = cli_runner.invoke(cli, ["repos", "list"])
    assert result.exit_code == 0
    assert "NAME" in result.output
    assert "iron-throne" in result.output
    assert "westeros" in result.output


@patch("ansel.cli.load_config")
def test_templates_list(mock_load, cli_runner):
    mock_config = MagicMock()
    mock_template = MagicMock(
        description="fire and blood",
        vars={"dragons": 3},
        groups=["targaryen"],
        repos=["dragonstone"],
        skip_groups=[],
        skip_repos=[],
    )
    mock_config.templates = {"dragons.yaml": mock_template}
    mock_config.general.workdir = None
    mock_load.return_value = mock_config

    result = cli_runner.invoke(cli, ["templates", "list"])
    assert result.exit_code == 0
    assert "NAME" in result.output
    assert "dragons.yaml" in result.output
    assert "fire and blood" in result.output
    assert "targaryen" in result.output
    assert "1" in result.output


@patch("ansel.cli.load_config")
def test_builtins_command(mock_load, cli_runner):
    mock_config = MagicMock()
    mock_config.config_dir = Path(".")
    mock_config.general.hooks = []
    mock_config.general.workdir = None
    mock_load.return_value = mock_config

    result = cli_runner.invoke(cli, ["builtins"])
    assert result.exit_code == 0
    assert "NAME" in result.output
    assert "TYPE" in result.output
    assert "hook" in result.output
    assert "var" in result.output


@patch("ansel.cli.load_config")
@patch("ansel.cli.clone_or_pull")
@patch("ansel.cli.create_branch")
@patch("ansel.cli.apply_template")
@patch("ansel.cli.commit_and_push")
@patch("ansel.cli.open_pr")
def test_sync_continues_on_repo_failure(
    mock_open,
    mock_commit,
    mock_apply,
    mock_branch,
    mock_clone,
    mock_load,
    tmp_path,
    cli_runner,
):
    mock_config = MagicMock()
    mock_config.repositories = {
        "winterfell": MagicMock(url="url1", groups=[], branch="main"),
        "casterly-rock": MagicMock(url="url2", groups=[], branch="main"),
    }
    mock_config.templates = {
        "wolf.yaml": MagicMock(
            name="wolf",
            path="p1",
            vars={},
            groups=[],
            repos=[],
            skip_groups=[],
            skip_repos=[],
            type="template",
        )
    }
    mock_config.general.vars = {}
    mock_config.general.commit_message = "msg"
    mock_config.general.workdir = None
    mock_config.general.default_branch = "main"
    mock_config.general.use_pre_commit = False
    mock_config.general.hooks = []
    mock_load.return_value = mock_config

    mock_clone.side_effect = [Exception("white walkers"), MagicMock()]

    with cli_runner.isolated_filesystem(temp_dir=tmp_path):
        Path("ansel.yaml").touch()
        result = cli_runner.invoke(cli, ["sync"])

        assert result.exit_code == 1
        assert "◌ winterfell" in result.output
        assert "✗ winterfell: failed: white walkers" in result.output
        assert mock_clone.call_count == 2


@patch("ansel.cli.load_config")
@patch("ansel.cli.clone_or_pull")
@patch("ansel.cli.apply_template")
@patch("ansel.cli.commit_and_push")
def test_sync_summary_exit_code(
    mock_commit, mock_apply, mock_clone, mock_load, tmp_path, cli_runner
):
    mock_config = MagicMock()
    mock_config.repositories = {"braavos": MagicMock(url="u1", groups=[], branch="m")}
    mock_config.templates = {
        "coin": MagicMock(
            name="t1",
            path="p1",
            vars={},
            groups=[],
            repos=[],
            skip_groups=[],
            skip_repos=[],
        )
    }
    mock_config.general.vars = {}
    mock_config.general.commit_message = "valar morghulis"
    mock_config.general.workdir = None
    mock_config.general.default_branch = "main"
    mock_config.general.use_pre_commit = False
    mock_config.general.hooks = []
    mock_load.return_value = mock_config

    mock_repo = MagicMock()
    repo_dir = tmp_path / "braavos"
    repo_dir.mkdir()
    (repo_dir / "coin").write_text("iron")
    mock_repo.working_tree_dir = str(repo_dir)
    mock_clone.return_value = mock_repo

    mock_apply.return_value = ["coin"]
    mock_commit.return_value = True

    with cli_runner.isolated_filesystem(temp_dir=tmp_path):
        Path("ansel.yaml").touch()
        result = cli_runner.invoke(cli, ["sync"])

        assert result.exit_code == 0
        assert "RESOURCE" in result.output
        assert "repositories" in result.output


@patch("ansel.cli.load_config")
@patch("ansel.cli.clone_or_pull")
@patch("ansel.cli.apply_template")
@patch("ansel.cli.commit_and_push")
@patch("click.prompt")
def test_sync_plan_interactive(
    mock_prompt, mock_commit, mock_apply, mock_clone, mock_load, tmp_path, cli_runner
):
    mock_config = MagicMock()
    mock_config.repositories = {"the-wall": MagicMock(url="u1", groups=[], branch="m")}
    mock_config.templates = {
        "oath": MagicMock(
            name="t1",
            path="p1",
            vars={},
            groups=[],
            repos=[],
            skip_groups=[],
            skip_repos=[],
            type="template",
        ),
        "watch": MagicMock(
            name="t2",
            path="p2",
            vars={},
            groups=[],
            repos=[],
            skip_groups=[],
            skip_repos=[],
            type="template",
        ),
    }
    mock_config.general.vars = {}
    mock_config.general.commit_message = "msg"
    mock_config.general.workdir = None
    mock_config.general.default_branch = "main"
    mock_config.general.use_pre_commit = False
    mock_config.general.hooks = []
    mock_load.return_value = mock_config

    mock_repo = MagicMock()
    repo_dir = tmp_path / "the-wall"
    repo_dir.mkdir()
    (repo_dir / "oath").write_text("v1")
    (repo_dir / "watch").write_text("v2")
    mock_repo.working_tree_dir = str(repo_dir)
    mock_clone.return_value = mock_repo

    mock_apply.side_effect = [["oath"], ["watch"]]
    mock_prompt.side_effect = ["n", "y"]
    mock_commit.return_value = True

    with cli_runner.isolated_filesystem(temp_dir=tmp_path):
        Path("ansel.yaml").touch()
        result = cli_runner.invoke(cli, ["sync", "--plan"])

        assert result.exit_code == 0
        mock_commit.assert_called_once()
        assert "planned: oath changed" in result.output
        assert "planned: watch changed" in result.output


@patch("ansel.cli.load_config")
@patch("ansel.cli.clone_or_pull")
@patch("ansel.cli.apply_template")
@patch("ansel.cli.compute_diff")
def test_diff_shows_changes(
    mock_diff, mock_apply, mock_clone, mock_load, tmp_path, cli_runner
):
    mock_config = MagicMock()
    mock_config.repositories = {
        "kings-landing": MagicMock(url="u1", groups=[], branch="m")
    }
    mock_config.templates = {
        "decree": MagicMock(
            name="t1",
            path="p1",
            vars={},
            groups=[],
            repos=[],
            skip_groups=[],
            skip_repos=[],
            type="template",
        )
    }
    mock_config.general.vars = {}
    mock_config.general.commit_message = "msg"
    mock_config.general.workdir = None
    mock_config.general.default_branch = "main"
    mock_config.general.use_pre_commit = False
    mock_config.general.hooks = []
    mock_load.return_value = mock_config

    mock_repo = MagicMock()
    repo_dir = tmp_path / "kings-landing"
    repo_dir.mkdir()
    (repo_dir / "decree").write_text("new decree")
    mock_repo.working_tree_dir = str(repo_dir)
    mock_clone.return_value = mock_repo

    mock_apply.return_value = ["decree"]
    mock_diff.return_value = "wildfire spread"

    with cli_runner.isolated_filesystem(temp_dir=tmp_path):
        Path("ansel.yaml").touch()
        result = cli_runner.invoke(cli, ["sync", "--dry-run"])
        assert result.exit_code == 0
        assert "planning changes" in result.output
        assert "decree changed" in result.output
        assert "wildfire spread" in result.output


@patch("ansel.cli.load_config")
@patch("ansel.cli.clone_or_pull")
@patch("ansel.cli.apply_template")
@patch("ansel.cli.compute_diff")
def test_sync_dry_run_captures_original_content(
    mock_diff, mock_apply, mock_clone, mock_load, tmp_path, cli_runner
):
    mock_config = MagicMock()
    mock_config.repositories = {"harrenhal": MagicMock(url="u1", groups=[], branch="m")}
    mock_config.templates = {
        "curse": MagicMock(
            name="p1",
            type="patch",
            include=["walls.txt"],
            operations=[{"engine": "regex", "search": "clean", "replace": "ruined"}],
            groups=[],
            repos=[],
            skip_groups=[],
            skip_repos=[],
        )
    }
    mock_config.general.vars = {}
    mock_config.general.commit_message = "msg"
    mock_config.general.workdir = None
    mock_config.general.default_branch = "main"
    mock_config.general.use_pre_commit = False
    mock_config.general.hooks = []
    mock_load.return_value = mock_config

    mock_repo = MagicMock()
    repo_dir = tmp_path / "curse_special"
    repo_dir.mkdir()
    wall_file = repo_dir / "walls.txt"
    wall_file.write_text("clean walls\n")
    mock_repo.working_tree_dir = str(repo_dir)
    mock_clone.return_value = mock_repo

    def simulate_apply(*args, **kwargs):
        wall_file.write_text("ruined walls\n")
        return ["walls.txt"]

    mock_apply.side_effect = simulate_apply

    with cli_runner.isolated_filesystem(temp_dir=tmp_path):
        Path("ansel.yaml").touch()
        cli_runner.invoke(cli, ["sync", "--dry-run"])

        mock_diff.assert_called()
        _, kwargs = mock_diff.call_args
        assert kwargs["original_content"] == "clean walls\n"
