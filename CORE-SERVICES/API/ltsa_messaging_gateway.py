"""
MWO-LTSA-039A -- LTSAMessagingGateway: a channel-agnostic orchestration
foundation over already-existing services, reused in-process exactly as
pumps.py's get_ltsa_pump_knowledge and fleet.py's get_fleet_powerbi
already compose them -- no HTTP client, no SQL, no WhatsApp SDK, no new
calculation, no new formatting. See test_ltsa_messaging_gateway.py's own
structural guards for the exact constraints this module is held to.

get_pump_summary(tag_number) reuses LTSAKnowledgeService (the pump's own
recommendations) and EngineeringContextEngine (the pump's cm_summary/
overall_condition) exactly as engineering_insight.py's own
build_engineering_insight() already expects them, mirroring
EngineeringContextEngine.build()'s own (tag_number, today=None) shape --
this gateway never re-derives risk/root-cause/action, only composes
values those two already-existing components produced.

get_fleet_summary() reuses FleetExecutiveSummaryService and
fleet_insight.py's build_fleet_insight() the same way fleet.py's
/api/ltsa/fleet/powerbi endpoint already does -- distinct response shape
(summary nested under its own "summary" key rather than spread at the
top level) since this is a channel-agnostic message payload, not the
Power BI dataset contract get_fleet_powerbi() serves.
"""
from __future__ import annotations
import dataclasses
from typing import Any

from .engineering_context_engine import EngineeringContextEngine
from .engineering_insight import build_engineering_insight
from .fleet_executive_summary import FleetExecutiveSummaryService
from .fleet_insight import build_fleet_insight
from .ltsa_knowledge_service import LTSAKnowledgeService


@dataclasses.dataclass(frozen=True, slots=True)
class MessageRequest:
    """Immutable: one channel-agnostic inbound request. `tag` is only
    meaningful for pump-scoped intents; fleet-scoped requests leave it
    unset."""
    intent: str
    tag: str | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class MessageResponse:
    """Immutable: one channel-agnostic outbound response."""
    success: bool
    data: dict[str, Any]


class LTSAMessagingGateway:
    """Orchestrates already-existing LTSA services into the two message
    intents this gateway currently serves (pump summary, fleet summary).
    No new gateway, no new calculation -- pure composition."""

    def __init__(
        self,
        ltsa_knowledge_service: LTSAKnowledgeService,
        engineering_context_engine: EngineeringContextEngine,
        fleet_executive_summary_service: FleetExecutiveSummaryService,
    ) -> None:
        self.ltsa_knowledge_service = ltsa_knowledge_service
        self.engineering_context_engine = engineering_context_engine
        self.fleet_executive_summary_service = fleet_executive_summary_service

    def get_pump_summary(self, tag_number: str) -> MessageResponse:
        knowledge = self.ltsa_knowledge_service.build(tag_number)
        context = self.engineering_context_engine.build(tag_number)
        insight = build_engineering_insight(knowledge.recommendation, context)
        return MessageResponse(
            success=True,
            data={
                "tag_number": tag_number,
                "summary": context,
                "insight": dataclasses.asdict(insight) if insight is not None else None,
            },
        )

    def get_fleet_summary(self) -> MessageResponse:
        summary = self.fleet_executive_summary_service.build()
        insight = build_fleet_insight(summary)
        return MessageResponse(
            success=True,
            data={
                "summary": dataclasses.asdict(summary),
                "insight": dataclasses.asdict(insight) if insight is not None else None,
            },
        )


__all__ = ["LTSAMessagingGateway", "MessageRequest", "MessageResponse"]
