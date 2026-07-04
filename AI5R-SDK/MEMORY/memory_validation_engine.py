from .memory_object import MemoryObject


class MemoryValidationEngine:
    """
    Validates Enterprise Memory Objects before persistence.
    """

    MINIMUM_CONFIDENCE = 0.50

    def validate(self, memory: MemoryObject):

        if not memory.memory_id:
            raise ValueError("memory_id is required")

        if not memory.learning_id:
            raise ValueError("learning_id is required")

        if memory.confidence < self.MINIMUM_CONFIDENCE:
            raise ValueError(
                "Memory confidence below minimum threshold"
            )

        if not memory.digital_thread_id:
            raise ValueError(
                "digital_thread_id is required"
            )

        return True
