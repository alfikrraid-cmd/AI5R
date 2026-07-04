from typing import Any, Dict, List

from .knowledge_chunking_engine import KnowledgeChunkingEngine, KnowledgeChunk
from .knowledge_ingestion_engine import KnowledgeIngestionEngine
from .knowledge_registry import KnowledgeRegistry
from .knowledge_retrieval_engine import KnowledgeRetrievalEngine
from .knowledge_source import KnowledgeSource
from .knowledge_validation_engine import KnowledgeValidationEngine


class KnowledgeRuntime:
    """
    Runtime orchestrator for the AI5R Knowledge subsystem.

    Objective:
    Provide a single runtime entry point for knowledge ingestion,
    validation, chunking, registration, and retrieval.

    Architecture:
    Source -> Ingestion -> Validation -> Chunking -> Registry -> Retrieval
    """

    def __init__(
        self,
        ingestion_engine=None,
        validation_engine=None,
        chunking_engine=None,
        retrieval_engine=None,
        registry=None,
    ):
        self.ingestion_engine = ingestion_engine or KnowledgeIngestionEngine()
        self.validation_engine = validation_engine or KnowledgeValidationEngine()
        self.chunking_engine = chunking_engine or KnowledgeChunkingEngine()
        self.retrieval_engine = retrieval_engine or KnowledgeRetrievalEngine()
        self.registry = registry or KnowledgeRegistry()
        self._chunks: List[KnowledgeChunk] = []

    def process(
        self,
        source: KnowledgeSource,
        title: str,
        content: str,
        metadata: Dict[str, Any] | None = None,
        max_chars: int = 500,
    ) -> Dict[str, Any]:
        knowledge = self.ingestion_engine.ingest(
            source=source,
            title=title,
            content=content,
            metadata=metadata,
        )

        validation = self.validation_engine.validate(knowledge)

        if not validation["valid"]:
            return {
                "status": "FAILED",
                "knowledge": knowledge,
                "validation": validation,
                "chunks": [],
            }

        chunks = self.chunking_engine.chunk(
            knowledge=knowledge,
            max_chars=max_chars,
        )

        self.registry.register(knowledge)
        self._chunks.extend(chunks)

        return {
            "status": "PROCESSED",
            "knowledge": knowledge,
            "validation": validation,
            "chunks": chunks,
        }

    def get(self, knowledge_id):
        return self.registry.get(knowledge_id)

    def list_all(self):
        return self.registry.list_all()

    def list_chunks(self):
        return list(self._chunks)

    def search(
        self,
        organization_id: str,
        query: str,
        limit: int = 5,
    ):
        return self.retrieval_engine.search(
            chunks=self._chunks,
            organization_id=organization_id,
            query=query,
            limit=limit,
        )
