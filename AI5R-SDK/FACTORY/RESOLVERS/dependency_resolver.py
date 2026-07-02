"""
FM-005.4 Dependency Resolver

Minimal resolver for entity dependencies.
"""

class DependencyResolver:

    def resolve(self, manifest: dict) -> dict:
        entities = manifest.get("entities", [])
        graph = {}

        for entity in entities:
            name = entity.get("entity") or entity.get("name")

            if not name:
                raise ValueError("Entity missing name")

            depends_on = entity.get("depends_on", [])

            if not isinstance(depends_on, list):
                raise ValueError(f"Entity '{name}' depends_on must be a list")

            graph[name] = depends_on

        return graph
