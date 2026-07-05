import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from KERNEL.kernel_builder import KernelBuilder
from KERNEL.kernel_pipeline import KernelPipeline


def test_kernel_pipeline():

    kernel = KernelBuilder().build()

    result = KernelPipeline().run(
        kernel=kernel,
        user_input="Evaluate new business idea",
        identity_context={
            "brand": "AI5R",
        },
        position_context={
            "position_code": "CEO",
        },
        decision_context={
            "objective": "Assess viability",
        },
        metadata={
            "owner": "AI5R",
        },
    )

    context = result["context"]

    assert result["status"] == "PIPELINE_COMPLETED"
    assert result["kernel_id"] == kernel.kernel_id
    assert context.kernel_id == kernel.kernel_id
    assert context.user_input == "Evaluate new business idea"
    assert context.identity_context["brand"] == "AI5R"
    assert context.position_context["position_code"] == "CEO"
    assert context.decision_context["objective"] == "Assess viability"
