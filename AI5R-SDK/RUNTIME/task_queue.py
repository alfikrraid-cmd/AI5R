from collections import deque
from typing import Optional

from RUNTIME.enterprise_task import EnterpriseTask


class TaskQueue:

    def __init__(self):
        self._queue = deque()

    def enqueue(self, task: EnterpriseTask):
        self._queue.append(task)

    def dequeue(self) -> Optional[EnterpriseTask]:
        if not self._queue:
            return None

        return self._queue.popleft()

    def empty(self):
        return len(self._queue) == 0

    def size(self):
        return len(self._queue)

    def clear(self):
        self._queue.clear()
