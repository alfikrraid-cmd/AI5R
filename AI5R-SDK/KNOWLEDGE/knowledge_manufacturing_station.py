from MANUFACTURING.station import ManufacturingStation

from .knowledge_manifest import KnowledgeManifest


class KnowledgeManufacturingStation(ManufacturingStation):
    """
    AI5R Knowledge Manufacturing Station

    Produces the canonical Knowledge Foundation artifact.
    """

    @property
    def name(self):
        return "knowledge"

    @property
    def depends_on(self):
        return []

    def run(self, unit=None, target=None):
        manifest = KnowledgeManifest()

        return {
            "station": self.name,
            "status": "SUCCESS",
            "manifest": manifest.to_dict(),
        }
