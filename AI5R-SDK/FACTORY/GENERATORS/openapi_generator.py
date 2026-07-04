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
            base = f"/{entity.name.lower()}s"
            detail = f"{base}/{{id}}"

            paths[base] = {
                "get": {
                    "summary": f"List {entity.name}s",
                    "responses": {"200": {"description": "OK"}}
                },
                "post": {
                    "summary": f"Create {entity.name}",
                    "responses": {"201": {"description": "Created"}}
                }
            }

            paths[detail] = {
                "get": {
                    "summary": f"Get {entity.name}",
                    "responses": {"200": {"description": "OK"}}
                },
                "put": {
                    "summary": f"Update {entity.name}",
                    "responses": {"200": {"description": "OK"}}
                },
                "delete": {
                    "summary": f"Delete {entity.name}",
                    "responses": {"204": {"description": "No Content"}}
                }
            }

        openapi = {
            "openapi": "3.0.0",
            "info": {
                "title": "LTSA Brain API",
                "version": "1.0.0"
            },
            "paths": paths
        }

        output.write_text(json.dumps(openapi, indent=2))
        return openapi

    def generate(self, unit, target):
        return self.run(unit, target)
