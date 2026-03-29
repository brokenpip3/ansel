from ansel.cli import cli


def test_version_command(cli_runner):
    result = cli_runner.invoke(cli, ["version"])
    assert result.exit_code == 0
    assert "ansel version" in result.output
    assert "don't leave crumbs in the woods" in result.output
