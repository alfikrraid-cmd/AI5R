from FOUNDATION.canonical_identity import CanonicalIdentityGenerator
from FOUNDATION.canonical_object import CanonicalObject
from FOUNDATION.canonical_event import CanonicalEvent
from FOUNDATION.canonical_pipeline import CanonicalPipeline
from FOUNDATION.canonical_registry import CanonicalRegistry
from FOUNDATION.canonical_runtime import CanonicalRuntime


class KernelBaseline:

    VERSION = "1.0.0"

    COMPONENTS = {
        "identity": CanonicalIdentityGenerator,
        "object": CanonicalObject,
        "event": CanonicalEvent,
        "pipeline": CanonicalPipeline,
        "registry": CanonicalRegistry,
        "runtime": CanonicalRuntime,
    }

    @classmethod
    def verify(cls) -> dict:
        required = [
            "identity",
            "object",
            "event",
            "pipeline",
            "registry",
            "runtime",
        ]

        missing = [
            item
            for item in required
            if item not in cls.COMPONENTS
        ]

        return {
            "version": cls.VERSION,
            "status": "PASS" if not missing else "FAIL",
            "components": sorted(cls.COMPONENTS.keys()),
            "missing": missing,
        }
