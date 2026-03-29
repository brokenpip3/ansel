import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict
from typing import Generator
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import click
from git import Repo

from ansel.browser import open_pr
from ansel.config import load_config
from ansel.config import RepositoryConfig
from ansel.config import should_apply_template
from ansel.config import TemplateConfig
from ansel.diff import compute_diff
from ansel.exceptions import AnselError
from ansel.hooks import Hook
from ansel.repo import clone_or_pull
from ansel.repo import commit_and_push
from ansel.repo import create_branch
from ansel.repo import get_workdir
from ansel.template import (
    apply_template,
)
from ansel.ui import UIManager


class Context:
    def __init__(
        self,
        config_path: Optional[str],
        workdir: Optional[str],
        verbose: bool,
        load: bool = True,
        skip_discovery: bool = False,
    ):
        self.ui = UIManager()
        self.verbose = verbose
        if not load:
            self.config = None
            self.workdir = None
            return

        # Print header before loading anything
        self.ui.echo(self.ui.status(f"ansel v{get_version()} — {MOTTO}"))

        try:
            self.config = load_config(config_path, skip_discovery=skip_discovery)
            self.workdir = get_workdir(self.config.general.workdir, workdir)
        except Exception as e:
            # Pydantic errors can be quite long, we echo them with our error style
            self.ui.echo(self.ui.error(f"Error: {e}"), err=True)
            sys.exit(1)


@dataclass
class Change:
    template_name: str
    rel_path: str
    new_content: str
    original_content: Optional[str] = None


def _generate_changes(
    obj: Context,
    repos: Dict[str, RepositoryConfig],
    templates: Dict[str, TemplateConfig],
) -> Generator[
    Tuple[str, RepositoryConfig, Optional[Repo], Union[List[Change], Exception]],
    None,
    None,
]:
    for repo_name, repo_cfg in repos.items():
        try:
            obj.ui.log_repo_start(repo_name)
            obj.ui.log_repo_step(obj.ui.status("cloning..."), is_last=False)
            default_branch = obj.config.general.default_branch
            repo = clone_or_pull(repo_cfg, obj.workdir, default_branch)
            repo_path = Path(repo.working_tree_dir)

            repo_templates = {
                t_name: t_cfg
                for t_name, t_cfg in templates.items()
                if should_apply_template(t_cfg, repo_cfg)
            }

            if not repo_templates:
                yield repo_name, repo_cfg, repo, []
                continue

            changes = []
            for t_name, t_cfg in repo_templates.items():
                if len(repo_templates) == 1:
                    branch_name = f"ansel/update-{t_name}"
                else:
                    timestamp = int(time.time())
                    branch_name = f"ansel/update-multi-{timestamp}"

                # Resolve potential targets to capture original content
                originals = {}
                includes = t_cfg.include if t_cfg.include else [t_name]
                for pattern in includes:
                    for p in repo_path.glob(pattern):
                        if p.is_file():
                            rel_p = str(p.relative_to(repo_path))
                            originals[rel_p] = p.read_text()

                modified_rel_paths = apply_template(
                    repo_path,
                    t_cfg,
                    obj.config.general.vars,
                    repo_name,
                    branch_name,
                )

                for rel_path in modified_rel_paths:
                    p = repo_path / rel_path
                    new_content = p.read_text()
                    orig = originals.get(rel_path)

                    if new_content != orig:
                        changes.append(
                            Change(
                                template_name=t_name,
                                rel_path=rel_path,
                                new_content=new_content,
                                original_content=orig,
                            )
                        )

            yield repo_name, repo_cfg, repo, changes

        except Exception as e:
            yield repo_name, repo_cfg, None, e


def get_version() -> str:
    import importlib.metadata

    try:
        return importlib.metadata.version("ansel")
    except importlib.metadata.PackageNotFoundError:
        # Fallback for development: try to read from pyproject.toml
        try:
            import tomlkit

            pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
            if pyproject_path.exists():
                data = tomlkit.parse(pyproject_path.read_text())
                return str(data["tool"]["poetry"]["version"])
        except Exception:
            pass
        return "0.0.0-dev"


MOTTO = "don't leave crumbs in the woods"


@click.group(help=f"{MOTTO}")
@click.option("--config", "-f", help="Path to ansel.yaml")
@click.option("--workdir", help="Override workdir")
@click.option("--verbose", "-v", is_flag=True, help="Debug-level logging")
@click.version_option(
    version=get_version(),
    prog_name="ansel",
    message=f"%(prog)s version %(version)s\n{MOTTO}",
)
@click.pass_context
def cli(ctx, config, workdir, verbose):
    if ctx.invoked_subcommand == "version":
        ctx.obj = Context(None, None, verbose, load=False)
        return

    # We don't need repo discovery for templates or builtins
    skip_discovery = ctx.invoked_subcommand in ["templates", "template", "builtins"]
    ctx.obj = Context(config, workdir, verbose, skip_discovery=skip_discovery)


@cli.command(help="Apply all templates to all repos")
@click.option("--dry-run", is_flag=True, help="Alias for diff behavior")
@click.option(
    "--plan", is_flag=True, help="Interactive mode: prompt before every change"
)
@click.option("--group", help="Filter repos by group")
@click.option("--template", "template_filter", help="Filter templates by name")
@click.pass_obj
def sync(
    obj: Context,
    dry_run: bool,
    plan: bool,
    group: Optional[str],
    template_filter: Optional[str],
):
    _do_sync(obj, dry_run, plan, group, template_filter)


@cli.command(help="List all builtin hooks and variables")
@click.pass_obj
def builtins(obj: Context):
    from ansel.hooks import HookRegistry

    registry = HookRegistry(obj.config.config_dir)
    all_hooks = registry.get_all_hooks(obj.config.general.hooks)

    headers = ["NAME", "TYPE", "DESCRIPTION"]
    rows = []

    for name, h in all_hooks.items():
        rows.append(
            [
                name,
                "hook",
                h.description
                or (h.run if isinstance(h.run, str) else "python callable"),
            ]
        )

    vars_list = [
        ["repo_name", "var", "Name of the current repository"],
        ["branch", "var", "Name of the branch being created"],
        ["repo_path", "var", "Local absolute path to the repository"],
        ["date", "var", "Current date (YYYY-MM-DD)"],
        ["env.*", "var", "Any environment variable (e.g. env.HOME)"],
    ]
    rows.extend(vars_list)
    rows.sort(key=lambda x: (x[1], x[0]))
    _print_table(obj.ui, headers, rows)


@cli.command()
@click.pass_obj
def version(obj: Context):
    """Show the current version of Ansel."""
    obj.ui.echo(f"ansel version {get_version()}")
    obj.ui.echo(obj.ui.status(MOTTO))


@cli.group(help="Manage repositories", invoke_without_command=True)
@click.pass_context
def repos(ctx):
    if ctx.invoked_subcommand is None:
        ctx.invoke(repos_list)


@cli.group(
    name="repo", help="Alias for repos", invoke_without_command=True, hidden=True
)
@click.pass_context
def repo_alias(ctx):
    if ctx.invoked_subcommand is None:
        ctx.invoke(repos_list)


def _print_table(ui: UIManager, headers: List[str], rows: List[List[str]]):
    ui.echo("")  # Newline before table
    if not rows:
        styled_headers = [ui.header(h) for h in headers]
        ui.echo("   ".join(styled_headers))
        return

    import shutil

    term_width = shutil.get_terminal_size((80, 20)).columns

    # Calculate max width for each column
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(str(val)))

    # Ensure total width doesn't exceed terminal width if possible
    # We add 3 spaces of padding between columns
    padding = 3

    header_line = ""
    for i, h in enumerate(headers):
        header_line += ui.header(f"{h:<{widths[i] + padding}}")
    ui.echo(header_line.rstrip())

    for row in rows:
        line = ""
        for i, val in enumerate(row):
            line += f"{str(val):<{widths[i] + padding}}"
        ui.echo(line.rstrip()[:term_width])


@click.command(name="list")
@click.pass_obj
def repos_list(obj: Context):
    headers = ["NAME", "URL", "GROUPS", "BRANCH"]
    rows = []
    for name, repo in obj.config.repositories.items():
        rows.append(
            [
                name,
                repo.url,
                ",".join(repo.groups) if repo.groups else "-",
                repo.branch or obj.config.general.default_branch,
            ]
        )
    _print_table(obj.ui, headers, rows)


repos.add_command(repos_list)
repo_alias.add_command(repos_list)


@cli.group(help="Manage templates", invoke_without_command=True)
@click.pass_context
def templates(ctx):
    if ctx.invoked_subcommand is None:
        ctx.invoke(templates_list)


@cli.group(
    name="template",
    help="Alias for templates",
    invoke_without_command=True,
    hidden=True,
)
@click.pass_context
def template_alias(ctx):
    if ctx.invoked_subcommand is None:
        ctx.invoke(templates_list)


@click.command(name="list")
@click.pass_obj
def templates_list(obj: Context):
    headers = ["NAME", "DESCRIPTION", "GROUPS", "REPOS", "VARS"]
    rows = []
    for name, template in obj.config.templates.items():
        rows.append(
            [
                name,
                template.description or "-",
                ",".join(template.groups) if template.groups else "*",
                ",".join(template.repos) if template.repos else "*",
                str(len(template.vars)),
            ]
        )
    _print_table(obj.ui, headers, rows)


templates.add_command(templates_list)
template_alias.add_command(templates_list)


def _filter_repos(
    repos: Dict[str, RepositoryConfig], group: Optional[str]
) -> Dict[str, RepositoryConfig]:
    if not group:
        return repos
    return {n: r for n, r in repos.items() if group in r.groups}


def _filter_templates(
    templates: Dict[str, TemplateConfig], template_filter: Optional[str]
) -> Dict[str, TemplateConfig]:
    if not template_filter:
        return templates
    if template_filter not in templates:
        raise AnselError(f"Template not found: {template_filter}")
    return {template_filter: templates[template_filter]}


def _prompt_user(ui: UIManager, repo_name: str, change: Change) -> str:
    diff_output = compute_diff(
        change.new_content,
        Path("__dummy__"),
        change.rel_path,
        original_content=change.original_content,
        style=ui.use_color,
    )

    if diff_output:
        ui.log_repo_step(
            f"planned: {ui.header(change.rel_path)} {ui.success('changed')}",
            is_last=False,
        )
        ui.indent_block(diff_output, prefix=ui.PIPE)
    else:
        ui.log_repo_step(
            f"planned: {ui.header(change.rel_path)} {ui.warn('unchanged')}",
            is_last=False,
        )

    while True:
        prompt_text = (
            f"{ui.status(ui.BRANCH)} {ui.header(f'apply {change.rel_path}?')} [y,n,a,q,?]"
        )
        choice = ui.prompt(
            prompt_text,
            type=str,
            default="y",
            show_choices=False,
        ).lower()

        if choice in ["y", "n", "a", "q"]:
            return choice
        if choice == "?":
            ui.echo("y: apply this change")
            ui.echo("n: skip this change")
            ui.echo("a: apply this and all subsequent changes without prompting")
            ui.echo("q: quit immediately")
        else:
            ui.echo(f"Invalid choice: {choice}")


def _do_sync(
    obj: Context,
    dry_run: bool,
    plan: bool,
    group: Optional[str],
    template_filter: Optional[str],
):
    stats = {
        "repos": {"total": 0, "applied": 0, "failed": 0},
        "files": {"total": 0, "applied": 0},
    }
    apply_all = False

    from ansel.hooks import HookRegistry

    registry = HookRegistry(obj.config.config_dir)

    try:
        repos_dict = _filter_repos(obj.config.repositories, group)
        templates_dict = _filter_templates(obj.config.templates, template_filter)
    except AnselError as e:
        obj.ui.echo(obj.ui.error(f"Error: {e}"), err=True)
        sys.exit(1)

    stats["repos"]["total"] = len(repos_dict)

    for repo_name, repo_cfg, repo, changes_or_err in _generate_changes(
        obj, repos_dict, templates_dict
    ):
        try:
            if isinstance(changes_or_err, Exception):
                raise changes_or_err

            all_changes = changes_or_err

            if not all_changes:
                obj.ui.log_repo_step(obj.ui.warn("unchanged"), is_last=True)
                obj.ui.log_repo_done(repo_name, "unchanged")
                continue

            if len(all_changes) == 1:
                branch_name = f"ansel/update-{all_changes[0].template_name}"
            else:
                timestamp = int(time.time())
                branch_name = f"ansel/update-multi-{timestamp}"

            # Prepare hook pipeline
            hook_pipeline = []
            if obj.config.general.use_pre_commit:
                hook_pipeline.append(
                    Hook(name="pre-commit", type="builtin", run="pre-commit")
                )

            hook_pipeline.extend(obj.config.general.hooks)
            hook_pipeline.extend(repo_cfg.hooks)

            if dry_run or (plan and not apply_all):
                # Resolve variables for hooks
                from ansel.template import merge_vars, get_builtin_vars, resolve_vars

                raw_vars = merge_vars(obj.config.general.vars, {})
                raw_vars.update(get_builtin_vars(repo_name, branch_name))
                vars_dict = resolve_vars(raw_vars, Path(repo.working_tree_dir))

                if hook_pipeline:
                    obj.ui.log_repo_step(obj.ui.status("planning hooks"), is_last=False)
                    registry.run_pipeline(
                        Path(repo.working_tree_dir),
                        hook_pipeline,
                        vars_dict,
                        obj.ui.log_repo_step,
                        indent=1,
                    )
                    # Re-read changes after hooks might have modified files
                    for c in all_changes:
                        p = Path(repo.working_tree_dir) / c.rel_path
                        if p.exists():
                            c.new_content = p.read_text()

            if dry_run:
                obj.ui.log_repo_step(obj.ui.status("planning changes"), is_last=False)
                for i, change in enumerate(all_changes):
                    is_last = i == len(all_changes) - 1
                    diff_output = compute_diff(
                        change.new_content,
                        Path("__dummy__"),
                        change.rel_path,
                        original_content=change.original_content,
                        style=obj.ui.use_color,
                    )
                    if diff_output:
                        obj.ui.log_repo_step(
                            f"{obj.ui.header(change.rel_path)} {obj.ui.success('changed')}",
                            is_last=is_last,
                        )
                        obj.ui.indent_block(diff_output, prefix=obj.ui.PIPE)
                    else:
                        obj.ui.log_repo_step(
                            f"{obj.ui.header(change.rel_path)} {obj.ui.warn('unchanged')}",
                            is_last=is_last,
                        )
                continue

            confirmed_changes = []
            if plan and not apply_all:
                for change in all_changes:
                    choice = _prompt_user(obj.ui, repo_name, change)
                    if choice == "y":
                        confirmed_changes.append(change)
                    elif choice == "a":
                        apply_all = True
                        confirmed_changes.append(change)
                    elif choice == "q":
                        obj.ui.echo(obj.ui.warn("Quitting..."))
                        sys.exit(0)

                if apply_all:
                    already_in = [c.rel_path for c in confirmed_changes]
                    for c in all_changes:
                        if c.rel_path not in already_in:
                            confirmed_changes.append(c)
            else:
                confirmed_changes = all_changes

            if not confirmed_changes:
                obj.ui.log_repo_step(obj.ui.warn("skipped"), is_last=True)
                obj.ui.log_repo_done(repo_name, "skipped")
                continue

            create_branch(repo, branch_name)

            applied_files = list(set([c.rel_path for c in confirmed_changes]))
            stats["files"]["total"] += len(applied_files)
            for i, f in enumerate(applied_files):
                obj.ui.log_repo_step(f"applied: {obj.ui.success(f)}", is_last=False)

            # Run Hooks in sync mode if not already run in plan
            if not (plan and not apply_all):
                if hook_pipeline:
                    from ansel.template import (
                        merge_vars,
                        get_builtin_vars,
                        resolve_vars,
                    )

                    raw_vars = merge_vars(obj.config.general.vars, {})
                    raw_vars.update(get_builtin_vars(repo_name, branch_name))
                    vars_dict = resolve_vars(raw_vars, Path(repo.working_tree_dir))

                    obj.ui.log_repo_step(obj.ui.status("running hooks"), is_last=False)
                    registry.run_pipeline(
                        Path(repo.working_tree_dir),
                        hook_pipeline,
                        vars_dict,
                        obj.ui.log_repo_step,
                        indent=1,
                    )

            pushed = commit_and_push(
                repo,
                obj.config.general.commit_message,
                branch_name,
                applied_files,
            )

            if pushed:
                open_pr(repo_cfg.url, branch_name)
                obj.ui.log_repo_step(obj.ui.success("pr opened"), is_last=True)
                obj.ui.log_repo_done(repo_name, f"updated ({branch_name})")
                stats["repos"]["applied"] += 1
                stats["files"]["applied"] += len(applied_files)
            else:
                obj.ui.log_repo_step(obj.ui.warn("unchanged"), is_last=True)
                obj.ui.log_repo_done(repo_name, "unchanged")

        except Exception as e:
            obj.ui.log_repo_fail(repo_name, f"failed: {e}")
            stats["repos"]["failed"] += 1

    obj.ui.echo("")
    _print_table(
        obj.ui,
        ["RESOURCE", "TOTAL", "APPLIED", "FAILED"],
        [
            [
                "repositories",
                str(stats["repos"]["total"]),
                str(stats["repos"]["applied"]),
                str(stats["repos"]["failed"]),
            ],
            [
                "files",
                str(stats["files"]["total"]),
                str(stats["files"]["applied"]),
                "-",
            ],
        ],
    )

    if not dry_run:
        if stats["repos"]["failed"] > 0:
            sys.exit(1)


if __name__ == "__main__":
    cli()
