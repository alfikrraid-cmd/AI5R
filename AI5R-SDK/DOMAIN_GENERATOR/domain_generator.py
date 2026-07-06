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

    def __init__(self, root_path):
        self.root_path = Path(root_path)

    def generate(self, domain_name: str):
        if not domain_name or not domain_name.strip():
            raise ValueError("domain_name is required")

        normalized_name = domain_name.strip().upper().replace(" ", "_").replace("-", "_")
        domain_path = self.root_path / normalized_name

        domain_path.mkdir(parents=True, exist_ok=True)

        created = []

        for layer in self.REQUIRED_LAYERS:
            layer_path = domain_path / layer
            layer_path.mkdir(parents=True, exist_ok=True)
            init_file = layer_path / "__init__.py"
            init_file.touch(exist_ok=True)
            created.append(str(layer_path))

        manifest_path = domain_path / "domain_manifest.py"
        manifest_path.write_text(
            f'''DOMAIN_NAME = "{normalized_name}"

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

        return {
            "status": "DOMAIN_GENERATED",
            "domain_name": normalized_name,
            "domain_path": str(domain_path),
            "created_layers": created,
        }
