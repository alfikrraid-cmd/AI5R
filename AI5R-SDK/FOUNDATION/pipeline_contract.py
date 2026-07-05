from abc import ABC, abstractmethod
from typing import Any


class PipelineContract(ABC):
    @abstractmethod
    def execute(self, payload: Any) -> Any:
        raise NotImplementedError
