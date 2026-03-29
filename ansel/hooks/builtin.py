import subprocess
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Optional

from ansel.exceptions import AnselError


def find_pre_commit_config(repo_path: Path) -> Optional[Path]:
    for name in [".pre-commit-config.yaml", ".pre-commit-config.yml"]:
        p = repo_path / name
        if p.exists():
            return p
    return None


def run_pre_commit(repo_path: Path, vars_dict: Dict[str, Any]):
    config_path = find_pre_commit_config(repo_path)
    if config_path:
        # Install
        subprocess.run(
            ["pre-commit", "install"],
            cwd=str(repo_path),
            check=True,
            capture_output=True,
            text=True,
        )
        # Run
        subprocess.run(
            ["pre-commit", "run", "--all-files"],
            cwd=str(repo_path),
            check=False,
            capture_output=True,
            text=True,
        )


def run_check_yaml(repo_path: Path, vars_dict: Dict[str, Any]):
    from ruamel.yaml import YAML

    yaml = YAML(typ="safe")
    errors = []
    for ext in ["yaml", "yml"]:
        for p in repo_path.rglob(f"*.{ext}"):
            try:
                with open(p, "r") as f:
                    yaml.load(f)
            except Exception as e:
                errors.append(f"{p.relative_to(repo_path)}: {e}")
    if errors:
        raise AnselError("\n".join(errors))


def run_check_toml(repo_path: Path, vars_dict: Dict[str, Any]):
    import tomlkit

    errors = []
    for p in repo_path.rglob("*.toml"):
        try:
            tomlkit.parse(p.read_text())
        except Exception as e:
            errors.append(f"{p.relative_to(repo_path)}: {e}")
    if errors:
        raise AnselError("\n".join(errors))
