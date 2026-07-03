import json
from pathlib import Path

from MANUFACTURING.station import ManufacturingStation


class ReleaseGenerator(ManufacturingStation):

    @property
    def name(self):
        return "release"

    def run(self, unit, target):
        output = Path(target)
        output.parent.mkdir(parents=True, exist_ok=True)

        release = {
            "product": unit.product,
            "release": "generated",
            "status": "ready"
        }

        output.write_text(json.dumps(release, indent=2))
        return str(output)

    def generate(self, unit, target):
        return self.run(unit, target)
