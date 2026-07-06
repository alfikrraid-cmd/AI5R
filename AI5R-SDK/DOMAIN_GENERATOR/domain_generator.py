from pathlib import Path


class AI5RDomainGenerator:
    REQUIRED_LAYERS = [
        "SPECIFICATION",
        "FACTORY",
        "ARTIFACT",
        "REGISTRY",
        "RUNTIME",
        "TESTS",
    ]

    CANONICAL_PATTERN = [
        "Specification",
        "Factory",
        "Artifact",
        "Registry",
        "Runtime",
        "Operation",
        "Evolution",
    ]

    def __init__(self, root_path):
        self.root_path = Path(root_path)

    def _normalize(self, domain_name: str):
        return domain_name.strip().upper().replace(" ", "_").replace("-", "_")

    def _class_prefix(self, normalized_name: str):
        return "".join(part.title() for part in normalized_name.lower().split("_"))

    def generate(self, domain_name: str):
        if not domain_name or not domain_name.strip():
            raise ValueError("domain_name is required")

        normalized_name = self._normalize(domain_name)
        class_prefix = self._class_prefix(normalized_name)
        domain_path = self.root_path / normalized_name

        domain_path.mkdir(parents=True, exist_ok=True)

        created = []

        templates = {
            "SPECIFICATION/specification.py": f'''class {class_prefix}Specification:
    domain_name = "{normalized_name}"

    def describe(self):
        return {{
            "domain": self.domain_name,
            "layer": "Specification",
            "status": "READY",
        }}
''',
            "FACTORY/factory.py": f'''class {class_prefix}Factory:
    domain_name = "{normalized_name}"

    def build(self, specification):
        return {{
            "domain": self.domain_name,
            "layer": "Factory",
            "status": "BUILT",
            "specification": specification,
        }}
''',
            "ARTIFACT/artifact.py": f'''class {class_prefix}Artifact:
    domain_name = "{normalized_name}"

    def create(self, payload):
        return {{
            "domain": self.domain_name,
            "layer": "Artifact",
            "status": "CREATED",
            "payload": payload,
        }}
''',
            "REGISTRY/registry.py": f'''class {class_prefix}Registry:
    def __init__(self):
        self.items = {{}}

    def register(self, artifact_id, artifact):
        self.items[artifact_id] = artifact
        return artifact_id

    def get(self, artifact_id):
        return self.items.get(artifact_id)
''',
            "RUNTIME/runtime.py": f'''class {class_prefix}Runtime:
    domain_name = "{normalized_name}"

    def run(self, artifact):
        return {{
            "domain": self.domain_name,
            "layer": "Runtime",
            "status": "RUNNING",
            "artifact": artifact,
        }}
''',
            "TESTS/test_domain.py": f'''import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from {normalized_name}.SPECIFICATION.specification import {class_prefix}Specification
from {normalized_name}.FACTORY.factory import {class_prefix}Factory
from {normalized_name}.ARTIFACT.artifact import {class_prefix}Artifact
from {normalized_name}.REGISTRY.registry import {class_prefix}Registry
from {normalized_name}.RUNTIME.runtime import {class_prefix}Runtime


def test_{normalized_name.lower()}_domain_flow():
    specification = {class_prefix}Specification().describe()
    built = {class_prefix}Factory().build(specification)
    artifact = {class_prefix}Artifact().create(built)

    registry = {class_prefix}Registry()
    artifact_id = registry.register("artifact-001", artifact)

    stored_artifact = registry.get(artifact_id)
    runtime_result = {class_prefix}Runtime().run(stored_artifact)

    assert specification["status"] == "READY"
    assert built["status"] == "BUILT"
    assert artifact["status"] == "CREATED"
    assert stored_artifact == artifact
    assert runtime_result["status"] == "RUNNING"
''',
            "README.md": f'''# {normalized_name}

AI5R generated domain.

Canonical Pattern:

Specification
↓
Factory
↓
Artifact
↓
Registry
↓
Runtime
↓
Operation
↓
Evolution
''',
        }

        for layer in self.REQUIRED_LAYERS:
            layer_path = domain_path / layer
            layer_path.mkdir(parents=True, exist_ok=True)
            init_file = layer_path / "__init__.py"
            init_file.touch(exist_ok=True)
            created.append(str(layer_path))

        for relative_path, content in templates.items():
            file_path = domain_path / relative_path
            file_path.write_text(content, encoding="utf-8")
            created.append(str(file_path))

        manifest_path = domain_path / "domain_manifest.py"
        manifest_path.write_text(
            f'''DOMAIN_NAME = "{normalized_name}"
DOMAIN_VERSION = "1.0"

CANONICAL_PATTERN = [
    "Specification",
    "Factory",
    "Artifact",
    "Registry",
    "Runtime",
    "Operation",
    "Evolution",
]

REQUIRED_LAYERS = [
    "SPECIFICATION",
    "FACTORY",
    "ARTIFACT",
    "REGISTRY",
    "RUNTIME",
    "TESTS",
]
''',
            encoding="utf-8",
        )
        created.append(str(manifest_path))

        return {
            "status": "DOMAIN_GENERATED",
            "domain_name": normalized_name,
            "domain_path": str(domain_path),
            "created_layers": created,
        }
