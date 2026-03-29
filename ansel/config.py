import os
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict
from ruamel.yaml import YAML

from ansel.exceptions import ConfigError
from ansel.hooks import Hook


def parse_hooks(hooks_data: Any) -> List[Hook]:
    if not hooks_data:
        return []
    if isinstance(hooks_data, str):
        hooks_data = [hooks_data]

    parsed = []
    for h in hooks_data:
        if isinstance(h, str):
            parsed.append(Hook(name=h, type="config", run=h))
        elif isinstance(h, dict):
            # Ensure name and type exist for the dataclass
            name = h.get("name", "anonymous")
            run = h.get("run", "")
            h_type = h.get("type", "config")
            allow_failure = h.get("allow_failure", True)
            description = h.get("description")
            parsed.append(
                Hook(
                    name=name,
                    type=h_type,
                    run=run,
                    allow_failure=allow_failure,
                    description=description,
                )
            )
        elif isinstance(h, Hook):
            parsed.append(h)
    return parsed


class GeneralConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ANSEL_", extra="forbid")

    commit_message: str = "update via ansel"
    default_branch: str = "main"
    workdir: Optional[str] = None
    vars: Dict[str, Any] = Field(default_factory=dict)
    gh_org: Optional[str] = None
    gitlab_org: Optional[str] = None
    gh_cli: bool = False
    use_pre_commit: bool = False
    hooks: List[Hook] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def apply_env_overrides(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # Manually check for ANSEL_ overrides to ensure they win over YAML
        for field_name in cls.model_fields:
            env_key = f"ANSEL_{field_name.upper()}"
            env_val = os.environ.get(env_key)
            if env_val is not None:
                data[field_name] = env_val

        # Handle boolean conversion for use_pre_commit specifically
        val = data.get("use_pre_commit")
        if isinstance(val, str):
            data["use_pre_commit"] = val.lower() in ("true", "1", "yes", "on")

        # Parse hooks
        if "hooks" in data:
            data["hooks"] = parse_hooks(data["hooks"])

        return data


class RepositoryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    url: str
    groups: List[str] = Field(default_factory=list)
    branch: Optional[str] = None
    hooks: List[Hook] = Field(default_factory=list)

    # Pre-processing fields (allowed for validation but not used in core logic)
    gh: Optional[str] = None
    gitlab: Optional[str] = None
    group: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def resolve_shortcuts(cls, data: Any) -> Any:
        if isinstance(data, str):
            # Compact list handled at parent level (AnselConfig)
            return data

        if not isinstance(data, dict):
            return data

        if "hooks" in data:
            data["hooks"] = parse_hooks(data["hooks"])

        return data


class TemplateConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    path: Optional[str] = None
    description: Optional[str] = None
    vars: Dict[str, Any] = Field(default_factory=dict)
    type: str = "template"
    patches: List[Dict[str, str]] = Field(default_factory=list)
    groups: List[str] = Field(default_factory=list)
    repos: List[str] = Field(default_factory=list)
    skip_groups: List[str] = Field(default_factory=list)
    skip_repos: List[str] = Field(default_factory=list)
    include: List[str] = Field(default_factory=list)
    operations: List[Dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def ensure_lists(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        for field_name in ["groups", "repos", "skip_groups", "skip_repos", "include"]:
            val = data.get(field_name)
            if val is not None and isinstance(val, str):
                data[field_name] = [val]
        return data


class AnselConfig(BaseModel):
    general: GeneralConfig
    repositories: Dict[str, RepositoryConfig]
    templates: Dict[str, TemplateConfig]
    config_dir: Path

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def parse_sections(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # Check for skip_discovery
        skip_discovery = data.pop("_skip_discovery", False)

        general_data = data.get("general", {})
        gh_org = general_data.get("gh_org") or os.environ.get("ANSEL_GH_ORG")
        gl_org = general_data.get("gitlab_org") or os.environ.get("ANSEL_GITLAB_ORG")
        gh_cli = str(general_data.get("gh_cli", os.environ.get("ANSEL_GH_CLI", "false"))).lower() == "true"

        repos_input = data.get("repositories", {})
        repos_dict = {}
        if isinstance(repos_input, list):
            for item in repos_input:
                if isinstance(item, str):
                    if item.endswith("/*"):
                        if skip_discovery:
                            continue
                        # Wildcard discovery
                        org_name = item[:-2]
                        import shutil
                        from ansel.github import fetch_repos

                        try:
                            from ansel.ui import UIManager

                            ui = UIManager()
                            use_gh = gh_cli and bool(shutil.which("gh"))
                            mode = "gh cli" if use_gh else "public rest api"
                            ui.echo(
                                ui.status(f"discovery/{org_name}: scanning ({mode})..."),
                                nl=False,
                            )
                            discovered = fetch_repos(org_name, use_gh_cli=use_gh)
                            ui.echo(ui.status(f" found {len(discovered)} repos"))
                            for d in discovered:
                                repos_dict[d] = {}
                        except Exception as e:
                            raise ValueError(
                                f"Failed to discover repositories for '{org_name}': {e}"
                            )
                    else:
                        repos_dict[item] = {}
                elif isinstance(item, dict):
                    repos_dict.update(item)
        else:
            repos_dict = repos_input

        final_repos = {}
        for key, repo_data in repos_dict.items():
            name = key
            url = repo_data.get("url")
            gh = repo_data.get("gh")
            gitlab = repo_data.get("gitlab")

            # Validate URL definition count
            if sum(x is not None for x in [url, gh, gitlab]) > 1:
                raise ValueError(f"Multiple URL definitions for repository '{key}'")

            if gh:
                if "/" not in gh and gh_org:
                    gh = f"{gh_org}/{gh}"
                url = _resolve_shortcut("github.com", gh)
            elif gitlab:
                if "/" not in gitlab and gl_org:
                    gitlab = f"{gl_org}/{gitlab}"
                url = _resolve_shortcut("gitlab.com", gitlab)
            elif url is None:
                implicit_gh = key
                if "/" not in implicit_gh and gh_org:
                    implicit_gh = f"{gh_org}/{implicit_gh}"
                if "/" in implicit_gh:
                    url = f"git@github.com:{implicit_gh}.git"
                    name = implicit_gh.split("/")[-1]
                else:
                    raise ValueError(f"Missing URL for repository '{key}'")

            repo_data["name"] = name
            repo_data["url"] = url
            repo_data["groups"] = _parse_groups(repo_data)
            final_repos[key] = repo_data

        data["repositories"] = final_repos

        # 2. Parse Templates
        templates_input = data.get("templates", {})
        templates_dict = {}
        if isinstance(templates_input, list):
            for item in templates_input:
                if isinstance(item, str):
                    templates_dict[item] = {}
                elif isinstance(item, dict):
                    templates_dict.update(item)
        else:
            templates_dict = templates_input

        final_templates = {}
        for name, t_data in templates_dict.items():
            t_data["name"] = name
            final_templates[name] = t_data

        data["templates"] = final_templates
        return data


def detect_url_scheme(url: str) -> str:
    if url.startswith(("git@", "ssh://")):
        return "ssh"
    if url.startswith("https://"):
        return "https"
    if "@" in url and ":" in url:
        return "ssh"
    return "unknown"


def find_config_file(start_path: Path = Path.cwd()) -> Path:
    current = start_path.absolute()
    while True:
        config_file = current / "ansel.yaml"
        if config_file.exists():
            return config_file
        if current.parent == current:
            break
        current = current.parent
    raise ConfigError("ansel.yaml not found in current or parent directories")


def _resolve_shortcut(domain: str, value: str) -> str:
    # If no protocol specified, default to SSH
    if "://" not in value:
        return f"git@{domain}:{value}.git"

    # Explicit protocol
    if value.startswith("ssh://"):
        path = value[len("ssh://") :]
        return f"git@{domain}:{path}.git"
    elif value.startswith("https://"):
        path = value[len("https://") :]
        return f"https://{domain}/{path}.git"
    else:
        # Fallback for other protocols
        return value


def _parse_groups(repo_data: Dict[str, Any]) -> List[str]:
    groups = []
    if "group" in repo_data:
        groups.append(repo_data["group"])
    if "groups" in repo_data:
        g_input = repo_data["groups"]
        if isinstance(g_input, str):
            groups.append(g_input)
        elif isinstance(g_input, list):
            groups.extend(g_input)
    return list(set(groups))


def should_apply_template(template: TemplateConfig, repo: RepositoryConfig) -> bool:
    if repo.name in template.skip_repos:
        return False

    for g in repo.groups:
        if g in template.skip_groups:
            return False

    if template.repos and repo.name in template.repos:
        return True

    if template.groups:
        for g in repo.groups:
            if g in template.groups:
                return True
        return False  # Had groups but none matched

    if not template.repos and not template.groups:
        return True

    return False


def load_config(
    config_path: Optional[str] = None, skip_discovery: bool = False
) -> AnselConfig:
    if config_path:
        path = Path(config_path).absolute()
        if not path.exists():
            raise ConfigError(f"Config file not found: {config_path}")
    else:
        path = find_config_file()

    yaml_parser = YAML(typ="safe")
    with open(path, "r") as f:
        try:
            data = yaml_parser.load(f) or {}
        except Exception as e:
            raise ConfigError(f"Error parsing YAML: {e}")

    try:
        # Pydantic validation handles environment variables and shortcut logic
        # We inject _skip_discovery into the data to pass it to the validator
        config = AnselConfig.model_validate(
            {**data, "config_dir": str(path.parent), "_skip_discovery": skip_discovery}
        )
    except Exception as e:
        raise ConfigError(f"Configuration error: {e}")

    # Resolve template paths after validation
    config_dir = Path(config.config_dir)
    for t_name, template in config.templates.items():
        if template.path:
            p = Path(template.path)
            if not p.is_absolute():
                template.path = str(config_dir / p)
        else:
            template.path = str(config_dir / "templates" / t_name)

        if not Path(template.path).exists() and template.type == "template":
            raise ConfigError(f"Template not found: {template.path}")

    return config
