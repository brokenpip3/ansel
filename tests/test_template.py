import pytest

from ansel.config import TemplateConfig
from ansel.exceptions import TemplateError
from ansel.template import apply_template
from ansel.template import merge_vars
from ansel.template import render_template


def test_merge_vars():
    global_vars = {"house": "stark", "motto": "winter is coming"}
    template_vars = {"motto": "fire and blood", "sigil": "dragon"}
    merged = merge_vars(global_vars, template_vars)
    assert merged == {"house": "stark", "motto": "fire and blood", "sigil": "dragon"}


def test_render_template(tmp_path):
    template_file = tmp_path / "dragons.j2"
    template_file.write_text("Hello {{ name }}! {{ missing }}")

    rendered = render_template(template_file, {"name": "Winterfell"})
    assert rendered == "Hello Winterfell! "


def test_render_template_syntax_error(tmp_path):
    template_file = tmp_path / "wildfire.j2"
    template_file.write_text("{{ invalid wildfire }")

    with pytest.raises(TemplateError, match="Syntax error"):
        render_template(template_file, {})


def test_apply_template(tmp_path):
    repo_path = tmp_path / "allianz"
    repo_path.mkdir()

    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    template_file = template_dir / "juve/players.yaml"
    template_file.parent.mkdir()
    template_file.write_text("player: {{ name }}")

    template_cfg = TemplateConfig(
        name="juve/players.yaml", path=str(template_file), vars={"name": "del-piero"}
    )

    apply_template(repo_path, template_cfg, {"team": "juventus"}, "serie-a", "capitano")

    applied_file = repo_path / "juve/players.yaml"
    assert applied_file.exists()
    assert applied_file.read_text() == "player: del-piero"
