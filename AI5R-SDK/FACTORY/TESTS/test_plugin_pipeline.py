import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from IR.compilation_unit import CompilationUnit
from PIPELINE.plugin_pipeline import PluginPipeline


class DummyPlugin:

    def run(self, compilation_unit):
        return {
            "plugin": "dummy",
            "product": compilation_unit.product,
            "entities": compilation_unit.entity_count(),
        }


def test_plugin_pipeline():

    unit = CompilationUnit(product="LTSA-BRAIN")

    pipeline = PluginPipeline()

    pipeline.add_plugin(DummyPlugin())

    results = pipeline.run(unit)

    assert len(results) == 1
    assert results[0]["plugin"] == "dummy"
    assert results[0]["product"] == "LTSA-BRAIN"
    assert results[0]["entities"] == 0


if __name__ == "__main__":
    test_plugin_pipeline()
    print("FM-005.5 Plugin Pipeline OK")
