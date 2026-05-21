import json
import json as json_module
from unittest.mock import patch


def test_json_patch_indentation_preserved(tmp_path, json_engine):
    file_path = tmp_path / "config.json"
    content = '{\n    "base": {\n        "url": "http://localhost"\n    }\n}\n'
    file_path.write_text(content)

    ops = [{"select": "base", "update": {"url": "https://api.example.com"}}]

    modified = json_engine.apply(file_path, ops, {})
    assert modified is True

    updated = file_path.read_text()
    assert '"url": "https://api.example.com"' in updated
    assert '    "base": {' in updated
    assert updated.endswith('}\n')


def test_json_patch_no_indent(tmp_path, json_engine):
    file_path = tmp_path / "config.json"
    content = '{"theme": "dark"}'
    file_path.write_text(content)

    ops = [{"select": "..", "update": {"theme": "light"}}]

    modified = json_engine.apply(file_path, ops, {})
    assert modified is True
    assert file_path.read_text() == '{"theme": "light"}'


def test_json_patch_tabs(tmp_path, json_engine):
    file_path = tmp_path / "config.json"
    content = '{\n\t"theme": "dark"\n}'
    file_path.write_text(content)

    ops = [{"select": "..", "update": {"theme": "light"}}]

    modified = json_engine.apply(file_path, ops, {})
    assert modified is True
    assert file_path.read_text() == '{\n\t"theme": "light"\n}'


def test_json_patch_structural(tmp_path, json_engine):
    file_path = tmp_path / "data.json"
    content = '{"station": {"name": "ds", "defenses": ["a", "b"]}}'
    file_path.write_text(content)

    ops = [
        {"select": "station", "update": {"name": "starkiller-base"}},
        {"select": "station.defenses", "update": ["c", "d"]},
    ]

    modified = json_engine.apply(file_path, ops, {})
    assert modified is True

    data = json.loads(file_path.read_text())
    assert data["station"]["name"] == "starkiller-base"
    assert data["station"]["defenses"] == ["c", "d"]


def test_json_patch_invalid_json(tmp_path, json_engine):
    file_path = tmp_path / "bad.json"
    file_path.write_text("{not json}")
    assert json_engine.apply(file_path, [{}], {}) is False


def test_json_patch_style_exception_fallback(tmp_path, json_engine):
    original_dump = json_module.dump
    call_log = []

    def mock_dump(obj, fp, **kwargs):
        call_log.append(kwargs.get("indent"))
        if len(call_log) <= 4:
            raise TypeError("style failed")
        return original_dump(obj, fp, **kwargs)

    file_path = tmp_path / "config.json"
    file_path.write_text('{"a": 1}')
    ops = [{"select": "..", "update": {"a": 2}}]

    with patch("ansel.patch.engines.json.json.dump", mock_dump):
        modified = json_engine.apply(file_path, ops, {})

    assert modified is True
    assert len(call_log) == 5
    data = json.loads(file_path.read_text())
    assert data["a"] == 2


def test_json_patch_non_string_values(tmp_path, json_engine):
    file_path = tmp_path / "config.json"
    content = json.dumps({"count": 1, "active": False, "data": None})
    file_path.write_text(content)

    ops = [{"select": "..", "update": {"count": 42, "active": True}}]

    modified = json_engine.apply(file_path, ops, {})
    assert modified is True
    data = json.loads(file_path.read_text())
    assert data["count"] == 42
    assert data["active"] is True
    assert data["data"] is None


def test_json_patch_delete_target_dict(tmp_path, json_engine):
    file_path = tmp_path / "config.json"
    content = json.dumps({"keep": "a", "remove": "b"})
    file_path.write_text(content)

    ops = [{"select": "remove", "delete": True}]

    modified = json_engine.apply(file_path, ops, {})
    assert modified is True
    data = json.loads(file_path.read_text())
    assert "remove" not in data
    assert data["keep"] == "a"


def test_json_patch_delete_target_list(tmp_path, json_engine):
    file_path = tmp_path / "config.json"
    content = json.dumps({"items": [{"name": "remove"}, {"name": "keep"}]})
    file_path.write_text(content)

    ops = [{"select": "..", "where": {"name": "remove"}, "delete": True}]

    modified = json_engine.apply(file_path, ops, {})
    assert modified is True
    data = json.loads(file_path.read_text())
    assert data["items"] == [{"name": "keep"}]


def test_json_patch_delete_key_string(tmp_path, json_engine):
    file_path = tmp_path / "config.json"
    content = json.dumps({"outer": {"keep": "a", "remove": "b", "also_keep": "c"}})
    file_path.write_text(content)

    ops = [{"select": "outer", "delete": "remove"}]

    modified = json_engine.apply(file_path, ops, {})
    assert modified is True
    data = json.loads(file_path.read_text())
    assert "remove" not in data["outer"]
    assert data["outer"]["keep"] == "a"


def test_json_patch_delete_key_list(tmp_path, json_engine):
    file_path = tmp_path / "config.json"
    content = json.dumps({"outer": {"a": 1, "b": 2, "c": 3, "d": 4}})
    file_path.write_text(content)

    ops = [{"select": "outer", "delete": ["a", "c"]}]

    modified = json_engine.apply(file_path, ops, {})
    assert modified is True
    data = json.loads(file_path.read_text())
    assert "a" not in data["outer"]
    assert "c" not in data["outer"]
    assert data["outer"] == {"b": 2, "d": 4}


def test_json_patch_recursive_find_list(tmp_path, json_engine):
    file_path = tmp_path / "config.json"
    content = json.dumps(
        {
            "items": [
                {"name": "foo", "value": 1},
                {"name": "bar", "value": 2},
                {"name": "baz", "value": 3},
            ]
        }
    )
    file_path.write_text(content)

    ops = [{"select": "..", "where": {"name": "bar"}, "update": {"value": 99}}]

    modified = json_engine.apply(file_path, ops, {})
    assert modified is True
    data = json.loads(file_path.read_text())
    assert data["items"][1]["value"] == 99


def test_json_patch_doublestar_path(tmp_path, json_engine):
    file_path = tmp_path / "config.json"
    content = json.dumps({"a": {"b": {"c": "old"}}})
    file_path.write_text(content)

    ops = [{"select": "a.**", "where": {"c": "old"}, "update": {"c": "new"}}]

    modified = json_engine.apply(file_path, ops, {})
    assert modified is True
    data = json.loads(file_path.read_text())
    assert data["a"]["b"]["c"] == "new"


def test_json_patch_star_wildcard_dict(tmp_path, json_engine):
    file_path = tmp_path / "config.json"
    content = json.dumps({"items": {"foo": {"val": 1}, "bar": {"val": 2}}})
    file_path.write_text(content)

    ops = [{"select": "items.*", "where": {"val": 2}, "update": {"val": 99}}]

    modified = json_engine.apply(file_path, ops, {})
    assert modified is True
    data = json.loads(file_path.read_text())
    assert data["items"]["bar"]["val"] == 99


def test_json_patch_star_wildcard_list(tmp_path, json_engine):
    file_path = tmp_path / "config.json"
    content = json.dumps({"data": [{"id": 1, "val": "a"}, {"id": 2, "val": "b"}]})
    file_path.write_text(content)

    ops = [{"select": "data.*", "where": {"id": 1}, "update": {"val": "updated"}}]

    modified = json_engine.apply(file_path, ops, {})
    assert modified is True
    data = json.loads(file_path.read_text())
    assert data["data"][0]["val"] == "updated"


def test_json_patch_matches_fnmatch(tmp_path, json_engine):
    file_path = tmp_path / "config.json"
    content = json.dumps({"service": "my-app-backend"})
    file_path.write_text(content)

    ops = [
        {
            "select": "..",
            "where": {"service": "my-app-*"},
            "update": {"service": "renamed"},
        }
    ]

    modified = json_engine.apply(file_path, ops, {})
    assert modified is True
    data = json.loads(file_path.read_text())
    assert data["service"] == "renamed"


def test_json_patch_matches_nondict(tmp_path, json_engine):
    file_path = tmp_path / "config.json"
    content = json.dumps([1, 2, 3])
    file_path.write_text(content)

    ops = [{"select": "..", "where": {"x": "y"}, "update": {"val": 99}}]

    modified = json_engine.apply(file_path, ops, {})
    assert modified is False
