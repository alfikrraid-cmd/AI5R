import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from KERNEL.kernel_context import KernelContext
from KERNEL.kernel_response_builder import KernelResponseBuilder


def test_kernel_response_builder():

    context = KernelContext(
        kernel_id="KERNEL-001",
        user_input="Evaluate business idea",
        identity_context={
            "brand": "AI5R",
        },
        position_context={
            "position_code": "CEO",
        },
    )

    response = KernelResponseBuilder().build(
        context=context,
        decision_result={
            "status": "DECIDED",
            "selected_option": "VALIDATE_FIRST",
        },
        execution_result={
            "status": "READY",
        },
    )

    assert response["status"] == "RESPONSE_BUILT"
    assert response["context_id"] == context.context_id
    assert response["kernel_id"] == "KERNEL-001"
    assert response["identity_context"]["brand"] == "AI5R"
    assert response["position_context"]["position_code"] == "CEO"
    assert response["decision_result"]["selected_option"] == "VALIDATE_FIRST"
    assert response["execution_result"]["status"] == "READY"
