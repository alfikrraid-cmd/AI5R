from .enterprise_brain_manifest import EnterpriseBrainManifest
from .enterprise_brain_runtime import EnterpriseBrainRuntime


class EnterpriseBrainManufacturingStation:
    """
    Factory Manufacturing Station
    for Enterprise Brain.
    """

    station_name = "Enterprise Brain Manufacturing Station"

    station_version = "1.0"

    def manufacture(self):

        manifest = EnterpriseBrainManifest()

        runtime = EnterpriseBrainRuntime()

        return {
            "product_type": "enterprise_brain",
            "manifest": manifest.to_dict(),
            "runtime": runtime,
            "status": "manufactured",
        }
