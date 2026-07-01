import json
from pathlib import Path

BASE = Path(__file__).parent
WF = BASE / "WORKFLOWS"
TEST = BASE / "TEST"
DOCS = BASE / "DOCS"

WF.mkdir(exist_ok=True)
TEST.mkdir(exist_ok=True)
DOCS.mkdir(exist_ok=True)

def workflow(name, method, path):
    return {
        "name": name,
        "nodes": [
            {
                "parameters": {
                    "httpMethod": method,
                    "path": path,
                    "responseMode": "lastNode",
                    "options": {}
                },
                "id": f"webhook-{path.replace('/', '-')}",
                "name": "Webhook",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 2,
                "position": [0, 0]
            }
        ],
        "connections": {},
        "settings": {
            "executionOrder": "v1"
        },
        "active": False
    }

items = [
    ("WF-LTSA-CUSTOMER-CREATE-001.json", "WF-LTSA-CUSTOMER-CREATE-001", "POST", "ltsa/customer/create"),
    ("WF-LTSA-CUSTOMER-LIST-001.json", "WF-LTSA-CUSTOMER-LIST-001", "GET", "ltsa/customer/list"),
    ("WF-LTSA-CUSTOMER-GET-001.json", "WF-LTSA-CUSTOMER-GET-001", "GET", "ltsa/customer/get"),
    ("WF-LTSA-CUSTOMER-UPDATE-001.json", "WF-LTSA-CUSTOMER-UPDATE-001", "PUT", "ltsa/customer/update"),
    ("WF-LTSA-CUSTOMER-DELETE-001.json", "WF-LTSA-CUSTOMER-DELETE-001", "DELETE", "ltsa/customer/delete"),
]

for filename, name, method, path in items:
    with open(WF / filename, "w") as f:
        json.dump(workflow(name, method, path), f, indent=2)

(TEST / "customer_registry_test.sh").write_text("""#!/usr/bin/env bash
set -e

BASE_URL="https://n8n.osa-system.com/webhook"

curl -X POST "$BASE_URL/ltsa/customer/create" \\
  -H "Content-Type: application/json" \\
  -d '{
    "customer_code":"CUST-001",
    "customer_name":"PT TEST CUSTOMER",
    "customer_type":"company",
    "industry":"Power Plant",
    "billing_email":"finance@test.com",
    "phone":"08123456789",
    "city":"Jakarta",
    "province":"DKI Jakarta"
  }'

echo
echo "Customer Registry test executed"
""")

(BASE / "README.md").write_text("""# BP-005 Customer Registry

## Purpose
Customer Registry module for LTSA Brain revenue path.

## Endpoints
- POST /webhook/ltsa/customer/create
- GET /webhook/ltsa/customer/list
- GET /webhook/ltsa/customer/get
- PUT /webhook/ltsa/customer/update
- DELETE /webhook/ltsa/customer/delete

## Definition of Done
- Database migration applied
- Customer table exists
- Workflow JSON generated
- Workflow imported into n8n
- Create/List/Get/Update/Delete tested
- Git committed
""")

(BASE / "RELEASE-NOTES.md").write_text("""# BP-005 Release Notes

Customer Registry Build Pack initialized.

Status:
- Database migration completed
- API contract created
- Workflow generator added
- Test script added
""")

print("BP-005 generated successfully")
