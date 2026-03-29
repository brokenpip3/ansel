import os
import sys

import click


class UIManager:
    ROOT = "◌"
    BRANCH = "  ├─"
    LAST_BRANCH = "  └─"
    PIPE = "  │ "
    SUCCESS = "✓"
    FAILURE = "✗"

    def __init__(self):
        self.use_color = self._should_use_color()
        # Tracks lines printed since the last log_repo_start
        self.current_repo_lines = 0

    def _should_use_color(self) -> bool:
        if os.environ.get("ANSEL_NO_COLOR"):
            return False
        if os.environ.get("NO_COLOR"):
            return False
        if os.environ.get("TERM") == "dumb":
            return False
        return sys.stdout.isatty()

    def style(self, text: str, **kwargs) -> str:
        if not self.use_color:
            return text
        return click.style(text, **kwargs)

    def echo(self, text: str, err: bool = False, nl: bool = True):
        if not err:
            # Count actual lines being added.
            # We count newlines in text + 1 for the implicit newline if nl=True
            self.current_repo_lines += text.count("\n") + (1 if nl else 0)
        click.echo(text, err=err, nl=nl)

    def prompt(self, text: str, **kwargs) -> str:
        # Prompt prints the question line.
        # After user hits Enter, terminal cursor is one line below the prompt.
        # Total distance added to repo block: 1 line.
        self.current_repo_lines += 1
        return click.prompt(text, **kwargs)

    def success(self, text: str) -> str:
        return self.style(text, fg="green")

    def added(self, text: str) -> str:
        return self.style(text, fg="green", dim=True)

    def removed(self, text: str) -> str:
        return self.style(text, fg="red", dim=True)

    def warn(self, text: str) -> str:
        return self.style(text, fg="yellow")

    def error(self, text: str) -> str:
        return self.style(text, fg="red", bold=True)

    def header(self, text: str) -> str:
        return self.style(text, bold=True)

    def dim(self, text: str) -> str:
        return self.style(text, fg="white", dim=True)

    def status(self, text: str) -> str:
        return self.style(text, fg="bright_black")

    def log_repo_start(self, repo_name: str):
        # Reset counter for new repo block
        self.current_repo_lines = 0
        self.echo(f"{self.ROOT} {repo_name}")

    def log_repo_step(
        self,
        status: str,
        is_last: bool = False,
        overwrite: bool = False,
        indent: int = 0,
    ):
        if indent == 0:
            prefix = self.LAST_BRANCH if is_last else self.BRANCH
            styled_prefix = self.status(prefix)
        else:
            parent_pipe = self.status(self.PIPE)
            child_symbol = self.LAST_BRANCH if is_last else self.BRANCH
            styled_prefix = f"{parent_pipe}{self.status(child_symbol[2:])}"

        if overwrite and sys.stdout.isatty():
            # \033[A moves UP, \r moves to START, \033[K CLEARS line
            # We use sys.stdout.write directly to avoid echo() double-counting
            sys.stdout.write(f"\033[A\r\033[K{styled_prefix} {status}\n")
            sys.stdout.flush()
        else:
            self.echo(f"{styled_prefix} {status}")

    def log_repo_done(self, repo_name: str, message: str):
        is_warn = any(word in message.lower() for word in ["skipped", "unchanged"])
        style_fn = self.warn if is_warn else self.success

        if sys.stdout.isatty() and self.current_repo_lines > 0:
            # Move up exactly current_repo_lines to reach the ROOT line
            n = self.current_repo_lines
            # Move up, CR, Clear line, Write success line, Move back down, CR
            sys.stdout.write(
                f"\033[{n}A\r\033[K{self.SUCCESS} {repo_name} {style_fn('(' + message + ')')}\033[{n}B\r"
            )
            sys.stdout.flush()
        else:
            # Non-TTY fallback: don't repeat repo name if we can help it,
            # but we need to show the final status.
            self.echo(f"{self.SUCCESS} {style_fn(repo_name + ': ' + message)}")

    def log_repo_fail(self, repo_name: str, message: str):
        if sys.stdout.isatty() and self.current_repo_lines > 0:
            n = self.current_repo_lines
            sys.stdout.write(
                f"\033[{n}A\r\033[K{self.FAILURE} {repo_name} {self.error(message)}\033[{n}B\r"
            )
            sys.stdout.flush()
        else:
            self.echo(f"{self.FAILURE} {self.error(repo_name + ': ' + message)}")

    def indent_block(self, text: str, prefix: str = "    ") -> int:
        if not text:
            return 0
        lines = text.splitlines()
        styled_prefix = self.status(prefix)
        for line in lines:
            self.echo(f"{styled_prefix}{line}")
        return len(lines)
