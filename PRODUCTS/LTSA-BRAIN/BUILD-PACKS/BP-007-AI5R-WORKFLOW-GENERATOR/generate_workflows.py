import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
SPEC_FILE = BASE_DIR / "SPECS" / "workflow_generator_spec.json"
OUTPUT_DIR = BASE_DIR / "OUTPUTS"

def load_spec():
    with open(SPEC_FILE, "r") as f:
        return json.load(f)

def make_webhook_node(module, operation):
    return {
        "parameters": {
            "httpMethod": "GET" if operation != "create" else "POST",
            "path": f"ltsa/{module}/{operation}",
            "responseMode": "responseNode"
        },
        "id": f"webhook-{module}-{operation}",
        "name": "Webhook",
        "type": "n8n-nodes-base.webhook",
        "typeVersion": 2,
        "position": [0, 0]
    }

def make_postgres_node(table, operation):
    if operation == "list":
        query = f"SELECT * FROM {table} ORDER BY id DESC LIMIT 50;"
    elif operation == "detail":
        query = f"SELECT * FROM {table} WHERE id = {{$json.query.id}} LIMIT 1;"
    elif operation == "by-code":
        query = f"SELECT * FROM {table} WHERE customer_code = '{{$json.query.customer_code}}' LIMIT 1;"
    elif operation == "create":
        query = f"INSERT INTO {table} (customer_code, customer_name, customer_type, city) VALUES ('{{$json.body.customer_code}}', '{{$json.body.customer_name}}', '{{$json.body.customer_type}}', '{{$json.body.city}}') RETURNING *;"
    elif operation == "update":
        query = f"UPDATE {table} SET customer_name = '{{$json.body.customer_name}}', city = '{{$json.body.city}}' WHERE customer_code = '{{$json.body.customer_code}}' RETURNING *;"
    elif operation == "delete":
        query = f"DELETE FROM {table} WHERE customer_code = '{{$json.query.customer_code}}' RETURNING *;"
    else:
        query = "SELECT 1;"

    return {
        "parameters": {
            "operation": "executeQuery",
            "query": query
        },
        "id": f"postgres-{operation}",
        "name": "Postgres",
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.6,
        "position": [260, 0],
        "credentials": {
            "postgres": {
                "id": "REPLACE_WITH_POSTGRES_CREDENTIAL_ID",
                "name": "Postgres account"
            }
        }
    }

def make_code_node(operation):
    return {
        "parameters": {
            "jsCode": f"""
return [
  {{
    json: {{
      success: true,
      operation: "{operation}",
      data: items.map(item => item.json)
    }}
  }}
];
"""
        },
        "id": f"code-build-response-{operation}",
        "name": "Build Response",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [520, 0]
    }

def make_respond_node():
    return {
        "parameters": {
            "respondWith": "json",
            "responseBody": "={{$json}}"
        },
        "id": "respond-to-webhook",
        "name": "Respond to Webhook",
        "type": "n8n-nodes-base.respondToWebhook",
        "typeVersion": 1.4,
        "position": [780, 0]
    }

def make_workflow(module, table, operation):
    return {
        "name": f"LTSA {module.title()} {operation.title()}",
        "nodes": [
            make_webhook_node(module, operation),
            make_postgres_node(table, operation),
            make_code_node(operation),
            make_respond_node()
        ],
        "connections": {
            "Webhook": {
                "main": [[{"node": "Postgres", "type": "main", "index": 0}]]
            },
            "Postgres": {
                "main": [[{"node": "Build Response", "type": "main", "index": 0}]]
            },
            "Build Response": {
                "main": [[{"node": "Respond to Webhook", "type": "main", "index": 0}]]
            }
        },
        "settings": {},
        "staticData": None,
        "pinData": {}
    }

def main():
    spec = load_spec()
    module = spec["module"]
    table = spec["table"]
    operations = spec["operations"]

    OUTPUT_DIR.mkdir(exist_ok=True)

    for operation in operations:
        filename = f"WF-LTSA-{module.upper()}-{operation.upper()}-001.json"
        output_path = OUTPUT_DIR / filename

        workflow = make_workflow(module, table, operation)

        with open(output_path, "w") as f:
            json.dump(workflow, f, indent=2)

        print(f"Generated: {output_path}")

if __name__ == "__main__":
    main()
