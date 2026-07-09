from dataclasses import dataclass
from typing import Any

from WORKFORCE.workforce_execution_plan import WorkforceExecutionPlan


@dataclass
class SchedulerDecision:
    status: str
    work_item_id: str | None
    reason: str
    metadata: dict[str, Any]


class DigitalWorkforceScheduler:
    def next_work_item(self, plan: WorkforceExecutionPlan) -> SchedulerDecision:
        ready_items = plan.ready_items()

        if not ready_items:
            return SchedulerDecision(
                status="NO_READY_WORK",
                work_item_id=None,
                reason="No work item is ready to run",
                metadata=plan.snapshot(),
            )

        selected = ready_items[0]
        plan.mark_running(selected)

        return SchedulerDecision(
            status="WORK_SELECTED",
            work_item_id=selected,
            reason="Selected first ready work item",
            metadata=plan.snapshot(),
        )

    def complete_work_item(
        self,
        plan: WorkforceExecutionPlan,
        work_item_id: str,
    ) -> SchedulerDecision:
        plan.mark_completed(work_item_id)

        return SchedulerDecision(
            status="WORK_COMPLETED",
            work_item_id=work_item_id,
            reason="Work item completed and dependencies updated",
            metadata=plan.snapshot(),
        )
