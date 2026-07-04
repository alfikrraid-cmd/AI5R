from .memory_runtime import MemoryRuntime


class EnterpriseMemoryPipeline:
    """
    Enterprise Memory Pipeline

    Learning
        ↓
    Memory Engine
        ↓
    Validation
        ↓
    Registry
        ↓
    Memory Object
    """

    def __init__(self):
        self.runtime = MemoryRuntime()

    def run(self, learning):

        memory = self.runtime.memorize(
            learning
        )

        return {

            "learning": learning,

            "memory": memory,

            "registry_size": self.runtime.count(),

        }
