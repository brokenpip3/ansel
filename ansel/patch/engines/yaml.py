import fnmatch
import io
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Tuple

from ruamel.yaml import YAML

from ansel.patch.engines.base import BaseEngine


class YamlPatchEngine(BaseEngine):
    def __init__(self):
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.width = 4096
        self.yaml.indent(mapping=2, sequence=2, offset=0)

    def apply(
        self,
        file_path: Path,
        operations: List[Dict[str, Any]],
        vars_dict: Dict[str, Any],
    ) -> bool:
        from ansel.template import render_string

        content = file_path.read_text()
        styles = [(2, 2, 0), (2, 4, 2)]
        best_data = None
        best_yaml = None
        min_reformat_lines = float("inf")

        for m, s, o in styles:
            yaml_inst = YAML()
            yaml_inst.preserve_quotes = True
            yaml_inst.width = 4096
            yaml_inst.indent(mapping=m, sequence=s, offset=o)
            try:
                # We MUST load fresh for every style to ensure correctly detected state
                data = yaml_inst.load(content)
                out = io.StringIO()
                yaml_inst.dump(data, out)
                import difflib

                diff = list(
                    difflib.unified_diff(
                        content.splitlines(), out.getvalue().splitlines()
                    )
                )
                changes = len(
                    [
                        line
                        for line in diff
                        if line.startswith("-") or line.startswith("+")
                    ]
                )
                if changes < min_reformat_lines:
                    min_reformat_lines = changes
                    best_data = data
                    best_yaml = yaml_inst
            except Exception:
                continue

        if best_data is None:
            best_yaml = YAML()
            best_yaml.preserve_quotes = True
            best_yaml.width = 4096
            best_data = best_yaml.load(content)

        def render_recursive(val: Any) -> Any:
            if isinstance(val, str):
                return render_string(val, vars_dict)
            if isinstance(val, dict):
                return {k: render_recursive(v) for k, v in val.items()}
            if isinstance(val, list):
                return [render_recursive(i) for i in val]
            return val

        modified = False
        for op in operations:
            # Default select to "**" (recursive search everywhere)
            select = op.get("select", "**")
            where = render_recursive(op.get("where", {}))
            update = render_recursive(op.get("update", {}))
            delete = op.get("delete")
            targets = self._find_targets(best_data, select, where)

            # If we are deleting items from a list, we must do it in reverse
            # to keep indices stable.
            targets.sort(
                key=lambda t: t[1] if isinstance(t[1], int) else 0, reverse=True
            )

            for parent, identifier, value in targets:
                if delete is True:
                    # Deleting the whole block
                    if parent is not None:
                        if isinstance(parent, dict):
                            del parent[identifier]
                            modified = True
                        elif isinstance(parent, list):
                            parent.pop(identifier)
                            modified = True
                elif delete:
                    # Deleting specific keys from a dict
                    if isinstance(value, dict):
                        keys_to_del = [delete] if isinstance(delete, str) else delete
                        for k in keys_to_del:
                            if k in value:
                                del value[k]
                                modified = True

                if update:
                    if self._apply_update(value, update, identifier, parent):
                        modified = True

        if modified:
            with open(file_path, "w") as f:
                best_yaml.dump(best_data, f)
        return modified

    def _find_targets(
        self, data: Any, select: str, where: Dict[str, Any]
    ) -> List[Tuple[Any, Any, Any]]:
        results = []
        if select in ("**", ".."):
            self._recursive_find(None, None, data, where, results)
        else:
            parts = select.split(".")
            self._path_find(None, None, data, parts, where, results)
        return results

    def _recursive_find(
        self,
        parent: Any,
        ident: Any,
        data: Any,
        where: Dict[str, Any],
        results: List[Tuple[Any, Any, Any]],
    ):
        if self._matches(data, where):
            results.append((parent, ident, data))

        if isinstance(data, dict):
            for k, v in data.items():
                self._recursive_find(data, k, v, where, results)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._recursive_find(data, i, item, where, results)

    def _path_find(
        self,
        parent: Any,
        ident: Any,
        data: Any,
        parts: List[str],
        where: Dict[str, Any],
        results: List[Tuple[Any, Any, Any]],
    ):
        if not parts:
            if self._matches(data, where):
                results.append((parent, ident, data))
            return

        current = parts[0]
        remaining = parts[1:]

        if current == "**":
            self._recursive_find(parent, ident, data, where, results)
            return

        if current == "*":
            if isinstance(data, dict):
                for k, v in data.items():
                    self._path_find(data, k, v, remaining, where, results)
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    self._path_find(data, i, item, remaining, where, results)
        elif isinstance(data, dict) and current in data:
            self._path_find(data, current, data[current], remaining, where, results)

    def _matches(self, data: Any, where: Dict[str, Any]) -> bool:
        if not where:
            return True  # Empty where matches everything
        if not isinstance(data, dict):
            return False

        for k, pattern in where.items():
            if k not in data:
                return False
            val = str(data[k])
            if not fnmatch.fnmatch(val, str(pattern)):
                return False
        return True

    def _apply_update(
        self, target: Any, update: Any, identifier: Any, parent: Any
    ) -> bool:
        if isinstance(update, dict) and isinstance(target, dict):
            modified = False
            for k, v in update.items():
                new_v = v
                new_comment = None
                if isinstance(v, str) and " #" in v:
                    new_v, new_comment = v.split(" #", 1)
                    new_v = new_v.strip()
                    new_comment = f"# {new_comment.strip()}\n"

                if k not in target or target[k] != new_v:
                    target[k] = new_v
                    modified = True

                if new_comment:
                    if hasattr(target, "ca") and k in target.ca.items:
                        comm_list = target.ca.items[k]
                        if len(comm_list) > 2 and comm_list[2]:
                            comm_list[2].value = f"{new_comment}"
                            modified = True
                        else:
                            target.yaml_set_comment_before_after_key(
                                k, after=new_comment.strip()
                            )
                            modified = True
                    elif hasattr(target, "yaml_set_comment_before_after_key"):
                        target.yaml_set_comment_before_after_key(
                            k, after=new_comment.strip()
                        )
                        modified = True
                else:
                    # Clear existing comment if not in update
                    if hasattr(target, "ca") and k in target.ca.items:
                        comm_list = target.ca.items[k]
                        if len(comm_list) > 2 and comm_list[2] is not None:
                            comm_list[2] = None
                            modified = True
            return modified
        elif isinstance(target, list) and isinstance(update, list):
            target.clear()
            target.extend(update)
            return True
        return False
