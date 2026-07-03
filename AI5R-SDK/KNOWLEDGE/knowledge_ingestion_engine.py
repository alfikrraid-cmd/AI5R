from typing import Dict, Any

from .knowledge_object import KnowledgeObject
from .knowledge_source import KnowledgeSource


class KnowledgeIngestionEngine:
    def ingest(
        self,
        source: KnowledgeSource,
        title: str,
        content: str,
        metadata: Dict[str, Any] | None = None,
    ) -> KnowledgeObject:
        if not content or not content.strip():
            raise ValueError("Knowledge content cannot be empty")

        merged_metadata = dict(source.metadata)
        if metadata:
            merged_metadata.update(metadata)

        merged_metadata["source_id"] = source.source_id
        merged_metadata["source_code"] = source.source_code
        merged_metadata["source_type"] = source.source_type

        return KnowledgeObject(
            organization_id=source.organization_id,
            department_id=source.department_id,
            knowledge_code=f"KNW-{source.source_code}",
            title=title,
            content=content.strip(),
            source_type=source.source_type,
            metadata=merged_metadata,
        )
