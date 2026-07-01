"""
AI5R SQL Manufacturing Engine
FM-001.7
"""

SQL_TYPE_MAP = {
    "string": "TEXT",
    "integer": "INTEGER",
    "number": "NUMERIC",
    "boolean": "BOOLEAN",
    "date": "DATE",
    "datetime": "TIMESTAMP"
}


class SQLGenerator:

    def generate_create_table(self, registry: dict) -> str:
        table = registry["table"]
        primary_key = registry["primary_key"]
        fields = registry["fields"]

        lines = []
        lines.append(f"CREATE TABLE IF NOT EXISTS public.{table} (")

        column_lines = []

        for field in fields:
            name = field["name"]
            field_type = SQL_TYPE_MAP.get(field.get("type", "string"), "TEXT")
            required = field.get("required", False)

            column = f"    {name} {field_type}"

            if name == primary_key:
                column += " PRIMARY KEY"

            if required:
                column += " NOT NULL"

            column_lines.append(column)

        column_lines.append("    created_at TIMESTAMP DEFAULT NOW()")
        column_lines.append("    updated_at TIMESTAMP DEFAULT NOW()")

        lines.append(",\n".join(column_lines))
        lines.append(");")

        return "\n".join(lines)

    def generate_seed(self, registry: dict) -> str:
        table = registry["table"]
        primary_key = registry["primary_key"]

        return (
            f"INSERT INTO public.{table} ({primary_key})\n"
            f"VALUES ('TEST-001')\n"
            f"ON CONFLICT ({primary_key}) DO NOTHING;\n"
        )

    def generate_indexes(self, registry: dict) -> str:
        table = registry["table"]
        primary_key = registry["primary_key"]

        return (
            f"CREATE INDEX IF NOT EXISTS idx_{table}_{primary_key}\n"
            f"ON public.{table} ({primary_key});\n"
        )

    def generate_rollback(self, registry: dict) -> str:
        table = registry["table"]
        return f"DROP TABLE IF EXISTS public.{table};\n"
