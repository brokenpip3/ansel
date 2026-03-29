import pytest

from ansel.template import apply_patch
from ansel.template import get_builtin_vars
from ansel.template import render_string


def test_builtin_vars():
    vars = get_builtin_vars("death-star", "trench-run")
    assert vars["repo_name"] == "death-star"
    assert vars["branch"] == "trench-run"
    assert "date" in vars


def test_render_string():
    rendered = render_string("hello {{ name }}", {"name": "tatooine"})
    assert rendered == "hello tatooine"


def test_apply_patch(tmp_path):
    target = tmp_path / "falcon.txt"
    target.write_text("hyperdrive: broken\ncaptain: old\n")

    patches = [
        {"search": "hyperdrive: .*", "replace": "hyperdrive: {{ status }}"},
        {"search": "captain: old", "replace": "captain: han-solo"},
    ]

    vars_dict = {"status": "fixed"}
    apply_patch(target, patches, vars_dict)

    content = target.read_text()
    assert "hyperdrive: fixed" in content
    assert "captain: han-solo" in content


def test_apply_patch_not_found(tmp_path):
    target = tmp_path / "missing-droid.txt"
    with pytest.raises(Exception, match="Patch target not found"):
        apply_patch(target, [], {})
