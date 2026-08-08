"""
MWO-LTSA-037F -- FleetInsight: deterministic, rule-free derivation of a
fleet-wide Summary/Priority/Action/Reason, in the exact same composition
style as EngineeringInsight (MWO-LTSA-035): pure field selection over data
FleetExecutiveSummaryService (MWO-LTSA-037E) already produced. No LLM, no
prompt, no new business rules -- the actual risk ranking stays entirely
owned by RecommendationEngine, already reflected in
FleetExecutiveSummary.top_risks (sorted by priority descending).

Priority / Action / Reason: all taken from the fleet's own highest-
priority risk (top_risks[0] -- FleetExecutiveSummary.top_risks is already
sorted descending; this module does not re-sort or re-rank it), mirroring
EngineeringInsight's own recommended_action=top.action /
root_cause=top.description pattern exactly.

Summary: a fleet-level sentence composed entirely from
FleetExecutiveSummary's own already-computed fields (fleet_status,
critical_asset_count, and the top risk's tag_number/title) -- string
composition only, no new derivation, no fabricated analysis.

If no risk exists (top_risks is empty), there is nothing to build an
insight from -- returns None rather than fabricating placeholder content,
matching EngineeringInsight's own "no recommendations -> None" rule and
this codebase's established "disclosed gap, not invented" discipline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .fleet_executive_summary import FleetExecutiveSummary


@dataclass(frozen=True, slots=True)
class FleetInsight:
    """Immutable: deterministic fleet-wide insight, derived from the
    fleet's single highest-priority risk."""

    summary: str
    priority: int
    action: str
    reason: str


def build_fleet_insight(summary: "FleetExecutiveSummary") -> FleetInsight | None:
    if not summary.top_risks:
        return None

    top = summary.top_risks[0]

    return FleetInsight(
        summary=(
            f"Fleet status {summary.fleet_status}: {summary.critical_asset_count} "
            f"critical asset(s). Top risk: {top.title} on {top.tag_number}."
        ),
        priority=top.priority,
        action=top.action,
        reason=top.description,
    )


__all__ = ["FleetInsight", "build_fleet_insight"]
