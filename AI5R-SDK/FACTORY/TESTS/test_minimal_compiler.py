import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from COMPILER.minimal_compiler import MinimalCompiler
from IR.entity_ir import EntityIR


def test_minimal_compiler():
    manifest = {
        "entity": "pump",
        "fields": [
            {"name": "pump_code", "type": "string"},
            {"name": "pump_name", "type": "string"}
        ]
    }

    compiler = MinimalCompiler()
    ir = compiler.compile_entity(manifest)

    assert isinstance(ir, EntityIR)
    assert ir.name == "pump"
    assert len(ir.fields) == 2


if __name__ == "__main__":
    test_minimal_compiler()
    print("FM-004.6 Minimal Compiler OK")
