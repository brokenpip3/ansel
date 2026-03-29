import os
import subprocess
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from ansel.hooks import Hook
from ansel.hooks import HookRegistry


def test_hook_registry_discovery(tmp_path):
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    script = hooks_dir / "valyrian-spell.sh"
    script.write_text("#!/bin/bash\necho dracarys")
    script.chmod(script.stat().st_mode | os.X_OK)

    registry = HookRegistry(tmp_path)
    discovered = registry.get_discovered_hooks()

    assert "valyrian-spell.sh" in discovered
    assert discovered["valyrian-spell.sh"].type == "discovered"


@patch("subprocess.run")
def test_hook_registry_run_pipeline(mock_run, tmp_path):
    registry = HookRegistry(tmp_path)

    hooks = [
        Hook(name="h1", type="config", run="!cmd echo {{ repo_name }}"),
        Hook(name="h2", type="config", run="ls -la", allow_failure=True),
    ]

    vars_dict = {"repo_name": "winterfell"}
    log_mock = MagicMock()

    registry.run_pipeline(tmp_path, hooks, vars_dict, log_mock)

    assert mock_run.call_count == 2
    mock_run.assert_any_call(
        "echo winterfell",
        shell=True,
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=True,
    )

    log_mock.assert_any_call("hook/h1: running", is_last=False, indent=0)
    log_mock.assert_any_call("hook/h1: passed", is_last=False, overwrite=True, indent=0)


@patch("subprocess.run")
def test_hook_pipeline_blocking_failure(mock_run, tmp_path):
    registry = HookRegistry(tmp_path)
    mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")

    hooks = [Hook(name="fail", type="config", run="fail", allow_failure=False)]

    from ansel.exceptions import AnselError

    with pytest.raises(AnselError, match="Hook fail failed and is blocking."):
        registry.run_pipeline(tmp_path, hooks, {}, MagicMock())


def test_hook_check_yaml(tmp_path):
    registry = HookRegistry(tmp_path)
    h = registry.builtins["check-yaml"]

    (tmp_path / "stark.yaml").write_text("lord: ned")
    h.run(tmp_path, {})

    (tmp_path / "bolton.yml").write_text("lord: : :")
    from ansel.exceptions import AnselError

    with pytest.raises(AnselError, match="bolton.yml"):
        h.run(tmp_path, {})


def test_hook_check_toml(tmp_path):
    registry = HookRegistry(tmp_path)
    h = registry.builtins["check-toml"]

    (tmp_path / "lannister.toml").write_text('debt = "paid"')
    h.run(tmp_path, {})

    (tmp_path / "greyjoy.toml").write_text("what = dead [")
    from ansel.exceptions import AnselError

    with pytest.raises(AnselError, match="greyjoy.toml"):
        h.run(tmp_path, {})
