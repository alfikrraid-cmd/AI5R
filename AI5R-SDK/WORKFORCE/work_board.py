from WORKFORCE.work_item import WorkItem
from WORKFORCE.digital_employee import DigitalEmployee
from WORKFORCE.approval_chain_runtime import (
    is_production_work_item,
    validate_chief_approval,
)


class WorkBoard:

    def __init__(self, approval_chain_runtime=None):
        self._published: dict[str, WorkItem] = {}
        self._claimed: dict[str, WorkItem] = {}
        self._completed: dict[str, WorkItem] = {}
        self._released: dict[str, WorkItem] = {}
        self._approval_chain_runtime = approval_chain_runtime

    def publish(self, work_item: WorkItem):

        work_item.status = "PUBLISHED"

        self._published[
            work_item.work_item_id
        ] = work_item

        return work_item

    def available_work_items(self):

        return list(
            self._published.values()
        )

    def claimed_work_items(self):

        return list(
            self._claimed.values()
        )

    def completed_work_items(self):

        return list(
            self._completed.values()
        )

    def claim(self, employee: DigitalEmployee, work_item_id: str):

        if work_item_id not in self._published:
            raise ValueError("Work item is not available to claim")

        work_item = self._published[work_item_id]

        if employee.status != "ACTIVE":
            raise ValueError("Only ACTIVE employee can claim work item")

        if work_item.assigned_position_id != employee.position_id:
            raise ValueError("Employee position does not match work item")

        work_item.status = "CLAIMED"
        work_item.assigned_employee_id = employee.employee_id

        self._claimed[work_item_id] = work_item
        del self._published[work_item_id]

        return work_item

    def complete(self, employee: DigitalEmployee, work_item_id: str):

        if work_item_id not in self._claimed:
            raise ValueError("Work item is not claimed")

        work_item = self._claimed[work_item_id]

        if work_item.assigned_employee_id != employee.employee_id:
            raise ValueError("Only the employee who claimed the work item can complete it")

        work_item.status = "COMPLETED"

        self._completed[work_item_id] = work_item
        del self._claimed[work_item_id]

        return work_item

    def release(self, work_item_id: str, approval=None):

        if work_item_id not in self._completed:
            raise ValueError("Work item must be COMPLETED before it can be released")

        work_item = self._completed[work_item_id]

        if is_production_work_item(work_item):
            resolved_approval = (
                approval
                or work_item.metadata.get("chief_approval")
                or work_item.metadata.get("approval")
            )
            if resolved_approval is None and self._approval_chain_runtime is not None:
                resolved_approval = getattr(
                    self._approval_chain_runtime, "get_chief_approval", lambda _: None
                )(work_item_id)

            validate_chief_approval(work_item=work_item, approval=resolved_approval)

            work_item.metadata["chief_approval"] = (
                resolved_approval.snapshot()
                if hasattr(resolved_approval, "snapshot")
                else resolved_approval
            )

        work_item.status = "RELEASED"

        self._released[work_item_id] = work_item
        del self._completed[work_item_id]

        return work_item

    def released_work_items(self):

        return list(
            self._released.values()
        )
