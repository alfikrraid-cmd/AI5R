"""
FM-100.3.1 SQL Generator

Generates database.sql from a CompilationUnit.
"""

from pathlib import Path


class SQLGenerator:
    def generate(self, unit, output_path: str) -> str:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = []
        lines.append("-- AI5R Generated SQL")
        lines.append(f"-- Product: {unit.product}")
        lines.append("")

        for entity in unit.entities:
            table_name = f"ltsa_{entity.name}s"

            lines.append(f"CREATE TABLE IF NOT EXISTS {table_name} (")
            lines.append("    id SERIAL PRIMARY KEY,")
            lines.append("    code VARCHAR(100) UNIQUE NOT NULL,")
            lines.append("    name VARCHAR(255) NOT NULL,")
            lines.append("    status VARCHAR(50) DEFAULT 'active',")
            lines.append("    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,")
            lines.append("    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            lines.append(");")
            lines.append("")

        sql = "\n".join(lines)
        path.write_text(sql, encoding="utf-8")

        return sql
