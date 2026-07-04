from .memory_engine import MemoryEngine
from .memory_registry import MemoryRegistry
from .memory_validation_engine import MemoryValidationEngine
from .memory_query_engine import MemoryQueryEngine


class MemoryRuntime:
    """
    Enterprise Memory Runtime
    """

    def __init__(self):

        self.engine = MemoryEngine()

        self.registry = MemoryRegistry()

        self.validator = MemoryValidationEngine()

        self.query = MemoryQueryEngine(
            self.registry
        )

    def memorize(self, learning):

        memory = self.engine.memorize(
            learning
        )

        self.validator.validate(
            memory
        )

        self.registry.register(
            memory
        )

        return memory

    def get(
        self,
        memory_id,
    ):

        return self.registry.get(
            memory_id
        )

    def count(self):

        return self.registry.count()
