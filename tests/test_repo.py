from unittest.mock import MagicMock
from unittest.mock import patch

from git import GitCommandError

from ansel.config import RepositoryConfig
from ansel.repo import clone_or_pull
from ansel.repo import commit_and_push
from ansel.repo import create_branch
from ansel.repo import get_workdir


@patch("ansel.repo.Repo.clone_from")
def test_clone_when_absent(mock_clone, tmp_path):
    repo_cfg = RepositoryConfig(
        name="del-piero", url="https://juve.it/pinturicchio.git", branch="capitano"
    )
    workdir = tmp_path

    clone_or_pull(repo_cfg, workdir, "capitano")

    mock_clone.assert_called_once_with(
        "https://juve.it/pinturicchio.git", workdir / "del-piero"
    )


@patch("ansel.repo.Repo")
def test_pull_when_present(mock_repo_class, tmp_path):
    repo_cfg = RepositoryConfig(
        name="vlahovic", url="https://juve.it/dv9.git", branch="scudetto"
    )
    workdir = tmp_path
    (workdir / "vlahovic").mkdir()

    mock_repo = mock_repo_class.return_value
    mock_repo.remotes.origin.refs = ["scudetto"]

    clone_or_pull(repo_cfg, workdir, "capitano")

    mock_repo.remotes.origin.fetch.assert_called_once()
    mock_repo.git.checkout.assert_called_with("scudetto")


@patch("ansel.repo.Repo")
def test_pull_when_branch_missing(mock_repo_class, tmp_path):
    repo_cfg = RepositoryConfig(
        name="chiesa", url="https://juve.it/fede.git", branch="rehab"
    )
    workdir = tmp_path
    (workdir / "chiesa").mkdir()

    mock_repo = mock_repo_class.return_value
    mock_repo.remotes.origin.refs = ["capitano"]

    clone_or_pull(repo_cfg, workdir, "capitano")

    mock_repo.git.reset.assert_called_with("--hard", "HEAD")


@patch("ansel.repo.Repo")
def test_pull_when_repo_empty(mock_repo_class, tmp_path):
    repo_cfg = RepositoryConfig(
        name="danilo", url="https://juve.it/captain.git", branch="capitano"
    )
    workdir = tmp_path
    (workdir / "danilo").mkdir()

    mock_repo = mock_repo_class.return_value
    mock_repo.remotes.origin.refs = []
    mock_repo.git.rev_parse.side_effect = GitCommandError("rev-parse", 128)

    clone_or_pull(repo_cfg, workdir, "capitano")
    assert not mock_repo.git.reset.called


def test_create_branch():
    mock_repo = MagicMock()
    create_branch(mock_repo, "transfer-window")
    mock_repo.git.checkout.assert_called_with("-b", "transfer-window")


def test_commit_and_push(tmp_path):
    mock_repo = MagicMock()
    repo_dir = tmp_path / "allianz"
    repo_dir.mkdir()
    mock_repo.working_tree_dir = str(repo_dir)

    mock_repo.git.status.return_value = "A  goal.txt"

    abs_path = repo_dir / "goal.txt"
    result = commit_and_push(mock_repo, "scored", "match", [str(abs_path)])

    assert result is True
    mock_repo.git.add.assert_called_with("goal.txt")
    mock_repo.git.status.assert_called_with("--porcelain")
    mock_repo.index.commit.assert_called_with("scored", skip_hooks=True)
    mock_repo.remotes.origin.push.assert_called_with("match", force=True)


def test_commit_and_push_no_changes(tmp_path):
    mock_repo = MagicMock()
    repo_dir = tmp_path / "bench"
    repo_dir.mkdir()
    mock_repo.working_tree_dir = str(repo_dir)
    mock_repo.git.status.return_value = ""

    result = commit_and_push(mock_repo, "nil-nil", "bore-draw", ["nothing.txt"])

    assert result is False
    mock_repo.git.add.assert_called_with("nothing.txt")
    mock_repo.git.status.assert_called_with("--porcelain")
    assert not mock_repo.index.commit.called


def test_get_workdir(tmp_path):
    stadium_dir = tmp_path / "allianz"
    assert get_workdir(flag_workdir=str(stadium_dir)) == stadium_dir

    training_dir = tmp_path / "continassa"
    assert get_workdir(config_workdir=str(training_dir)) == training_dir

    assert "ansel" in str(get_workdir())
