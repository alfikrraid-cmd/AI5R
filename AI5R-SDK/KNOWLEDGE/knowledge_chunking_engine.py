from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List
from uuid import uuid4

from .knowledge_object import KnowledgeObject


@dataclass
class KnowledgeChunk:
    knowledge_id: str
    organization_id: str
    chunk_index: int
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    object_type: str = "KNOWLEDGE_CHUNK"
    chunk_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "ACTIVE"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self):
        return self.__dict__


class KnowledgeChunkingEngine:
    def chunk(
        self,
        knowledge: KnowledgeObject,
        max_chars: int = 500,
    ) -> List[KnowledgeChunk]:
        if max_chars <= 0:
            raise ValueError("max_chars must be greater than zero")

        text = knowledge.content.strip()
        if not text:
            raise ValueError("Knowledge content cannot be empty")

        chunks = []
        start = 0
        index = 0

        while start < len(text):
            part = text[start:start + max_chars].strip()

            chunks.append(
                KnowledgeChunk(
                    knowledge_id=knowledge.knowledge_id,
                    organization_id=knowledge.organization_id,
                    chunk_index=index,
                    content=part,
                    metadata={
                        "knowledge_code": knowledge.knowledge_code,
                        "title": knowledge.title,
                        "source_type": knowledge.source_type,
                    },
                )
            )

            start += max_chars
            index += 1

        return chunks
