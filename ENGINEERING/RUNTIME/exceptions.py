class CapabilityNotFound(Exception):
    """Raised when a requested capability is not present in the registry."""


class PolicyViolation(Exception):
    """Raised when a request fails runtime policy validation."""


class RuntimeExecutionError(Exception):
    """Raised when a capability fails during execution."""
