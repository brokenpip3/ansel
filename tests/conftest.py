from pathlib import Path
from typing import Any
from typing import Dict
from unittest.mock import MagicMock

import pytest
from ruamel.yaml import YAML

from ansel.config import AnselConfig
from ansel.config import GeneralConfig
from ansel.config import RepositoryConfig
from ansel.config import TemplateConfig
from ansel.patch.engines.regex import RegexPatchEngine
from ansel.patch.engines.toml import TomlPatchEngine
from ansel.patch.engines.yaml import YamlPatchEngine
from ansel.patch.manager import PatchManager


@pytest.fixture
def yaml_writer():
    yaml = YAML()
    yaml.default_flow_style = False
    return yaml


@pytest.fixture
def dump_yaml_func(yaml_writer):
    def _dump(data, path):
        with open(path, "w") as f:
            yaml_writer.dump(data, f)

    return _dump


@pytest.fixture
def cli_runner():
    from click.testing import CliRunner

    return CliRunner()


@pytest.fixture
def yaml_engine():
    return YamlPatchEngine()


@pytest.fixture
def toml_engine():
    return TomlPatchEngine()


@pytest.fixture
def regex_engine():
    return RegexPatchEngine()


@pytest.fixture
def patch_manager():
    return PatchManager()


@pytest.fixture
def global_vars() -> Dict[str, Any]:
    return {"org_name": "tatooine-moons", "env": "prod"}


@pytest.fixture
def template_vars() -> Dict[str, Any]:
    return {"version": "1.0.0", "owner": "stark"}


@pytest.fixture
def mock_repo() -> MagicMock:
    repo = MagicMock()
    repo.working_tree_dir = "/tmp/rebel-base"
    repo.remotes.origin.refs = ["main"]
    repo.branches = []
    return repo


@pytest.fixture
def ansel_config(tmp_path: Path) -> AnselConfig:
    general = GeneralConfig(commit_message="msg", vars={"g": "1"})
    repos = {
        "millennium-falcon": RepositoryConfig(
            name="millennium-falcon",
            url="https://host/falcon.git",
            group="rebel-alliance",
        )
    }
    templates = {
        "dragons.yaml": TemplateConfig(
            name="dragons.yaml",
            path=str(tmp_path / "templates/dragons.yaml"),
            vars={"l": "2"},
        )
    }
    return AnselConfig(
        general=general, repositories=repos, templates=templates, config_dir=tmp_path
    )


@pytest.fixture
def project_fs(tmp_path: Path) -> Path:
    config_file = tmp_path / "ansel.yaml"
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "welcome.j2").write_text("hello {{ name }}")

    config_data = {
        "general": {"vars": {"name": "winterfell"}},
        "repositories": {"r1": {"url": "https://host/r1.git"}},
        "templates": {"welcome.j2": {}},
    }
    yaml_obj = YAML()
    with open(config_file, "w") as f:
        yaml_obj.dump(config_data, f)
    return tmp_path
