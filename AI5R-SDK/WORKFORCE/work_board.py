from WORKFORCE.work_item import WorkItem
from WORKFORCE.digital_employee import DigitalEmployee


class WorkBoard:

    def __init__(self):
        self._published: dict[str, WorkItem] = {}
        self._claimed: dict[str, WorkItem] = {}
        self._completed: dict[str, WorkItem] = {}

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
