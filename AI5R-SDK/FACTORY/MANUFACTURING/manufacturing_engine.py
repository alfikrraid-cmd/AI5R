"""
FM-100.4 Manufacturing Engine
"""

from GENERATORS.sql_generator import SQLGenerator
from GENERATORS.schema_generator import SchemaGenerator
from GENERATORS.openapi_generator import OpenAPIGenerator


class ManufacturingEngine:

    def __init__(self):

        self.generators = [
            SQLGenerator(),
            SchemaGenerator(),
            OpenAPIGenerator()
        ]

    def manufacture(self, unit, output_dir):

        results = []

        for generator in self.generators:

            name = generator.__class__.__name__.lower()

            if "sql" in name:
                target = f"{output_dir}/database.sql"

            elif "schema" in name:
                target = f"{output_dir}/schema.json"

            elif "openapi" in name:
                target = f"{output_dir}/openapi.json"

            else:
                continue

            generator.generate(unit, target)

            results.append(target)

        return results

