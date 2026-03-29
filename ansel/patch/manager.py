from pathlib import Path
from typing import Any
from typing import Dict
from typing import List

from ansel.config import TemplateConfig
from ansel.patch.engines.regex import RegexPatchEngine
from ansel.patch.engines.toml import TomlPatchEngine
from ansel.patch.engines.yaml import YamlPatchEngine


class PatchManager:
    def __init__(self):
        self.engines = {
            "yaml": YamlPatchEngine(),
            "toml": TomlPatchEngine(),
            "regex": RegexPatchEngine(),
        }

    def apply(
        self, repo_path: Path, config: TemplateConfig, vars_dict: Dict[str, Any]
    ) -> List[str]:
        modified_files = []

        # If include is missing, we might want to fallback to the template name as path
        # but the new schema expects include.
        includes = config.include if config.include else [config.name]

        target_files = []
        for pattern in includes:
            target_files.extend(list(repo_path.glob(pattern)))

        # Deduplicate
        target_files = list(set(target_files))

        for file_path in target_files:
            if not file_path.is_file():
                continue

            # Group operations by engine
            ops_by_engine: Dict[str, List[Dict[str, Any]]] = {}
            for op in config.operations:
                engine_name = op.get("engine", "yaml")
                if engine_name not in ops_by_engine:
                    ops_by_engine[engine_name] = []
                ops_by_engine[engine_name].append(op)

            file_modified = False
            for engine_name, ops in ops_by_engine.items():
                engine = self.engines.get(engine_name)
                if engine and engine.apply(file_path, ops, vars_dict):
                    file_modified = True

            if file_modified:
                modified_files.append(str(file_path.relative_to(repo_path)))

        return modified_files
