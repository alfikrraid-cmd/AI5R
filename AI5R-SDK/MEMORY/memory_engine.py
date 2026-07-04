from uuid import uuid4

from .memory_object import MemoryObject


class MemoryEngine:
    """
    Enterprise Memory Engine

    Learning
        ↓
    Memory
    """

    def memorize(self, learning):

        learning_id = getattr(learning, "learning_id", None)

        if not learning_id:
            raise ValueError("Learning must have learning_id")

        lesson = getattr(learning, "lesson", "")

        confidence_delta = getattr(
            learning,
            "confidence_delta",
            0.0,
        )

        return MemoryObject(

            memory_id=f"memory-{uuid4()}",

            learning_id=learning_id,

            content={
                "lesson": lesson,
            },

            confidence=max(0.0, min(1.0, 0.5 + confidence_delta)),

            digital_thread_id=learning.digital_thread_id,
        )
