class UnsupportedDockerOperation(Exception):
    """Raised internally when a requested operation is not in SUPPORTED_OPERATIONS.

    Always caught inside DockerCapability.execute() and converted into a
    FAILED CapabilityResult. Never propagates out of the capability.
    """
