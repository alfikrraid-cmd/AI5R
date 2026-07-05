from typing import Any

from FOUNDATION.canonical_object import CanonicalObject


class ReasoningObject(CanonicalObject):
    def __init__(
        self,
        reasoning_id: str | None = None,
        premises: list[dict[str, Any]] | None = None,
        evidence: list[dict[str, Any]] | None = None,
        conclusion: dict[str, Any] | None = None,
        confidence: float = 0.0,
        reasoning_path: list[str] | None = None,
        supporting_knowledge: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        version: str = "1.0",
    ):
        super().__init__(
            object_type="REASONING_OBJECT",
            object_id=reasoning_id,
            version=version,
            metadata=metadata or {},
        )

        self.premises = premises or []
        self.evidence = evidence or []
        self.conclusion = conclusion or {}
        self.confidence = confidence
        self.reasoning_path = reasoning_path or []
        self.supporting_knowledge = supporting_knowledge or []

    @property
    def reasoning_id(self) -> str:
        return self.object_id

    def validate(self) -> bool:
        super().validate()

        if not isinstance(self.premises, list):
            raise ValueError("premises must be a list")

        if not isinstance(self.evidence, list):
            raise ValueError("evidence must be a list")

        if not isinstance(self.reasoning_path, list):
            raise ValueError("reasoning_path must be a list")

        return True

    def add_premise(self, premise: dict[str, Any]):
        self.premises.append(premise)
        self.touch()

    def add_evidence(self, evidence: dict[str, Any]):
        self.evidence.append(evidence)
        self.touch()

    def set_conclusion(
        self,
        conclusion: dict[str, Any],
        confidence: float,
    ):
        self.conclusion = conclusion
        self.confidence = confidence
        self.touch()

    def add_reasoning_step(self, step: str):
        self.reasoning_path.append(step)
        self.touch()

    def add_supporting_knowledge(self, knowledge_id: str):
        self.supporting_knowledge.append(knowledge_id)
        self.touch()

    def to_dict(self):
        return {
            "object_id": self.object_id,
            "object_type": self.object_type,
            "reasoning_id": self.reasoning_id,
            "premises": self.premises,
            "evidence": self.evidence,
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "reasoning_path": self.reasoning_path,
            "supporting_knowledge": self.supporting_knowledge,
            "metadata": self.metadata,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
