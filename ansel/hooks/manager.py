import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from ansel.exceptions import AnselError


@dataclass
class Hook:
    name: str
    type: str  # 'builtin', 'config', 'discovered'
    run: Union[str, Callable]
    allow_failure: bool = True
    description: Optional[str] = None


class HookRegistry:
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.builtins: Dict[str, Hook] = {}
        self._register_builtins()

    def _register_builtins(self):
        from ansel.hooks.builtin import run_pre_commit, run_check_yaml, run_check_toml

        self.builtins["pre-commit"] = Hook(
            name="pre-commit",
            type="builtin",
            run=run_pre_commit,
            allow_failure=True,
            description="Installs and runs pre-commit hooks on all files",
        )
        self.builtins["check-yaml"] = Hook(
            name="check-yaml",
            type="builtin",
            run=run_check_yaml,
            description="Validates syntax of all YAML files in the repository",
        )
        self.builtins["check-toml"] = Hook(
            name="check-toml",
            type="builtin",
            run=run_check_toml,
            description="Validates syntax of all TOML files in the repository",
        )

    def get_discovered_hooks(self) -> Dict[str, Hook]:
        discovered = {}
        hooks_dir = self.config_dir / "hooks"
        if hooks_dir.is_dir():
            for item in hooks_dir.iterdir():
                if item.is_file():
                    is_exec = os.access(item, os.X_OK)
                    has_ext = item.suffix in [".sh", ".py", ".bash"]
                    if is_exec or has_ext:
                        discovered[item.name] = Hook(
                            name=item.name,
                            type="discovered",
                            run=f"!cmd {item.absolute()}",
                            description=f"Script found in {hooks_dir}",
                        )
        return discovered

    def get_all_hooks(self, config_hooks: List[Hook] = None) -> Dict[str, Hook]:
        all_hooks = {**self.builtins, **self.get_discovered_hooks()}
        if config_hooks:
            for h in config_hooks:
                all_hooks[h.name] = h
        return all_hooks

    def run_pipeline(
        self,
        repo_path: Path,
        hooks: List[Hook],
        vars_dict: Dict[str, Any],
        log_fn: Callable,
        indent: int = 0,
    ):
        from ansel.template import render_string
        import subprocess

        all_available = self.get_all_hooks()

        from ansel.ui import UIManager

        ui = UIManager()  # Fallback or just use it to style

        for i, h_def in enumerate(hooks):
            actual_hook = all_available.get(h_def.name, h_def)
            # Prioritize registry settings if name matches
            allow_failure = (
                actual_hook.allow_failure
                if h_def.name in all_available
                else h_def.allow_failure
            )
            is_last = i == len(hooks) - 1

            log_fn(
                f"hook/{actual_hook.name}: {ui.status('running')}",
                is_last=is_last,
                indent=indent,
            )

            success = False
            error_msg = ""
            try:
                if isinstance(actual_hook.run, str):
                    cmd = render_string(actual_hook.run, vars_dict)
                    if cmd.startswith("!cmd "):
                        cmd = cmd[5:]

                    subprocess.run(
                        cmd,
                        shell=True,
                        cwd=str(repo_path),
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    success = True
                elif callable(actual_hook.run):
                    actual_hook.run(repo_path, vars_dict)
                    success = True
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr or str(e)
            except Exception as e:
                error_msg = str(e)

            if success:
                log_fn(
                    f"hook/{actual_hook.name}: {ui.success('passed')}",
                    is_last=is_last,
                    overwrite=True,
                    indent=indent,
                )
            else:
                status = f"failed: {error_msg.strip()}"
                if allow_failure:
                    log_fn(
                        f"hook/{actual_hook.name}: {ui.warn(status)} {ui.status('(ignored)')}",
                        is_last=is_last,
                        overwrite=True,
                        indent=indent,
                    )
                else:
                    log_fn(
                        f"hook/{actual_hook.name}: {ui.error(status)}",
                        is_last=is_last,
                        overwrite=True,
                        indent=indent,
                    )
                    raise AnselError(f"Hook {actual_hook.name} failed and is blocking.")
