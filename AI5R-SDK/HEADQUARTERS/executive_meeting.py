from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from HEADQUARTERS.board import ExecutiveBoard


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class ExecutiveOpinion:
    executive_id: str
    executive_name: str
    title: str
    perspective: str
    recommendation: str
    confidence: int
    risks: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExecutiveMeetingResult:
    meeting_id: str
    mission: str
    status: str
    leader: str
    opinions: list[ExecutiveOpinion]
    final_recommendation: str
    created_at: str = field(default_factory=_now)

    def snapshot(self) -> dict[str, Any]:
        return {
            "meeting_id": self.meeting_id,
            "mission": self.mission,
            "status": self.status,
            "leader": self.leader,
            "opinions": [
                {
                    "executive_id": opinion.executive_id,
                    "executive_name": opinion.executive_name,
                    "title": opinion.title,
                    "perspective": opinion.perspective,
                    "recommendation": opinion.recommendation,
                    "confidence": opinion.confidence,
                    "risks": opinion.risks,
                    "metadata": opinion.metadata,
                }
                for opinion in self.opinions
            ],
            "final_recommendation": self.final_recommendation,
            "created_at": self.created_at,
        }


class ExecutiveMeetingRuntime:
    PERSPECTIVES = {
        "CEO": "Strategy and value creation",
        "CTO": "Technology and architecture",
        "CFO": "Finance, ROI and sustainability",
        "CLO": "Legal, compliance and risk",
        "COO": "Operations and delivery",
        "CMO": "Marketing and growth",
        "CHRO": "Workforce and capability",
        "CKO": "Knowledge and learning",
    }

    def __init__(self, board: ExecutiveBoard) -> None:
        self.board = board

    def run(
        self,
        mission: str,
        participants: list[str] | None = None,
        leader_id: str = "CEO",
    ) -> ExecutiveMeetingResult:
        resolved_participants = participants or [
            "CEO",
            "CTO",
            "CFO",
            "CLO",
            "COO",
            "CMO",
            "CHRO",
            "CKO",
        ]

        opinions = []

        for executive_id in resolved_participants:
            executive = self.board.get(executive_id)
            executive.assign_mission(mission)

            opinions.append(
                ExecutiveOpinion(
                    executive_id=executive.executive_id,
                    executive_name=executive.name,
                    title=executive.title,
                    perspective=self.PERSPECTIVES.get(
                        executive.executive_id,
                        "General executive review",
                    ),
                    recommendation=self._recommendation_for(
                        executive.executive_id,
                        mission,
                    ),
                    confidence=self._confidence_for(executive.executive_id),
                    risks=self._risks_for(executive.executive_id),
                )
            )

            executive.complete()

        leader = self.board.get(leader_id)

        return ExecutiveMeetingResult(
            meeting_id=f"MEET-{uuid4()}",
            mission=mission,
            status="EXECUTIVE_RECOMMENDATION_READY",
            leader=leader.name,
            opinions=opinions,
            final_recommendation=(
                f"{leader.name} recommends approving the mission "
                "after considering executive perspectives."
            ),
        )

    def _recommendation_for(self, executive_id: str, mission: str) -> str:
        recommendations = {
            "CEO": "Approve if the mission creates measurable value.",
            "CTO": "Use a simple architecture first and scale after validation.",
            "CFO": "Control scope and validate ROI before expanding investment.",
            "CLO": "Review legal, privacy and compliance risks before launch.",
            "COO": "Break execution into clear phases with measurable milestones.",
            "CMO": "Define positioning and acquisition strategy before release.",
            "CHRO": "Assign capable employees and capture performance signals.",
            "CKO": "Retrieve relevant knowledge and store lessons after completion.",
        }

        return recommendations.get(
            executive_id,
            f"Review mission: {mission}",
        )

    def _confidence_for(self, executive_id: str) -> int:
        confidence = {
            "CEO": 90,
            "CTO": 88,
            "CFO": 84,
            "CLO": 82,
            "COO": 86,
            "CMO": 83,
            "CHRO": 80,
            "CKO": 87,
        }

        return confidence.get(executive_id, 75)

    def _risks_for(self, executive_id: str) -> list[str]:
        risks = {
            "CEO": ["Mission may lack business value if objective is unclear"],
            "CTO": ["Overengineering", "Technical debt"],
            "CFO": ["Budget overrun", "Low ROI"],
            "CLO": ["Compliance gap", "Privacy risk"],
            "COO": ["Delivery delay", "Resource bottleneck"],
            "CMO": ["Weak positioning", "Low adoption"],
            "CHRO": ["Capability gap", "Workforce overload"],
            "CKO": ["Incomplete knowledge", "Low knowledge reuse"],
        }

        return risks.get(executive_id, [])
