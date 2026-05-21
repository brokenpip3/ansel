import json

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
        {"select": "station.defenses", "update": ["c", "d"]}
    ]

    modified = json_engine.apply(file_path, ops, {})
    assert modified is True

    data = json.loads(file_path.read_text())
    assert data["station"]["name"] == "starkiller-base"
    assert data["station"]["defenses"] == ["c", "d"]
