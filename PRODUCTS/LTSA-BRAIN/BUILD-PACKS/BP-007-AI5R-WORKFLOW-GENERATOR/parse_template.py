import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
TEMPLATE_FILE = BASE_DIR / "TEMPLATES" / "WF-TEMPLATE-CRUD-V1.json"

def main():
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        workflow = json.load(f)

    print("=" * 60)
    print("AI5R Workflow Template Parser")
    print("=" * 60)

    print(f"Workflow Name : {workflow['name']}")
    print(f"Workflow ID   : {workflow.get('id')}")
    print(f"Version ID    : {workflow.get('versionId')}")

    print()

    nodes = workflow["nodes"]

    print(f"Total Nodes       : {len(nodes)}")
    print(f"Total Connections : {len(workflow['connections'])}")

    print()

    print("Node List")
    print("-" * 60)

    for i, node in enumerate(nodes, start=1):
        print(f"{i}. {node['name']}")
        print(f"   Type : {node['type']}")
        print(f"   ID   : {node['id']}")

        if node["type"] == "n8n-nodes-base.webhook":
            print(f"   Path : {node['parameters']['path']}")

        if node["type"] == "n8n-nodes-base.postgres":
            print("   PostgreSQL Node")

        print()

if __name__ == "__main__":
    main()
