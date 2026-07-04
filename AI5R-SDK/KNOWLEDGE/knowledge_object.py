from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional


@dataclass
class KnowledgeObject:
    knowledge_id: str = ""
    organization_id: str = ""
    department_id: str = ""
    owner_worker_id: str = ""
    knowledge_code: str = ""
    title: str = ""
    content: Any = field(default_factory=dict)
    source_type: str = "memory"
    source_id: str = ""
    source_memory_ids: List[str] = field(default_factory=list)
    domain: str = "general"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    digital_thread_id: str = ""
    status: str = "knowledge"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self):
        if not self.knowledge_id:
            if self.knowledge_code:
                self.knowledge_id = self.knowledge_code
            elif self.source_memory_ids:
                self.knowledge_id = "knowledge-" + "-".join(self.source_memory_ids)
            else:
                self.knowledge_id = "knowledge-unknown"

        if not self.source_id and self.source_memory_ids:
            self.source_id = self.source_memory_ids[0]

        if not self.tags and self.domain:
            self.tags = [self.domain]

    def to_dict(self):
        return {
            "knowledge_id": self.knowledge_id,
            "organization_id": self.organization_id,
            "department_id": self.department_id,
            "owner_worker_id": self.owner_worker_id,
            "knowledge_code": self.knowledge_code,
            "title": self.title,
            "content": self.content,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "source_memory_ids": self.source_memory_ids,
            "domain": self.domain,
            "tags": self.tags,
            "metadata": self.metadata,
            "confidence": self.confidence,
            "digital_thread_id": self.digital_thread_id,
            "status": self.status,
            "created_at": self.created_at,
        }
