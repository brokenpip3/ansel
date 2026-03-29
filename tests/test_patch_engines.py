def test_regex_patch_engine(tmp_path, regex_engine):
    file_path = tmp_path / "holocron.txt"
    file_path.write_text("Hello Tatooine\nEmpire: Rising")

    ops = [
        {"search": "Tatooine", "replace": "Coruscant"},
        {"search": "Empire: .*", "replace": "Empire: Falling"},
    ]

    modified = regex_engine.apply(file_path, ops, {})
    assert modified is True

    content = file_path.read_text()
    assert "Hello Coruscant" in content
    assert "Empire: Falling" in content


def test_regex_patch_engine_no_change(tmp_path, regex_engine):
    file_path = tmp_path / "jedi-code.txt"
    file_path.write_text("Peace is a lie")

    ops = [{"search": "Sith", "replace": "Jedi"}]

    modified = regex_engine.apply(file_path, ops, {})
    assert modified is False
    assert file_path.read_text() == "Peace is a lie"
