from typing import Dict, Any

from .knowledge_source import KnowledgeSource
from .knowledge_registry import KnowledgeRegistry
from .knowledge_ingestion_engine import KnowledgeIngestionEngine
from .knowledge_validation_engine import KnowledgeValidationEngine
from .knowledge_chunking_engine import KnowledgeChunkingEngine


class KnowledgePipeline:
    def __init__(self):
        self.registry = KnowledgeRegistry()
        self.ingestion = KnowledgeIngestionEngine()
        self.validation = KnowledgeValidationEngine()
        self.chunking = KnowledgeChunkingEngine()

    def run(
        self,
        source: KnowledgeSource,
        title: str,
        content: str,
        metadata: Dict[str, Any] | None = None,
        max_chars: int = 500,
    ) -> Dict[str, Any]:
        knowledge = self.ingestion.ingest(
            source=source,
            title=title,
            content=content,
            metadata=metadata,
        )

        validation = self.validation.validate(knowledge)

        if not validation["valid"]:
            return {
                "success": False,
                "validation": validation,
                "knowledge": knowledge,
                "chunks": [],
            }

        self.registry.register(knowledge)
        chunks = self.chunking.chunk(knowledge, max_chars=max_chars)

        return {
            "success": True,
            "validation": validation,
            "knowledge": knowledge,
            "chunks": chunks,
        }
