from typing import Any, Dict, List

from .competency_object import CompetencyObject


class CompetencyMeasurementEngine:
    """
    Enterprise Competency Measurement Engine

    Objective:
    Measure capability performance from execution evidence.
    """

    def measure(
        self,
        organization_id: str,
        capability_id: str,
        competency_code: str,
        competency_name: str,
        executions: List[Dict[str, Any]],
        metadata: Dict[str, Any] | None = None,
    ) -> CompetencyObject:
        total = len(executions)

        if total == 0:
            success_rate = 0.0
            failure_rate = 0.0
            accuracy_score = 0.0
        else:
            successes = [
                item for item in executions
                if item.get("status") == "SUCCESS"
            ]

            failures = [
                item for item in executions
                if item.get("status") == "FAILED"
            ]

            accuracy_values = [
                item.get("accuracy", 0.0)
                for item in executions
                if isinstance(item.get("accuracy", None), (int, float))
            ]

            success_rate = len(successes) / total
            failure_rate = len(failures) / total

            if accuracy_values:
                accuracy_score = sum(accuracy_values) / len(accuracy_values)
            else:
                accuracy_score = 0.0

        evidence_ids = [
            item.get("execution_id")
            for item in executions
            if item.get("execution_id")
        ]

        return CompetencyObject(
            organization_id=organization_id,
            capability_id=capability_id,
            competency_code=competency_code,
            competency_name=competency_name,
            success_rate=success_rate,
            failure_rate=failure_rate,
            accuracy_score=accuracy_score,
            evidence_count=total,
            evidence_ids=evidence_ids,
            performance_metrics={
                "total_executions": total,
                "success_rate": success_rate,
                "failure_rate": failure_rate,
                "accuracy_score": accuracy_score,
            },
            metadata=metadata or {},
        )
