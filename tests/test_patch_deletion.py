def test_yaml_delete_key(tmp_path, yaml_engine):
    content = """name: DEATH-STAR-OPS
systems:
  laser:
    firing_sequence:
      - action: target-alderaan
        auth:
          token: tarkin-001
"""
    file_path = tmp_path / "station.yaml"
    file_path.write_text(content)

    ops = [{"where": {"action": "target-*"}, "delete": ["auth"]}]

    yaml_engine.apply(file_path, ops, {})

    updated = file_path.read_text()
    assert "action: target-alderaan" in updated
    assert "auth:" not in updated
    assert "token: tarkin-001" not in updated


def test_yaml_delete_entire_block(tmp_path, yaml_engine):
    content = """team: juventus
players:
  first_team:
    - name: del-piero
      role: legend
    - name: lord-bentner
      role: meme
    - name: vlahovic
      role: striker
"""
    file_path = tmp_path / "team.yaml"
    file_path.write_text(content)

    ops = [
        {
            "select": "players.first_team.*",
            "where": {"name": "lord-bentner"},
            "delete": True,
        }
    ]

    yaml_engine.apply(file_path, ops, {})

    updated = file_path.read_text()
    assert "lord-bentner" not in updated
    assert "meme" not in updated
    assert "\n\n\n" not in updated
    assert "name: vlahovic" in updated


def test_yaml_recursive_glob_selection(tmp_path, yaml_engine):
    content = """
westeros:
  north:
    winterfell:
      lord: bolton
"""
    file_path = tmp_path / "map.yaml"
    file_path.write_text(content)

    ops = [{"select": "**.winterfell", "update": {"lord": "stark"}}]

    yaml_engine.apply(file_path, ops, {})
    assert "lord: stark" in file_path.read_text()


def test_toml_delete_entire_block(tmp_path, toml_engine):
    content = """[alliance]
name = "rebels"
base = "yavin4"

[empire]
spy = "true"
"""
    file_path = tmp_path / "intelligence.toml"
    file_path.write_text(content)

    ops = [{"select": "empire", "delete": True}]

    toml_engine.apply(file_path, ops, {})

    updated = file_path.read_text()
    assert "[empire]" not in updated
    assert "spy =" not in updated
    assert "[alliance]" in updated
