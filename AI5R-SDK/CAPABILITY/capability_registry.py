from CAPABILITY.CONTRACTS.capability_contract import CapabilityManifest


class CapabilityRegistry:
    def __init__(self):
        self._capabilities: dict[str, CapabilityManifest] = {}

    def register(self, manifest: CapabilityManifest):
        if not manifest.capability_id:
            raise ValueError("capability_id is required")

        self._capabilities[manifest.capability_id] = manifest

        return manifest

    def get(self, capability_id: str):
        return self._capabilities.get(capability_id)


    def list_by_domain(self, domain):
        return [
            capability
            for capability in self.list_all()
            if domain in getattr(capability, "supported_domains", [])
        ]

    def list_all(self):
        return list(self._capabilities.values())

    def exists(self, capability_id: str) -> bool:
        return capability_id in self._capabilities
