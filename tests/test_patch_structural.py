def test_toml_patch_preserves_comments(tmp_path, toml_engine):
    file_path = tmp_path / "death-star.toml"
    content = """
[station]
name = "death-star" # Super weapon
defenses = [
    "shield-generator",
    "tie-fighters"
]
"""
    file_path.write_text(content)

    ops = [{"select": "station", "update": {"name": "starkiller-base"}}]

    toml_engine.apply(file_path, ops, {})

    updated = file_path.read_text()
    assert 'name = "starkiller-base"' in updated
    assert "# Super weapon" in updated
    assert '"shield-generator"' in updated


def test_yaml_patch_preserves_comments(tmp_path, yaml_engine):
    file_path = tmp_path / "juve.yaml"
    content = """
team: juventus # Serie A giant
players:
  captain:
    - name: del-piero # Legend
"""
    file_path.write_text(content)

    ops = [
        {
            "select": "..",
            "where": {"name": "del-piero*"},
            "update": {"name": "danilo # Current captain"},
        }
    ]

    yaml_engine.apply(file_path, ops, {})

    updated = file_path.read_text()
    assert "name: danilo" in updated
    assert "# Serie A giant" in updated
    assert "# Current captain" in updated


def test_yaml_patch_interpolation(tmp_path, yaml_engine):
    file_path = tmp_path / "stark.yaml"
    content = "lord: old"
    file_path.write_text(content)

    ops = [{"select": "..", "update": {"lord": "{{ new_lord }}"}}]

    vars_dict = {"new_lord": "jon-snow"}
    yaml_engine.apply(file_path, ops, vars_dict)

    assert "lord: jon-snow" in file_path.read_text()


def test_toml_patch_interpolation(tmp_path, toml_engine):
    file_path = tmp_path / "lannister.toml"
    content = 'debt = "unpaid"'
    file_path.write_text(content)

    ops = [{"select": "..", "update": {"debt": "{{ status }}"}}]

    vars_dict = {"status": "paid"}
    toml_engine.apply(file_path, ops, vars_dict)

    assert 'debt = "paid"' in file_path.read_text()


def test_yaml_patch_no_wrapping(tmp_path, yaml_engine):
    file_path = tmp_path / "long-msg.yaml"
    long_val = "force-" * 50
    content = f"message: {long_val}\n"
    file_path.write_text(content)

    ops = [
        {
            "select": "..",
            "where": {"message": "force-*"},
            "update": {"message": "dark-side-" * 50},
        }
    ]

    yaml_engine.apply(file_path, ops, {})
    assert "  " not in file_path.read_text()


def test_yaml_patch_update_comment(tmp_path, yaml_engine):
    file_path = tmp_path / "action.yaml"
    content = "uses: check-shield # v1\n"
    file_path.write_text(content)

    ops = [{"select": "..", "update": {"uses": "destroy-shield # v2"}}]

    yaml_engine.apply(file_path, ops, {})
    assert "uses: destroy-shield # v2" in file_path.read_text()
    assert "# v1" not in file_path.read_text()


def test_yaml_patch_clear_stale_comment(tmp_path, yaml_engine):
    file_path = tmp_path / "action.yaml"
    content = "uses: check-shield # v1\n"
    file_path.write_text(content)

    ops = [{"select": "..", "update": {"uses": "destroy-shield"}}]

    yaml_engine.apply(file_path, ops, {})
    assert "uses: destroy-shield\n" in file_path.read_text()
    assert "# v1" not in file_path.read_text()


def test_yaml_patch_complex_workflow(tmp_path, yaml_engine):
    file_path = tmp_path / "trench-run.yaml"
    content = """name: Trench Run

concurrency:
  group: "death-star"
  cancel-in-progress: true

on:
  push:
    branches:
      - rebel-base

jobs:
  attack:
    name: proton-torpedo
    runs-on: x-wing
    strategy:
      fail-fast: true
      matrix:
        pilot: ["luke", "wedge", "biggs"]
    steps:
    - uses: rebel/force-action @v1
      with:
        token: ${{ secrets.THE_FORCE }}

    - name: Target computer
      uses: empire/shield-action @v4

    - name: Fire
      run: fire-torpedo --pilot ${{ matrix.pilot }}
"""
    file_path.write_text(content)

    ops = [
        {
            "select": "..",
            "where": {"uses": "rebel/force-action*"},
            "update": {"uses": "rebel/jedi-action@v2"},
        }
    ]

    yaml_engine.apply(file_path, ops, {})

    updated = file_path.read_text()
    assert "rebel/jedi-action@v2" in updated
    assert "uses: empire/shield-action @v4" in updated
    assert "    - rebel-base" in updated


def test_yaml_patch_list_replace(tmp_path, yaml_engine):
    file_path = tmp_path / "squad.yaml"
    content = "pilots: [luke, wedge, biggs]"
    file_path.write_text(content)

    ops = [{"select": "pilots", "update": ["han", "chewie"]}]

    yaml_engine.apply(file_path, ops, {})
    content = file_path.read_text()
    assert "han" in content
    assert "chewie" in content
    assert "luke" not in content


def test_yaml_path_find_list_wildcard(tmp_path, yaml_engine):
    file_path = tmp_path / "players.yaml"
    content = """
juventus:
  - id: 10
    name: del-piero
  - id: 7
    name: ronaldo
"""
    file_path.write_text(content)

    ops = [{"select": "juventus.*", "where": {"id": 7}, "update": {"name": "vlahovic"}}]

    yaml_engine.apply(file_path, ops, {})
    assert "name: vlahovic" in file_path.read_text()
    assert "name: del-piero" in file_path.read_text()


def test_toml_patch_list_replace(tmp_path, toml_engine):
    file_path = tmp_path / "inventory.toml"
    content = "items = [1, 2, 3]"
    file_path.write_text(content)

    ops = [{"select": "items", "update": [4, 5]}]

    toml_engine.apply(file_path, ops, {})
    content = file_path.read_text()
    assert "4" in content
    assert "5" in content
    assert "1" not in content
