import json
from pathlib import Path

BASE = Path(__file__).parent

required = [
    "WORKFLOWS/WF-LTSA-CUSTOMER-CREATE-001.json",
    "WORKFLOWS/WF-LTSA-CUSTOMER-LIST-001.json",
    "WORKFLOWS/WF-LTSA-CUSTOMER-GET-001.json",
    "WORKFLOWS/WF-LTSA-CUSTOMER-UPDATE-001.json",
    "WORKFLOWS/WF-LTSA-CUSTOMER-DELETE-001.json",
    "TEST/customer_registry_test.sh",
    "README.md",
    "RELEASE-NOTES.md"
]

failed = False

for item in required:
    path = BASE / item
    if not path.exists():
        print(f"FAILED missing: {item}")
        failed = True
    elif item.endswith(".json"):
        try:
            json.load(open(path))
            print(f"OK json: {item}")
        except Exception as e:
            print(f"FAILED json: {item} {e}")
            failed = True
    else:
        print(f"OK file: {item}")

if failed:
    raise SystemExit(1)

print("PASS BP-005 verification")
