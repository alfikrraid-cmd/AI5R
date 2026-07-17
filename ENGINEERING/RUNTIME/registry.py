from .contracts import Capability
from .exceptions import CapabilityNotFound


class CapabilityRegistry:
    """Holds capability instances keyed by their capability_code."""

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        self._capabilities[capability.capability_code] = capability

    def unregister(self, capability_code: str) -> None:
        if capability_code not in self._capabilities:
            raise CapabilityNotFound(
                f"Cannot unregister unknown capability: {capability_code}"
            )
        del self._capabilities[capability_code]

    def get(self, capability_code: str) -> Capability:
        capability = self._capabilities.get(capability_code)

        if capability is None:
            raise CapabilityNotFound(
                f"Capability not found: {capability_code}"
            )

        return capability

    def list(self) -> list[Capability]:
        return list(self._capabilities.values())

    def load_builtin(self) -> None:
        """Reserved extension point for future built-in capability discovery."""
        raise NotImplementedError

    def load_package(self) -> None:
        """Reserved extension point for future package-based capability discovery."""
        raise NotImplementedError
