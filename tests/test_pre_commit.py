from unittest.mock import patch

from ansel.hooks import builtin


def test_pre_commit_find_config(tmp_path):
    assert builtin.find_pre_commit_config(tmp_path) is None

    config = tmp_path / ".pre-commit-config.yaml"
    config.touch()
    assert builtin.find_pre_commit_config(tmp_path) == config


@patch("subprocess.run")
def test_pre_commit_run_hooks_success(mock_run, tmp_path):
    config = tmp_path / ".pre-commit-config.yaml"
    config.touch()

    builtin.run_pre_commit(tmp_path, {})

    assert mock_run.call_count == 2
    mock_run.assert_any_call(
        ["pre-commit", "install"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
        text=True,
    )
    mock_run.assert_any_call(
        ["pre-commit", "run", "--all-files"],
        cwd=str(tmp_path),
        check=False,
        capture_output=True,
        text=True,
    )
