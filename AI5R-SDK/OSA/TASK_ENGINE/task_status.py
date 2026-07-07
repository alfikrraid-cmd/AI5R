from enum import Enum


class TaskStatus(str, Enum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    READY = "READY"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
