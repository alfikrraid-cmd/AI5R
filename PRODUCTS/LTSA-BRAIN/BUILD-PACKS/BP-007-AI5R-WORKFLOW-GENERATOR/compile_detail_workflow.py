import json
import copy
from pathlib import Path

BASE_DIR = Path(__file__).parent
TEMPLATE_FILE = BASE_DIR / "TEMPLATES" / "WF-TEMPLATE-CRUD-V1.json"
OUTPUT_DIR = BASE_DIR / "OUTPUTS"

MODULE = "pump"
TABLE = "public.ltsa_pumps"
PRIMARY_KEY = "tag_number"
OPERATION = "detail"

def find_node(workflow, node_type):
    for node in workflow["nodes"]:
        if node["type"] == node_type:
            return node
    raise Exception(f"Node type not found: {node_type}")

def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template = json.load(f)

    workflow = copy.deepcopy(template)

    workflow["name"] = "WF-LTSA-PUMP-DETAIL-001"
    workflow["active"] = False

    webhook = find_node(workflow, "n8n-nodes-base.webhook")
    old_webhook_name = webhook["name"]
    webhook["name"] = "GET /ltsa/pump/detail"
    webhook["parameters"]["path"] = "ltsa/pump/detail"
    webhook["webhookId"] = "ltsa-pump-detail"

    parse_node = next(n for n in workflow["nodes"] if n["name"] == "Parse ID")
    parse_node["name"] = "Parse Pump Code"
    parse_node["parameters"]["jsCode"] = """const tag_number = $json.query?.tag_number;

return [{
  json: {
    tag_number,
    valid: !!tag_number
  }
}];"""

    postgres = find_node(workflow, "n8n-nodes-base.postgres")
    postgres["name"] = "Get Pump Detail"
    postgres["parameters"]["query"] = """SELECT *
FROM public.ltsa_pumps
WHERE tag_number = '{{ $json.tag_number }}'
LIMIT 1;"""
    postgres["parameters"]["options"]["queryReplacement"] = "={{ [$json.tag_number] }}"

    build_node = next(n for n in workflow["nodes"] if n["name"] == "Build Detail Response")
    build_node["name"] = "Build Pump Detail Response"
    build_node["parameters"]["jsCode"] = """const row = $input.first()?.json;

if (!row || !row.id) {
  return [{
    json: {
      statusCode: 404,
      success: false,
      message: "Pump not found",
      data: null
    }
  }];
}

return [{
  json: {
    statusCode: 200,
    success: true,
    message: "Pump detail found",
    data: row
  }
}];"""

    respond = next(n for n in workflow["nodes"] if n["name"] == "Respond Detail")
    respond["name"] = "Respond Pump Detail"

    connections = workflow["connections"]

    connections[webhook["name"]] = connections.pop(old_webhook_name)

    for source, conn in connections.items():
        for output in conn.get("main", []):
            for item in output:
                if item["node"] == "Parse ID":
                    item["node"] = "Parse Pump Code"
                if item["node"] == "Get Customer Detail":
                    item["node"] = "Get Pump Detail"
                if item["node"] == "Build Detail Response":
                    item["node"] = "Build Pump Detail Response"
                if item["node"] == "Respond Detail":
                    item["node"] = "Respond Pump Detail"

    if "Parse ID" in connections:
        connections["Parse Pump Code"] = connections.pop("Parse ID")
    if "Get Customer Detail" in connections:
        connections["Get Pump Detail"] = connections.pop("Get Customer Detail")
    if "Build Detail Response" in connections:
        connections["Build Pump Detail Response"] = connections.pop("Build Detail Response")

    output_file = OUTPUT_DIR / "WF-LTSA-PUMP-DETAIL-001.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(workflow, f, indent=2)

    print(f"Generated: {output_file}")

if __name__ == "__main__":
    main()
