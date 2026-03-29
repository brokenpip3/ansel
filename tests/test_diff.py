from ansel.diff import compute_diff


def test_diff_changed_file(tmp_path):
    repo_file = tmp_path / "death-star.yaml"
    repo_file.write_text("status: operational\n")

    rendered = "status: destroyed\n"
    diff = compute_diff(rendered, repo_file, "death-star.yaml")

    assert "-status: operational" in diff
    assert "+status: destroyed" in diff
    assert "@@" not in diff


def test_diff_identical_file(tmp_path):
    repo_file = tmp_path / "falcon.yaml"
    repo_file.write_text("hyperdrive: true\n")

    rendered = "hyperdrive: true\n"
    diff = compute_diff(rendered, repo_file, "falcon.yaml")

    assert diff is None


def test_diff_missing_file_in_repo(tmp_path):
    repo_file = tmp_path / "new-hope.yaml"

    rendered = "jedi: returned\n"
    diff = compute_diff(rendered, repo_file, "new-hope.yaml")

    assert "+jedi: returned" in diff


def test_diff_with_original_content(tmp_path):
    repo_file = tmp_path / "winterfell.yaml"
    repo_file.write_text("lord: ramsay\n")

    original = "lord: ned\n"
    rendered = "lord: jon\n"
    diff = compute_diff(
        rendered, repo_file, "winterfell.yaml", original_content=original
    )

    assert "-lord: ned" in diff
    assert "+lord: jon" in diff
    assert "ramsay" not in diff


def test_diff_styled(tmp_path):
    repo_file = tmp_path / "juve.txt"
    repo_file.write_text("scudetto: 36\n")
    rendered = "scudetto: 38\n"

    diff = compute_diff(rendered, repo_file, "juve.txt", style=True)

    assert "36" in diff
    assert "38" in diff
    assert "---" not in diff
    assert "+++" not in diff
    assert "@@" not in diff


def test_diff_with_headers(tmp_path):
    repo_file = tmp_path / "allianz.yaml"
    repo_file.write_text("capacity: 41507\n")
    rendered = "capacity: 42000\n"

    diff = compute_diff(rendered, repo_file, "allianz.yaml", skip_headers=False)

    assert "--- a/allianz.yaml" in diff
    assert "+++ b/allianz.yaml" in diff
    assert "@@" in diff
    assert "-capacity: 41507" in diff
    assert "+capacity: 42000" in diff


def test_diff_styled_with_headers(tmp_path):
    repo_file = tmp_path / "lightsaber.yaml"
    repo_file.write_text("color: blue\n")
    rendered = "color: green\n"

    diff = compute_diff(
        rendered, repo_file, "lightsaber.yaml", style=True, skip_headers=False
    )

    assert "--- a/lightsaber.yaml" in diff
    assert "+++ b/lightsaber.yaml" in diff
    assert "@@" in diff
    assert "blue" in diff
    assert "green" in diff
