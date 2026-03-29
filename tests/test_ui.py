import os
from unittest.mock import patch

from ansel.ui import UIManager


def test_ui_color_suppression():
    with patch.dict(os.environ, {"ANSEL_NO_COLOR": "1"}):
        ui = UIManager()
        assert ui.use_color is False


@patch("sys.stdout.isatty", return_value=True)
@patch("sys.stdout.write")
@patch("click.echo")
def test_ui_line_counting_and_overwriting(mock_echo, mock_write, mock_isatty):
    ui = UIManager()
    ui.use_color = False

    ui.log_repo_start("allianz-stadium")
    assert ui.current_repo_lines == 1

    ui.log_repo_step("warming up")
    assert ui.current_repo_lines == 2

    ui.log_repo_step("match started", overwrite=True)
    assert ui.current_repo_lines == 2
    mock_write.assert_any_call("\033[A\r\033[K  ├─ match started\n")

    ui.indent_block("del piero\nvlahovic\nchiesa", prefix="| ")
    assert ui.current_repo_lines == 5

    ui.log_repo_done("allianz-stadium", "victory")
    mock_write.assert_any_call("\033[5A\r\033[K✓ allianz-stadium (victory)\033[5B\r")


@patch("sys.stdout.isatty", return_value=True)
@patch("sys.stdout.write")
@patch("click.echo")
@patch("click.prompt", return_value="y")
def test_ui_prompt_counting(mock_prompt, mock_echo, mock_write, mock_isatty):
    ui = UIManager()
    ui.use_color = False
    ui.log_repo_start("death-star")
    ui.prompt("fire weapon?")
    assert ui.current_repo_lines == 2
    ui.log_repo_done("death-star", "destroyed")
    mock_write.assert_any_call("\033[2A\r\033[K✓ death-star (destroyed)\033[2B\r")


@patch("click.echo")
def test_ui_nesting(mock_echo):
    ui = UIManager()
    ui.use_color = False
    ui.log_repo_step("the-force", indent=1)
    mock_echo.assert_called_with("  │ ├─ the-force", err=False, nl=True)


def test_ui_status_style():
    ui = UIManager()
    # Mock style to verify parameters
    with patch.object(ui, "style", wraps=ui.style) as mock_style:
        ui.status("test")
        mock_style.assert_called_with("test", fg="bright_black")


@patch("click.echo")
def test_ui_log_repo_step_uses_status(mock_echo):
    ui = UIManager()
    with patch.object(ui, "status", return_value="STATUS") as mock_status:
        ui.log_repo_step("cloning")
        # Verify status was called for the branch symbol
        assert mock_status.called


def test_ui_log_repo_done_styles():
    ui = UIManager()
    with patch.object(ui, "success", wraps=ui.success) as mock_success, patch.object(
        ui, "warn", wraps=ui.warn
    ) as mock_warn:
        ui.log_repo_done("repo", "updated")
        assert mock_success.called
        assert not mock_warn.called
        mock_success.reset_mock()
        mock_warn.reset_mock()

        ui.log_repo_done("repo", "skipped")
        assert mock_warn.called
        assert not mock_success.called
        mock_success.reset_mock()
        mock_warn.reset_mock()

        ui.log_repo_done("repo", "unchanged")
        assert mock_warn.called
        assert not mock_success.called
