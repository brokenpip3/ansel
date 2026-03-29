import os
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from ansel.config import detect_url_scheme
from ansel.config import find_config_file
from ansel.config import load_config
from ansel.config import RepositoryConfig
from ansel.config import should_apply_template
from ansel.config import TemplateConfig
from ansel.exceptions import ConfigError
from ansel.hooks import Hook


def test_url_scheme_detection():
    assert detect_url_scheme("git@github.com:vader/death-star.git") == "ssh"
    assert detect_url_scheme("ssh://git@github.com/luke/x-wing.git") == "ssh"
    assert detect_url_scheme("https://github.com/stark/winterfell.git") == "https"
    assert detect_url_scheme("git@gitea.internal:4444/han/falcon.git") == "ssh"
    assert detect_url_scheme("unknown_format") == "unknown"


def test_find_config_file(tmp_path):
    config_file = tmp_path / "ansel.yaml"
    config_file.touch()

    subdir = tmp_path / "tatooine" / "moisture-farm"
    subdir.mkdir(parents=True)

    assert find_config_file(subdir) == config_file


def test_find_config_file_missing(tmp_path):
    with pytest.raises(ConfigError, match="ansel.yaml not found"):
        find_config_file(tmp_path)


def test_load_config_valid(tmp_path, dump_yaml_func):
    config_dir = tmp_path
    config_file = config_dir / "ansel.yaml"
    template_dir = config_dir / "templates"
    template_dir.mkdir()
    (template_dir / "shield-generator.yaml").touch()

    config_data = {
        "general": {"commit_message": "deploy death star", "vars": {"side": "dark"}},
        "repositories": {"death-star": {"url": "https://empire.gov/core.git"}},
        "templates": {"shield-generator.yaml": {"description": "endor base"}},
    }
    dump_yaml_func(config_data, config_file)

    config = load_config(str(config_file))

    assert config.general.commit_message == "deploy death star"
    assert config.general.vars["side"] == "dark"
    assert "death-star" in config.repositories
    assert config.repositories["death-star"].url == "https://empire.gov/core.git"
    assert "shield-generator.yaml" in config.templates
    assert config.templates["shield-generator.yaml"].description == "endor base"


def test_load_config_missing_template(tmp_path, dump_yaml_func):
    config_file = tmp_path / "ansel.yaml"
    config_data = {
        "general": {"commit_message": "test"},
        "templates": {"kyber-crystal.yaml": {}},
    }
    dump_yaml_func(config_data, config_file)

    with pytest.raises(ConfigError, match="Template not found"):
        load_config(str(config_file))


def test_repo_shortcuts(tmp_path, dump_yaml_func):
    config_file = tmp_path / "ansel.yaml"
    config_data = {
        "general": {"gh_org": "juventus"},
        "repositories": {
            "allianz-stadium": {"gh": "ssh://del-piero/stadium"},
            "continassa": {"gitlab": "https://vlahovic/training"},
            "juventus/museum": {},
            "serie-a-trophy": {"gh": "league/trophy"},
        },
    }
    dump_yaml_func(config_data, config_file)

    config = load_config(str(config_file))

    assert (
        config.repositories["allianz-stadium"].url
        == "git@github.com:del-piero/stadium.git"
    )
    assert (
        config.repositories["continassa"].url
        == "https://gitlab.com/vlahovic/training.git"
    )
    assert (
        config.repositories["juventus/museum"].url
        == "git@github.com:juventus/museum.git"
    )
    assert config.repositories["juventus/museum"].name == "museum"
    assert (
        config.repositories["serie-a-trophy"].url == "git@github.com:league/trophy.git"
    )


def test_repo_shortcut_conflict(tmp_path, dump_yaml_func):
    config_file = tmp_path / "ansel.yaml"
    config_data = {
        "repositories": {
            "vader-ship": {"url": "https://host/ship.git", "gh": "empire/executor"}
        }
    }
    dump_yaml_func(config_data, config_file)

    with pytest.raises(ConfigError, match="Multiple URL definitions"):
        load_config(str(config_file))


def test_compact_lists_and_org_defaults(tmp_path, dump_yaml_func):
    config_file = tmp_path / "ansel.yaml"
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "lightsaber.txt").touch()
    (template_dir / "blaster.txt").touch()

    config_data = {
        "general": {"gh_org": "rebel-alliance", "gitlab_org": "galactic-empire"},
        "repositories": [
            "x-wing",
            {"tie-fighter": {"gitlab": "project-strike"}},
        ],
        "templates": [
            "lightsaber.txt",
            {"blaster.txt": {"description": "set to stun"}},
        ],
    }
    dump_yaml_func(config_data, config_file)

    config = load_config(str(config_file))

    assert (
        config.repositories["x-wing"].url == "git@github.com:rebel-alliance/x-wing.git"
    )
    assert (
        config.repositories["tie-fighter"].url
        == "git@gitlab.com:galactic-empire/project-strike.git"
    )
    assert "lightsaber.txt" in config.templates
    assert config.templates["lightsaber.txt"].path == str(
        template_dir / "lightsaber.txt"
    )
    assert config.templates["blaster.txt"].description == "set to stun"


def test_general_config_env_overrides(tmp_path, dump_yaml_func):
    config_file = tmp_path / "ansel.yaml"
    config_data = {
        "general": {
            "commit_message": "standard message",
            "gh_org": "old-org",
            "use_pre_commit": False,
        }
    }
    dump_yaml_func(config_data, config_file)

    env = {
        "ANSEL_COMMIT_MESSAGE": "iron throne message",
        "ANSEL_GH_ORG": "westeros",
        "ANSEL_DEFAULT_BRANCH": "nightswatch",
        "ANSEL_WORKDIR": "/castle/black",
        "ANSEL_GITLAB_ORG": "essos",
        "ANSEL_USE_PRE_COMMIT": "true",
    }

    with patch.dict(os.environ, env):
        config = load_config(str(config_file))

    assert config.general.commit_message == "iron throne message"
    assert config.general.gh_org == "westeros"
    assert config.general.default_branch == "nightswatch"
    assert config.general.workdir == "/castle/black"
    assert config.general.gitlab_org == "essos"
    assert config.general.use_pre_commit is True


def test_repository_multi_groups(tmp_path, dump_yaml_func):
    config_file = tmp_path / "ansel.yaml"
    config_data = {
        "general": {"commit_message": "test"},
        "repositories": {
            "jon-snow": {
                "url": "https://wall.com/jon.git",
                "groups": ["stark", "targaryen"],
            },
            "ned-stark": {"url": "https://wall.com/ned.git", "group": "stark"},
        },
    }
    dump_yaml_func(config_data, config_file)
    config = load_config(str(config_file))

    assert set(config.repositories["jon-snow"].groups) == {"stark", "targaryen"}
    assert set(config.repositories["ned-stark"].groups) == {"stark"}


def test_config_forbids_extra_keys(tmp_path, dump_yaml_func):
    config_file = tmp_path / "ansel.yaml"

    config_data = {
        "general": {"commit_message": "test", "rogue_key": "oops"},
        "repositories": [],
    }
    dump_yaml_func(config_data, config_file)
    with pytest.raises(ConfigError, match="Extra inputs are not permitted"):
        load_config(str(config_file))

    config_data = {
        "general": {"commit_message": "test"},
        "repositories": [{"valyria": {"url": "u", "dragon_fire": True}}],
    }
    dump_yaml_func(config_data, config_file)
    with pytest.raises(ConfigError, match="Extra inputs are not permitted"):
        load_config(str(config_file))


def test_frictionless_hooks_parsing(tmp_path, dump_yaml_func):
    config_file = tmp_path / "ansel.yaml"
    config_data = {
        "general": {
            "hooks": [
                "wildfire-check",
                {"name": "raven", "run": "send-msg", "allow_failure": False},
            ]
        },
        "repositories": [],
    }
    dump_yaml_func(config_data, config_file)

    config = load_config(str(config_file))

    hooks = config.general.hooks
    assert len(hooks) == 2
    assert isinstance(hooks[0], Hook)
    assert hooks[0].name == "wildfire-check"
    assert hooks[1].name == "raven"
    assert hooks[1].allow_failure is False


def test_github_org_discovery(tmp_path, dump_yaml_func):
    config_file = tmp_path / "ansel.yaml"
    config_data = {
        "general": {"commit_message": "test"},
        "repositories": ["stark-industries/*"],
    }
    dump_yaml_func(config_data, config_file)

    with (
        patch("ansel.github.fetch_repos") as mock_fetch,
        patch("shutil.which") as mock_which,
        patch("ansel.ui.UIManager") as mock_ui_cls,
    ):
        mock_which.return_value = None
        mock_ui = MagicMock()
        mock_ui_cls.return_value = mock_ui
        mock_ui.warning.return_value = "WARNING"
        mock_ui.dim.return_value = "DIM"

        mock_run = ["stark-industries/winterfell", "stark-industries/wall"]
        mock_fetch.return_value = mock_run

        config = load_config(str(config_file))

        assert "stark-industries/winterfell" in config.repositories
        assert "stark-industries/wall" in config.repositories
        assert (
            config.repositories["stark-industries/winterfell"].url
            == "git@github.com:stark-industries/winterfell.git"
        )
        mock_fetch.assert_called_once_with("stark-industries", use_gh_cli=False)
        mock_ui.status.assert_called_with(" found 2 repos")


def test_github_org_discovery_with_gh_cli(tmp_path, dump_yaml_func):
    config_file = tmp_path / "ansel.yaml"
    config_data = {
        "general": {"commit_message": "test", "gh_cli": True},
        "repositories": ["juventus/*"],
    }
    dump_yaml_func(config_data, config_file)

    with (
        patch("ansel.github.fetch_repos") as mock_fetch,
        patch("shutil.which") as mock_which,
        patch("ansel.ui.UIManager") as mock_ui_cls,
    ):
        mock_which.return_value = "/usr/bin/gh"
        mock_ui = MagicMock()
        mock_ui_cls.return_value = mock_ui

        mock_run = ["juventus/allianz"]
        mock_fetch.return_value = mock_run

        config = load_config(str(config_file))

        assert "juventus/allianz" in config.repositories
        mock_fetch.assert_called_once_with("juventus", use_gh_cli=True)
        mock_ui.status.assert_any_call("discovery/juventus: scanning (gh cli)...")


def test_template_selection_logic():
    repo = RepositoryConfig(
        name="iron-throne", url="", groups=["kings-landing", "capital"]
    )

    assert should_apply_template(TemplateConfig(name="t1"), repo) is True
    assert (
        should_apply_template(TemplateConfig(name="t2", groups=["kings-landing"]), repo)
        is True
    )
    assert (
        should_apply_template(TemplateConfig(name="t3", groups=["winterfell"]), repo)
        is False
    )
    assert (
        should_apply_template(TemplateConfig(name="t4", repos=["iron-throne"]), repo)
        is True
    )
    assert (
        should_apply_template(TemplateConfig(name="t5", skip_groups=["capital"]), repo)
        is False
    )
    assert (
        should_apply_template(
            TemplateConfig(name="t6", skip_repos=["iron-throne"]), repo
        )
        is False
    )
    assert (
        should_apply_template(
            TemplateConfig(
                name="t7", groups=["kings-landing"], skip_repos=["iron-throne"]
            ),
            repo,
        )
        is False
    )
