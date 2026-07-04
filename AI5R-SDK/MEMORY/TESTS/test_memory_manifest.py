import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from MEMORY.memory_manifest import EnterpriseMemoryManifest


def test_memory_manifest_defaults():

    manifest = EnterpriseMemoryManifest()

    assert manifest.memory_name == "Enterprise Memory"

    assert manifest.version == "1.0"

    assert manifest.supported_input == "learning"

    assert manifest.supported_output == "memory"

    assert len(manifest.pipeline) == 6

    assert manifest.pipeline[0] == "learning"

    assert manifest.pipeline[-1] == "runtime"


def test_memory_manifest_to_dict():

    manifest = EnterpriseMemoryManifest()

    data = manifest.to_dict()

    assert data["memory_name"] == "Enterprise Memory"

    assert data["version"] == "1.0"

    assert data["metadata"]["manufacturer"] == "AI5R Factory"
