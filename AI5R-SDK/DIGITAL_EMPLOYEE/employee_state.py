from enum import Enum


class EmployeeState(str, Enum):
    CREATED = "CREATED"
    INITIALIZED = "INITIALIZED"
    READY = "READY"
    PLANNING = "PLANNING"
    WORKING = "WORKING"
    OBSERVING = "OBSERVING"
    LEARNING = "LEARNING"
    SUSPENDED = "SUSPENDED"
