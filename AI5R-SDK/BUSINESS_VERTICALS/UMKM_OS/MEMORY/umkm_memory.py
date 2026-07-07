from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any



@dataclass
class BusinessMemory:

    memory_id: str
    category: str
    experience: dict[str, Any]
    created_at: str = datetime.now(UTC).isoformat()



class UMKMMemorySystem:


    def __init__(self):

        self.memories = {}



    def store(
        self,
        memory: BusinessMemory
    ):

        self.memories[
            memory.memory_id
        ] = memory


        return {

            "status":"STORED",

            "memory_id":
            memory.memory_id

        }



    def recall(
        self,
        memory_id: str
    ):

        return self.memories.get(
            memory_id
        )



    def learn(
        self
    ):

        return {

            "status":"LEARNING",

            "patterns":
            len(self.memories)

        }
