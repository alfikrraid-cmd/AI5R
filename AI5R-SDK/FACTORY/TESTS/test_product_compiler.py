import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from COMPILER.minimal_compiler import MinimalCompiler


def test_product_compiler():

    manifest = {

        "product": "LTSA-BRAIN",

        "entities": [

            {
                "entity": "pump",
                "fields": [
                    {"name": "pump_code", "type": "string"}
                ]
            },

            {
                "entity": "customer",
                "fields": [
                    {"name": "customer_code", "type": "string"}
                ]
            }

        ]
    }

    compiler = MinimalCompiler()

    unit = compiler.compile_product(manifest)

    assert unit.product == "LTSA-BRAIN"
    assert unit.entity_count() == 2

    assert unit.entities[0].name == "pump"
    assert unit.entities[1].name == "customer"


if __name__ == "__main__":
    test_product_compiler()
    print("FM-005.2 Product Compiler OK")
