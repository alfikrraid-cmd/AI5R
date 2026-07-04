from abc import ABC, abstractmethod
from typing import Any


class EnterpriseCognitiveStation(ABC):
    """
    Base class for all Enterprise Cognitive Stations.

    Canonical pattern:

        Input Object
              │
              ▼
        Cognitive Station
              │
              ▼
        Output Object
    """

    input_object_type: str = ""
    output_object_type: str = ""

    def process(self, enterprise_object: Any):
        self.validate(enterprise_object)
        return self.transform(enterprise_object)

    def validate(self, enterprise_object: Any):
        if enterprise_object is None:
            raise ValueError("Enterprise object cannot be None")

    @abstractmethod
    def transform(self, enterprise_object: Any):
        pass
