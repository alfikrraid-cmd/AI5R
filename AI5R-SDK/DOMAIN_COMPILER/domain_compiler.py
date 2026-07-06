from datetime import datetime, UTC
from pathlib import Path

from DOMAIN_VALIDATOR import AI5RDomainValidator


class AI5RDomainCompiler:
    def __init__(self, root_path):
        self.root_path = Path(root_path)
        self.validator = AI5RDomainValidator(root_path)

    def compile(self, domain_name: str):
        validation = self.validator.validate(domain_name)

        if validation["status"] != "VALID":
            return {
                "status": "FAILED",
                "reason": "DOMAIN_VALIDATION_FAILED",
                "validation": validation,
            }

        normalized_name = validation["domain"]
        domain_path = self.root_path / normalized_name

        manifest = domain_path / "domain_manifest.py"
        readme = domain_path / "README.md"

        compiled_layers = []

        for layer in [
            "SPECIFICATION",
            "FACTORY",
            "ARTIFACT",
            "REGISTRY",
            "RUNTIME",
            "TESTS",
        ]:
            if (domain_path / layer).exists():
                compiled_layers.append(layer)

        package = {
            "status": "COMPILED",
            "domain": normalized_name,
            "version": "1.0",
            "compiled_at": datetime.now(UTC).isoformat(),
            "manifest_exists": manifest.exists(),
            "readme_exists": readme.exists(),
            "layers": compiled_layers,
        }

        return package
