from MANUFACTURING.station import ManufacturingStation

from .capability_manifest import CapabilityManifest


class CapabilityManufacturingStation(ManufacturingStation):
    """
    AI5R Capability Manufacturing Station

    Produces the canonical Capability Foundation artifact.
    """

    @property
    def name(self):
        return "capability"

    @property
    def depends_on(self):
        return []

    def run(self, unit=None, target=None):
        manifest = CapabilityManifest()

        return {
            "station": self.name,
            "status": "SUCCESS",
            "manifest": manifest.to_dict(),
        }
