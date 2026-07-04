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

        sql_blocks = ["-- Auto Generated\n"]

        for entity in unit.entities:
            table_name = f"ltsa_{entity.name.lower()}s"
            sql_blocks.append(
                f"""CREATE TABLE IF NOT EXISTS {table_name} (
    id SERIAL PRIMARY KEY
);
"""
            )

        sql = "\n".join(sql_blocks)

        output.write_text(sql)
        return sql

    def generate(self, unit, target):
        return self.run(unit, target)
