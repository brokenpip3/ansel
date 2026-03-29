import runpy
from unittest.mock import patch


def test_main_execution():
    with patch("ansel.cli.cli") as mock_cli:
        runpy.run_module("ansel.__main__", run_name="__main__")
        mock_cli.assert_called_once()
