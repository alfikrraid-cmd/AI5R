from WORKFORCE.work_item import WorkItem


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
