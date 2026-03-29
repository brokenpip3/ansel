import difflib
from pathlib import Path
from typing import Optional


def compute_diff(
    rendered_content: str,
    repo_file_path: Path,
    template_name: str,
    original_content: Optional[str] = None,
    style: bool = False,
    skip_headers: bool = True,
) -> Optional[str]:
    if original_content is not None:
        current_content = original_content
    elif not repo_file_path.exists():
        # Entirely new file
        current_content = ""
    else:
        current_content = repo_file_path.read_text()

    if current_content == rendered_content:
        return None

    diff = list(
        difflib.unified_diff(
            current_content.splitlines(keepends=True),
            rendered_content.splitlines(keepends=True),
            fromfile=f"a/{template_name}",
            tofile=f"b/{template_name}",
        )
    )

    if style:
        from ansel.ui import UIManager

        ui = UIManager()
        styled_diff = []
        for line in diff:
            # Skip diff headers AND chunk headers (@@)
            if skip_headers and (
                line.startswith("---")
                or line.startswith("+++")
                or line.startswith("@@")
            ):
                continue

            if line.startswith("+"):
                styled_diff.append(ui.added(line))
            elif line.startswith("-"):
                styled_diff.append(ui.removed(line))
            else:
                # Context lines are grey (dimmed white)
                styled_diff.append(ui.dim(line))
        return "".join(styled_diff)

    if skip_headers:
        diff = [
            line
            for line in diff
            if not (
                line.startswith("---")
                or line.startswith("+++")
                or line.startswith("@@")
            )
        ]

    return "".join(diff)
