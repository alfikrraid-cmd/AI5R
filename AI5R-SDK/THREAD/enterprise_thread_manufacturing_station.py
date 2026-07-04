from .enterprise_thread_manifest import EnterpriseThreadManifest


class EnterpriseThreadManufacturingStation:
    """
    AI5R Enterprise Thread Manufacturing Station

    Produces the canonical Thread Foundation artifact.
    """

    @property
    def name(self):
        return "enterprise_thread"

    @property
    def depends_on(self):
        return []

    def run(self, unit=None, target=None):
        manifest = EnterpriseThreadManifest()

        return {
            "station": self.name,
            "status": "SUCCESS",
            "manifest": manifest.to_dict(),
        }
