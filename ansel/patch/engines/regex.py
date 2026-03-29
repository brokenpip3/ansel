import re
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List

from ansel.patch.engines.base import BaseEngine


class RegexPatchEngine(BaseEngine):
    def apply(
        self,
        file_path: Path,
        operations: List[Dict[str, Any]],
        vars_dict: Dict[str, Any],
    ) -> bool:
        content = file_path.read_text()
        original_content = content

        for op in operations:
            search = str(op.get("search", ""))
            replace = str(op.get("replace", ""))
            content = re.sub(search, replace, content)

        if content != original_content:
            file_path.write_text(content)
            return True
        return False
