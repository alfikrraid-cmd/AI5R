import json
from pathlib import Path

from MANUFACTURING.station import ManufacturingStation


class SchemaGenerator(ManufacturingStation):

    @property
    def name(self):
        return "schema"

    @property
    def depends_on(self):
        return ["sql"]

    def run(self, unit, target):
        output = Path(target)
        output.parent.mkdir(parents=True, exist_ok=True)

        entities = []

        for entity in unit.entities:
            entities.append({
                "name": entity.name,
                "fields": entity.fields,
            })

        schema = {
            "product": unit.product,
            "entities": entities,
        }

        output.write_text(json.dumps(schema, indent=2))
        return schema

    def generate(self, unit, target):
        return self.run(unit, target)
