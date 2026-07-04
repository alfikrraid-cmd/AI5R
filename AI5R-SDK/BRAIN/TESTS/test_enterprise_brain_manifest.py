import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from BRAIN.enterprise_brain_manifest import EnterpriseBrainManifest


def test_manifest_defaults():

    manifest = EnterpriseBrainManifest()

    assert manifest.brain_name == "Enterprise Brain"

    assert manifest.version == "1.0"

    assert manifest.supported_input == "reality"

    assert manifest.supported_output == "learning"

    assert len(manifest.enterprise_cognitive_thread) == 8

    assert manifest.enterprise_cognitive_thread[0] == "observation"

    assert manifest.enterprise_cognitive_thread[-1] == "learning"


def test_manifest_to_dict():

    manifest = EnterpriseBrainManifest()

    data = manifest.to_dict()

    assert data["brain_name"] == "Enterprise Brain"

    assert data["version"] == "1.0"

    assert data["supported_input"] == "reality"

    assert data["supported_output"] == "learning"

    assert data["metadata"]["manufacturer"] == "AI5R Factory"
