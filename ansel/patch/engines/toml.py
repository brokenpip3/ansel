import fnmatch
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Tuple

import tomlkit

from ansel.patch.engines.base import BaseEngine


class TomlPatchEngine(BaseEngine):
    def apply(
        self,
        file_path: Path,
        operations: List[Dict[str, Any]],
        vars_dict: Dict[str, Any],
    ) -> bool:
        from ansel.template import render_string

        content = file_path.read_text()
        doc = tomlkit.parse(content)

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
            select = op.get("select", "**")
            where = render_recursive(op.get("where", {}))
            update = render_recursive(op.get("update", {}))
            delete = op.get("delete")

            targets = self._find_targets(doc, select, where)
            # Reverse sort for list stability
            targets.sort(
                key=lambda t: t[1] if isinstance(t[1], int) else 0, reverse=True
            )

            for parent, identifier, value in targets:
                if delete is True:
                    if parent is not None:
                        ident_str = str(identifier)
                        # We must use doc.remove for top-level items
                        if parent is doc:
                            doc.remove(ident_str)
                            modified = True
                        elif isinstance(parent, dict) and ident_str in parent:
                            del parent[ident_str]
                            modified = True
                        elif isinstance(parent, list):
                            parent.pop(identifier)
                            modified = True
                elif delete:
                    if isinstance(value, dict):
                        keys_to_del = [delete] if isinstance(delete, str) else delete
                        for k in keys_to_del:
                            if k in value:
                                del value[k]
                                modified = True

                if update:
                    if self._apply_update(value, update):
                        modified = True

        if modified:
            file_path.write_text(tomlkit.dumps(doc))
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
            return True
        if not isinstance(data, dict):
            return False

        for k, pattern in where.items():
            if k not in data:
                return False
            val = str(data[k])
            if not fnmatch.fnmatch(val, str(pattern)):
                return False
        return True

    def _apply_update(self, target: Any, update: Any) -> bool:
        if isinstance(update, dict) and isinstance(target, dict):
            modified = False
            for k, v in update.items():
                if k not in target or target[k] != v:
                    target[k] = v
                    modified = True
            return modified
        elif isinstance(target, list) and isinstance(update, list):
            target.clear()
            target.extend(update)
            return True
        return False
