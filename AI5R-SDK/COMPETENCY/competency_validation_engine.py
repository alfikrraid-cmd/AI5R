from typing import Any, Dict, List

from .competency_object import CompetencyObject


class CompetencyValidationEngine:
    """
    Enterprise Competency Validation Engine

    Objective:
    Validate measured competency before registration.
    """

    REQUIRED_FIELDS = [
        "organization_id",
        "capability_id",
        "competency_code",
        "competency_name",
    ]

    ALLOWED_STATUSES = [
        "ACTIVE",
        "INACTIVE",
        "DEPRECATED",
    ]

    def validate(self, competency: CompetencyObject) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []

        data = competency.to_dict()

        for field in self.REQUIRED_FIELDS:
            if not data.get(field):
                errors.append(f"Missing required field: {field}")

        if competency.status not in self.ALLOWED_STATUSES:
            errors.append("Invalid competency status")

        for metric_name in [
            "success_rate",
            "accuracy_score",
            "failure_rate",
        ]:
            value = getattr(competency, metric_name)

            if value < 0 or value > 1:
                errors.append(f"{metric_name} must be between 0 and 1")

        if competency.evidence_count == 0:
            warnings.append("Competency has no execution evidence")

        if not competency.evidence_ids:
            warnings.append("Competency has no evidence references")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "competency_id": competency.competency_id,
            "competency_code": competency.competency_code,
            "capability_id": competency.capability_id,
        }
