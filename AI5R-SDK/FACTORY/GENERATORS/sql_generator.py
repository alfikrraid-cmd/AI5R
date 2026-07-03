from pathlib import Path

from MANUFACTURING.station import ManufacturingStation


class SQLGenerator(ManufacturingStation):

    @property
    def name(self):
        return "sql"


    @property
    def depends_on(self):
        return []

    def run(self, unit, target):
        output = Path(target)
        output.parent.mkdir(parents=True, exist_ok=True)

        sql = f"""-- Auto Generated

CREATE TABLE {unit.product.lower()} (
    id SERIAL PRIMARY KEY
);
"""

        output.write_text(sql)
        return str(output)

    def generate(self, unit, target):
        return self.run(unit, target)
