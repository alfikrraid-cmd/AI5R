import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from IR.entity_ir import EntityIR
from IR.compilation_unit import CompilationUnit


def test_compilation_unit():
    unit = CompilationUnit(product="LTSA-BRAIN")

    entity = EntityIR(
        name="pump",
        fields=[
            {"name": "pump_code", "type": "string"},
            {"name": "pump_name", "type": "string"}
        ]
    )

    unit.add_entity(entity)

    assert unit.product == "LTSA-BRAIN"
    assert unit.entity_count() == 1
    assert unit.entities[0].name == "pump"


if __name__ == "__main__":
    test_compilation_unit()
    print("FM-005.1 Compilation Unit OK")
