import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List

from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import TemplateSyntaxError
from jinja2 import Undefined

from ansel.config import TemplateConfig
from ansel.exceptions import TemplateError
from ansel.patch.manager import PatchManager


def merge_vars(
    global_vars: Dict[str, Any], template_vars: Dict[str, Any]
) -> Dict[str, Any]:
    merged = global_vars.copy()
    merged.update(template_vars)
    return merged


def resolve_vars(raw_vars: Dict[str, Any], repo_path: Path) -> Dict[str, Any]:
    resolved = {}
    context = os.environ.copy()

    pending = raw_vars.copy()

    while pending:
        changed = False
        to_remove = []
        for key, value in pending.items():
            if not isinstance(value, str):
                resolved[key] = value
                context[key] = str(value)
                to_remove.append(key)
                changed = True
                continue

            matches = re.findall(r"\${(.*?)}", value)
            all_resolved = True
            for match in matches:
                if ":-" in match:
                    var_name, _ = match.split(":-", 1)
                else:
                    var_name = match

                if var_name not in context:
                    all_resolved = False
                    break

            if all_resolved:
                interpolated = value
                for m in matches:
                    if ":-" in m:
                        var_name, default_val = m.split(":-", 1)
                        actual_val = context.get(var_name, default_val)
                    else:
                        actual_val = context.get(m, "")
                    interpolated = interpolated.replace(f"${{{m}}}", str(actual_val))

                if interpolated.startswith("!cmd "):
                    command = interpolated[5:]
                    try:
                        result = subprocess.run(
                            command,
                            shell=True,
                            cwd=repo_path,
                            capture_output=True,
                            text=True,
                            check=True,
                        )
                        final_val = result.stdout.strip()
                    except subprocess.CalledProcessError as e:
                        raise TemplateError(f"Command failed: {command} - {e.stderr}")
                else:
                    final_val = interpolated

                resolved[key] = final_val
                context[key] = str(final_val)
                to_remove.append(key)
                changed = True

        for key in to_remove:
            del pending[key]

        if not changed and pending:
            for key, value in pending.items():
                interpolated = value
                matches = re.findall(r"\${(.*?)}", value)
                for m in matches:
                    if ":-" in m:
                        var_name, default_val = m.split(":-", 1)
                        actual_val = context.get(var_name, default_val)
                    else:
                        actual_val = context.get(m, "")
                    interpolated = interpolated.replace(f"${{{m}}}", str(actual_val))

                if interpolated.startswith("!cmd "):
                    command = interpolated[5:]
                    try:
                        result = subprocess.run(
                            command,
                            shell=True,
                            cwd=repo_path,
                            capture_output=True,
                            text=True,
                        )
                        final_val = result.stdout.strip()
                    except Exception:
                        final_val = ""
                else:
                    final_val = interpolated

                resolved[key] = final_val
                context[key] = str(final_val)
            break

    return resolved


def get_builtin_vars(repo_name: str, branch: str) -> Dict[str, str]:
    return {
        "repo_name": repo_name,
        "branch": branch,
        "date": datetime.now().strftime("%Y-%m-%d"),
    }


def render_string(content: str, vars_dict: Dict[str, Any]) -> str:
    try:
        env = Environment(undefined=Undefined)
        template = env.from_string(content)
        return template.render(**vars_dict)
    except Exception as e:
        raise TemplateError(f"Failed to render string: {e}")


def render_template(source_path: Path, vars_dict: Dict[str, Any]) -> str:
    try:
        env = Environment(
            loader=FileSystemLoader(str(source_path.parent)), undefined=Undefined
        )
        template = env.get_template(source_path.name)
        return template.render(**vars_dict)
    except TemplateSyntaxError as e:
        raise TemplateError(f"Syntax error in template {source_path.name}: {e}")
    except Exception as e:
        raise TemplateError(f"Failed to render template {source_path.name}: {e}")


def apply_template(
    repo_path: Path,
    template_cfg: TemplateConfig,
    global_vars: Dict[str, Any],
    repo_name: str,
    branch: str,
) -> List[str]:
    raw_vars = merge_vars(global_vars, template_cfg.vars)
    raw_vars.update(get_builtin_vars(repo_name, branch))
    vars_dict = resolve_vars(raw_vars, repo_path)

    if template_cfg.type == "template":
        dest_path = repo_path / template_cfg.name
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        source_path = Path(template_cfg.path)
        content = render_template(source_path, vars_dict)
        dest_path.write_text(content)
        return [template_cfg.name]
    elif template_cfg.type == "patch":
        if template_cfg.operations:
            manager = PatchManager()
            return manager.apply(repo_path, template_cfg, vars_dict)
        else:
            # Legacy patch support
            dest_path = repo_path / template_cfg.name
            apply_patch(dest_path, template_cfg.patches, vars_dict)
            return [template_cfg.name]

    return []


def apply_patch(
    file_path: Path, patches: List[Dict[str, str]], vars_dict: Dict[str, Any]
):
    if not file_path.exists():
        raise TemplateError(f"Patch target not found: {file_path}")

    content = file_path.read_text()
    for patch in patches:
        search_pattern = render_string(patch["search"], vars_dict)
        replace_pattern = render_string(patch["replace"], vars_dict)
        content = re.sub(search_pattern, replace_pattern, content)

    file_path.write_text(content)
