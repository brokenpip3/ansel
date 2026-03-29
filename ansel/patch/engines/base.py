from abc import ABC
from abc import abstractmethod
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List


class BaseEngine(ABC):
    @abstractmethod
    def apply(
        self,
        file_path: Path,
        operations: List[Dict[str, Any]],
        vars_dict: Dict[str, Any],
    ) -> bool:
        pass
