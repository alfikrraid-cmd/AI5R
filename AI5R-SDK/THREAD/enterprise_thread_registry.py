class EnterpriseThreadRegistry:
    """
    Enterprise Thread Registry

    Objective:
    Store and retrieve Enterprise Cognitive Threads.
    """

    def __init__(self):
        self._threads = {}

    def register(self, thread):
        thread_id = getattr(thread, "thread_id", None)

        if thread_id is None:
            raise ValueError("EnterpriseThread must have thread_id")

        self._threads[thread_id] = thread
        return thread

    def get(self, thread_id):
        return self._threads.get(thread_id)

    def exists(self, thread_id):
        return thread_id in self._threads

    def list_all(self):
        return list(self._threads.values())

    def list_by_organization(self, organization_id):
        return [
            thread
            for thread in self._threads.values()
            if getattr(thread, "organization_id", None) == organization_id
        ]

    def list_by_mission(self, mission_id):
        return [
            thread
            for thread in self._threads.values()
            if getattr(thread, "mission_id", None) == mission_id
        ]

    def list_by_worker(self, worker_id):
        return [
            thread
            for thread in self._threads.values()
            if getattr(thread, "worker_id", None) == worker_id
        ]

    def list_by_status(self, status):
        return [
            thread
            for thread in self._threads.values()
            if getattr(thread, "status", None) == status
        ]

    def list_by_station(self, station):
        return [
            thread
            for thread in self._threads.values()
            if getattr(thread, "current_station", None) == station
        ]
