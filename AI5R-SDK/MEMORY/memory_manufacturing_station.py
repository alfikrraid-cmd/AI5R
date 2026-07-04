from .memory_manifest import EnterpriseMemoryManifest
from .memory_runtime import MemoryRuntime


class EnterpriseMemoryManufacturingStation:
    """
    Factory Manufacturing Station
    for Enterprise Memory.
    """

    station_name = "Enterprise Memory Manufacturing Station"

    station_version = "1.0"

    def manufacture(self):

        manifest = EnterpriseMemoryManifest()

        runtime = MemoryRuntime()

        return {

            "product_type": "enterprise_memory",

            "manifest": manifest.to_dict(),

            "runtime": runtime,

            "status": "manufactured",
        }
