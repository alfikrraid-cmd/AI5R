from enum import Enum


class EmployeeStatus(str, Enum):
    CREATED = "CREATED"
    INITIALIZED = "INITIALIZED"
    READY = "READY"
    WORKING = "WORKING"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    EVALUATED = "EVALUATED"
    LEARNING = "LEARNING"
