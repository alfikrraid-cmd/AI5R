import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from KERNEL.kernel_context import KernelContext


def test_kernel_context():

    context = KernelContext(
        kernel_id="KERNEL-001",
        user_input="Evaluate this business idea",
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

    assert context.object_type == "KERNEL_CONTEXT"
    assert context.status == "CREATED"
    assert context.kernel_id == "KERNEL-001"
    assert context.user_input == "Evaluate this business idea"
    assert context.identity_context["brand"] == "AI5R"
    assert context.position_context["position_code"] == "CEO"
    assert context.context_id.startswith("KCTX-")
