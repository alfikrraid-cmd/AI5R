#!/usr/bin/env python3

from module_loader import load_module


def generate_detail_sql(module_name: str):
    spec = load_module(module_name)

    schema = spec["database"]["schema"]
    table = spec["database"]["table"]
    lookup = spec["database"]["primary_lookup"]["field"]

    sql = f"""
SELECT *
FROM {schema}.{table}
WHERE {lookup} = $1;
""".strip()

    return sql


if __name__ == "__main__":
    print(generate_detail_sql("pump"))
