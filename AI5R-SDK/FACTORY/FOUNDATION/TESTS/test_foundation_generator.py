import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.FOUNDATION.foundation_manifest import FoundationManifest
from FACTORY.FOUNDATION.foundation_generator import FoundationGenerator


def test_foundation_generator():
    with TemporaryDirectory() as temp_dir:
        manifest = FoundationManifest(
            foundation="Worker",
            code="WA",
        )

        result = FoundationGenerator().generate(
            manifest=manifest,
            root=temp_dir,
        )

        base = Path(temp_dir) / "WORKER"

        assert result["status"] == "GENERATED"
        assert result["foundation"] == "WORKER"
        assert (base / "__init__.py").exists()
        assert (base / "worker_object.py").exists()
        assert (base / "worker_registry.py").exists()
        assert (base / "worker_validation_engine.py").exists()
        assert (base / "worker_runtime.py").exists()
        assert (base / "worker_manifest.py").exists()
        assert (base / "worker_manufacturing_station.py").exists()
        assert (base / "TESTS" / "test_worker_object.py").exists()
        assert (base / "DOCS" / "WA-SPECIFICATION.md").exists()
        assert (base / "DOCS" / "WORKER-FOUNDATION-FREEZE-v1.0.md").exists()

    print("FG-001 Foundation Generator OK")


if __name__ == "__main__":
    test_foundation_generator()
