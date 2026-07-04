from dataclasses import dataclass, field
from typing import List


@dataclass
class KnowledgeManifest:
    """
    AI5R Knowledge Foundation Manifest

    Canonical description of the Knowledge subsystem.
    """

    subsystem: str = "KNOWLEDGE"
    foundation_version: str = "1.0"
    runtime: str = "KnowledgeRuntime"

    registry: str = "KnowledgeRegistry"

    engines: List[str] = field(default_factory=lambda: [
        "KnowledgeIngestionEngine",
        "KnowledgeValidationEngine",
        "KnowledgeChunkingEngine",
        "KnowledgeRetrievalEngine",
    ])

    objects: List[str] = field(default_factory=lambda: [
        "KnowledgeObject",
        "KnowledgeSource",
        "KnowledgeChunk",
    ])

    pipeline: List[str] = field(default_factory=lambda: [
        "KnowledgeIngestion",
        "KnowledgeValidation",
        "KnowledgeChunking",
        "KnowledgeRegistry",
        "KnowledgeRetrieval",
    ])

    status: str = "FROZEN_CANDIDATE"

    def to_dict(self):
        return {
            "subsystem": self.subsystem,
            "foundation_version": self.foundation_version,
            "runtime": self.runtime,
            "registry": self.registry,
            "engines": self.engines,
            "objects": self.objects,
            "pipeline": self.pipeline,
            "status": self.status,
        }
