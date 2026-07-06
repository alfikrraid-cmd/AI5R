from pathlib import Path


class AI5RDomainValidator:
    REQUIRED_LAYERS = [
        "SPECIFICATION",
        "FACTORY",
        "ARTIFACT",
        "REGISTRY",
        "RUNTIME",
        "TESTS",
    ]

    REQUIRED_PATTERN = [
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

    def validate(self, domain_name: str):
        if not domain_name or not domain_name.strip():
            raise ValueError("domain_name is required")

        normalized_name = domain_name.strip().upper().replace(" ", "_").replace("-", "_")
        domain_path = self.root_path / normalized_name

        missing = []
        warnings = []

        if not domain_path.exists():
            return {
                "status": "INVALID",
                "domain": normalized_name,
                "score": 0,
                "missing": ["DOMAIN"],
                "warnings": ["Domain directory does not exist"],
            }

        for layer in self.REQUIRED_LAYERS:
            layer_path = domain_path / layer
            if not layer_path.exists():
                missing.append(layer)
            elif not (layer_path / "__init__.py").exists():
                warnings.append(f"Missing __init__.py in {layer}")

        manifest_path = domain_path / "domain_manifest.py"
        if not manifest_path.exists():
            warnings.append("Missing domain_manifest.py")

        total_checks = len(self.REQUIRED_LAYERS) + 1
        failed_checks = len(missing) + (1 if "Missing domain_manifest.py" in warnings else 0)

        score = int(((total_checks - failed_checks) / total_checks) * 100)

        return {
            "status": "VALID" if not missing and not warnings else "INVALID",
            "domain": normalized_name,
            "score": score,
            "missing": missing,
            "warnings": warnings,
        }
