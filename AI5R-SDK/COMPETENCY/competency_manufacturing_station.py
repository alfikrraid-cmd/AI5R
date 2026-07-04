from .competency_manifest import CompetencyManifest


class CompetencyManufacturingStation:
    """
    AI5R Competency Manufacturing Station

    Produces the canonical Competency Foundation artifact.
    """

    @property
    def name(self):
        return "competency"

    @property
    def depends_on(self):
        return ["capability"]

    def run(self, unit=None, target=None):
        manifest = CompetencyManifest()

        return {
            "station": self.name,
            "status": "SUCCESS",
            "manifest": manifest.to_dict(),
        }
