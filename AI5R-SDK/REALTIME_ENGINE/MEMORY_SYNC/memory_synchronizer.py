from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any


@dataclass
class MemoryRecord:

    memory_type: str
    content: dict[str, Any]
    created_at: str = datetime.now(UTC).isoformat()



class RealtimeMemorySynchronizer:


    def __init__(self):

        self.memories = []


    def store(
        self,
        experience: dict[str, Any]
    ):

        memory = MemoryRecord(
            memory_type="REALTIME_EXPERIENCE",
            content=experience
        )

        self.memories.append(memory)


        return {
            "status": "STORED",
            "memory_count": len(self.memories)
        }



    def recall(self):

        return self.memories
