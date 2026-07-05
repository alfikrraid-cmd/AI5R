from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from FACTORY.PIPELINE.ltsa_ai_blueprint_runtime import LTSAIBlueprintRuntime


def test_ltsa_ai_blueprint_runtime_runs_product_blueprint():
    runtime = LTSAIBlueprintRuntime(
        REPO / "PRODUCTS/LTSA-AI/product.blueprint.json"
    )

    result = runtime.run(
        {
            "source": "manual_input",
            "payload": {
                "observation": "customer needs LTSA technical service agreement support"
            },
            "metadata": {
                "product": "LTSA-AI"
            },
            "context": {
                "customer_type": "enterprise"
            },
        }
    )

    assert result.status == "COMPLETED"
    assert result.steps[0] == "MS-001"
    assert result.steps[-1] == "MS-011"
    assert result.outputs["MS-001"]["type"] == "REALITY_OBJECT"
    assert result.outputs["MS-011"]["type"] == "ACTION_OBJECT"
    assert result.outputs["MS-011"]["action_data"]["action"] == "execute_next_step"
