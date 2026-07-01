#!/usr/bin/env python3

import json
import sys
from pathlib import Path

from module_loader import load_module
from sql_generator import generate_detail_sql


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "OUTPUTS"


def generate_workflow(module_name: str, workflow_type: str):
    spec = load_module(module_name)

    workflow_spec = spec["workflows"][workflow_type]
    lookup = spec["database"]["primary_lookup"]

    sql = generate_detail_sql(module_name)

    workflow = {
        "name": workflow_spec["name"],
        "nodes": [
            {
                "parameters": {
                    "path": workflow_spec["webhook_path"],
                    "responseMode": "lastNode",
                    "options": {}
                },
                "id": "Webhook",
                "name": "Webhook",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 2,
                "position": [0, 0],
                "webhookId": workflow_spec["name"]
            },
            {
                "parameters": {
                    "operation": "executeQuery",
                    "query": sql,
                    "options": {
                        "queryReplacement": f"={{ $json.query.{lookup['query_param']} }}"
                    }
                },
                "id": "Postgres",
                "name": "Postgres",
                "type": "n8n-nodes-base.postgres",
                "typeVersion": 2.6,
                "position": [260, 0],
                "credentials": {
                    "postgres": {
                        "id": "",
                        "name": "Postgres account"
                    }
                }
            }
        ],
        "connections": {
            "Webhook": {
                "main": [
                    [
                        {
                            "node": "Postgres",
                            "type": "main",
                            "index": 0
                        }
                    ]
                ]
            }
        },
        "settings": {},
        "staticData": None
    }

    return workflow


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 workflow_generator.py <module> <workflow_type>")
        sys.exit(1)

    module_name = sys.argv[1]
    workflow_type = sys.argv[2]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    workflow = generate_workflow(module_name, workflow_type)
    output_file = OUTPUT_DIR / f"{workflow['name']}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(workflow, f, indent=2)

    print(output_file)


if __name__ == "__main__":
    main()
