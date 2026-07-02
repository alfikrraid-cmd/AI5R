"""
AI5R Workflow Generator
FM-100.5.1
Generates minimal n8n workflow JSON from CompilationUnit.
"""

import json
from pathlib import Path


class WorkflowGenerator:

    def generate(self, unit, output_path):

        workflow = {
            "name": f"{unit.product_name} Workflow",
            "nodes": [],
            "connections": {},
            "active": False,
            "settings": {},
            "versionId": "fm-100.5.1"
        }

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        output_path.write_text(
            json.dumps(workflow, indent=2),
            encoding="utf-8"
        )

        return str(output_path)
