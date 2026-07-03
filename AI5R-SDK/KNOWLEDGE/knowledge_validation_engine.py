from typing import Dict, Any, List

from .knowledge_object import KnowledgeObject


class KnowledgeValidationEngine:
    REQUIRED_FIELDS = [
        "organization_id",
        "knowledge_code",
        "title",
        "content",
        "source_type",
    ]

    TRUST_LEVELS = [
        "low",
        "medium",
        "high",
        "verified",
    ]

    def validate(self, knowledge: KnowledgeObject) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []

        data = knowledge.to_dict()

        for field in self.REQUIRED_FIELDS:
            if not data.get(field):
                errors.append(f"Missing required field: {field}")

        if knowledge.content and len(knowledge.content.strip()) < 20:
            warnings.append("Knowledge content is very short")

        trust_level = knowledge.metadata.get("trust_level")

        if trust_level and trust_level not in self.TRUST_LEVELS:
            errors.append("Invalid trust_level")

        if not trust_level:
            warnings.append("Missing trust_level metadata")

        valid = len(errors) == 0

        return {
            "valid": valid,
            "errors": errors,
            "warnings": warnings,
            "knowledge_id": knowledge.knowledge_id,
            "knowledge_code": knowledge.knowledge_code,
        }
