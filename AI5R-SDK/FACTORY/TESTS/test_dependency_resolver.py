import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from RESOLVERS.dependency_resolver import DependencyResolver


def test_dependency_resolver():
    manifest = {
        "product": "LTSA-BRAIN",
        "entities": [
            {
                "entity": "customer",
                "fields": [
                    {"name": "customer_code", "type": "string"}
                ]
            },
            {
                "entity": "pump",
                "depends_on": ["customer"],
                "fields": [
                    {"name": "pump_code", "type": "string"}
                ]
            }
        ]
    }

    resolver = DependencyResolver()
    graph = resolver.resolve(manifest)

    assert graph["customer"] == []
    assert graph["pump"] == ["customer"]


if __name__ == "__main__":
    test_dependency_resolver()
    print("FM-005.4 Dependency Resolver OK")
