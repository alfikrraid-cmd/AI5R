"""
AI5R Entity IR Test
FM-004.5
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
FACTORY = ROOT / "AI5R-SDK" / "FACTORY"

sys.path.insert(0, str(FACTORY))

from IR.entity_ir import EntityIR

ir = EntityIR(
    name="Pump",
    fields=[
        {"name": "pump_code", "type": "string"},
        {"name": "capacity", "type": "float"}
    ]
)

data = ir.to_dict()

assert data["kind"] == "entity"
assert data["name"] == "Pump"
assert len(data["fields"]) == 2

ir2 = EntityIR.from_dict(data)

assert ir2.name == "Pump"
assert ir2.fields[0]["name"] == "pump_code"

print("FM-004.5 Entity IR OK")
