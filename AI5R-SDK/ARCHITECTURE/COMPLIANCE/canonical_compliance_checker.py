from pathlib import Path


class CanonicalComplianceChecker:
    CANONICAL_PATTERN = [
        "SPECIFICATION",
        "FACTORY",
        "ARTIFACT",
        "REGISTRY",
        "RUNTIME",
        "TESTS",
    ]

    def __init__(self, root_path):
        self.root_path = Path(root_path)

    def check(self, domain_name: str):
        normalized = (
            domain_name.strip()
            .upper()
            .replace(" ", "_")
            .replace("-", "_")
        )

        domain_path = self.root_path / normalized

        if not domain_path.exists():
            return {
                "status": "NON_COMPLIANT",
                "domain": normalized,
                "score": 0,
                "missing": ["DOMAIN"],
                "checked": [],
            }

        checked = []
        missing = []

        for layer in self.CANONICAL_PATTERN:
            layer_path = domain_path / layer
            if layer_path.exists():
                checked.append(layer)
            else:
                missing.append(layer)

        score = int(
            (len(checked) / len(self.CANONICAL_PATTERN)) * 100
        )

        return {
            "status": "COMPLIANT" if not missing else "NON_COMPLIANT",
            "domain": normalized,
            "score": score,
            "checked": checked,
            "missing": missing,
        }
