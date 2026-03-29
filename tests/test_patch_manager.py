from ansel.config import TemplateConfig


def test_patch_manager_globs(tmp_path, patch_manager):
    (tmp_path / "schematics").mkdir()
    f1 = tmp_path / "schematics/exhaust-port.yml"
    f2 = tmp_path / "schematics/shield-gen.yml"
    f1.write_text("vulnerability: low")
    f2.write_text("vulnerability: none")

    config = TemplateConfig(
        name="death-star-blueprints",
        type="patch",
        include=["schematics/*.yml"],
        operations=[{"engine": "yaml", "select": "..", "update": {"inspected": True}}],
    )

    modified_files = patch_manager.apply(tmp_path, config, {})
    assert len(modified_files) == 2
    assert "inspected: true" in f1.read_text().lower()
    assert "inspected: true" in f2.read_text().lower()
