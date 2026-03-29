import difflib


def test_preservation_style_a(tmp_path, yaml_engine):
    content = """jobs:
  trench-run:
    steps:
    - uses: old-force
      with:
        v: 1
"""
    file_path = tmp_path / "a.yaml"
    file_path.write_text(content)

    ops = [
        {"select": "..", "where": {"uses": "old-force"}, "update": {"uses": "new-jedi"}}
    ]
    yaml_engine.apply(file_path, ops, {})

    updated = file_path.read_text()
    diff = list(difflib.unified_diff(content.splitlines(), updated.splitlines()))
    assert (
        len([line for line in diff if line.startswith("-") or line.startswith("+")])
        <= 4
    )


def test_preservation_style_b(tmp_path, yaml_engine):
    content = """jobs:
  match-day:
    steps:
      - uses: del-piero
        with:
          v: 10
"""
    file_path = tmp_path / "b.yaml"
    file_path.write_text(content)

    ops = [
        {"select": "..", "where": {"uses": "del-piero"}, "update": {"uses": "vlahovic"}}
    ]
    yaml_engine.apply(file_path, ops, {})

    updated = file_path.read_text()
    assert "      - uses: vlahovic" in updated
    diff = list(difflib.unified_diff(content.splitlines(), updated.splitlines()))
    assert (
        len([line for line in diff if line.startswith("-") or line.startswith("+")])
        <= 4
    )


def test_preservation_complex_workflow(tmp_path, yaml_engine):
    content = """name: death-star-ops
on:
  red-alert:
jobs:
  attack:
    steps:
      - name: Ignition
        uses: empire/laser-action@v4
        with:
          power: ${{ secrets.KYBER_CRYSTAL }}
"""
    file_path = tmp_path / "complex.yaml"
    file_path.write_text(content)

    ops = [{"select": "..", "where": {"name": "Ignition"}, "update": {"name": "Fire"}}]
    yaml_engine.apply(file_path, ops, {})

    updated = file_path.read_text()
    assert "      - name: Fire" in updated
    assert "        uses: empire/laser-action@v4" in updated
    diff = list(difflib.unified_diff(content.splitlines(), updated.splitlines()))
    assert (
        len([line for line in diff if line.startswith("-") or line.startswith("+")])
        <= 4
    )
