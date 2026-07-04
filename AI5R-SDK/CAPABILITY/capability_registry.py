class CapabilityRegistry:
    """
    Enterprise Capability Registry

    Objective:
    Store and retrieve Capability Objects by canonical identifiers.
    """

    def __init__(self):
        self._capabilities = {}

    def register(self, capability):
        capability_id = getattr(capability, "capability_id", None)

        if capability_id is None:
            raise ValueError("Capability object must have capability_id")

        self._capabilities[capability_id] = capability
        return capability

    def get(self, capability_id):
        return self._capabilities.get(capability_id)

    def exists(self, capability_id):
        return capability_id in self._capabilities

    def list_all(self):
        return list(self._capabilities.values())

    def list_by_organization(self, organization_id):
        return [
            capability
            for capability in self._capabilities.values()
            if getattr(capability, "organization_id", None) == organization_id
        ]

    def list_by_domain(self, domain):
        return [
            capability
            for capability in self._capabilities.values()
            if domain in getattr(capability, "supported_domains", [])
        ]

    def list_by_status(self, status):
        return [
            capability
            for capability in self._capabilities.values()
            if getattr(capability, "status", None) == status
        ]
