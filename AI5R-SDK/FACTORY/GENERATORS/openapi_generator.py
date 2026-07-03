import json
from pathlib import Path

from MANUFACTURING.station import ManufacturingStation


class OpenAPIGenerator(ManufacturingStation):

    @property
    def name(self):
        return "openapi"


    @property
    def depends_on(self):
        return ["schema"]

    def run(self, unit, target):
        output = Path(target)
        output.parent.mkdir(parents=True, exist_ok=True)

        paths = {}

        for entity in unit.entities:
            route = f"/{entity.name.lower()}"
            paths[route] = {
                "get": {
                    "summary": f"List {entity.name}",
                    "responses": {
                        "200": {
                            "description": "OK"
                        }
                    }
                }
            }

        openapi = {
            "openapi": "3.0.0",
            "info": {
                "title": unit.product,
                "version": "1.0.0"
            },
            "paths": paths
        }

        output.write_text(json.dumps(openapi, indent=2))
        return str(output)

    def generate(self, unit, target):
        return self.run(unit, target)
