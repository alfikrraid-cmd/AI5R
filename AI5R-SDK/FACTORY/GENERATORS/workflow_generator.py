import json
from pathlib import Path

from MANUFACTURING.station import ManufacturingStation


class WorkflowGenerator(ManufacturingStation):

    @property
    def name(self):
        return "workflow"


    @property
    def depends_on(self):
        return ["schema", "openapi"]

    def run(self, unit, target):
        output = Path(target)
        output.parent.mkdir(parents=True, exist_ok=True)

        workflow = {
            "product": unit.product,
            "workflow": "generated",
            "steps": []
        }

        output.write_text(json.dumps(workflow, indent=2))
        return str(output)

    def generate(self, unit, target):
        return self.run(unit, target)
