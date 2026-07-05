import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from KERNEL.kernel_builder import KernelBuilder
from KERNEL.kernel_orchestrator import KernelOrchestrator


def test_kernel_orchestrator():

    kernel = KernelBuilder().build()

    result = KernelOrchestrator().handle(
        kernel=kernel,
        user_input="Evaluate expansion idea",
        identity_context={
            "brand": "AI5R",
        },
        position_context={
            "position_code": "CEO",
        },
        decision_context={
            "objective": "Assess viability",
        },
        decision_result={
            "status": "DECIDED",
            "selected_option": "VALIDATE_FIRST",
        },
        execution_result={
            "status": "READY",
        },
    )

    assert result["status"] == "ORCHESTRATED"
    assert result["kernel_id"] == kernel.kernel_id
    assert result["pipeline"]["status"] == "PIPELINE_COMPLETED"
    assert result["response"]["status"] == "RESPONSE_BUILT"
    assert result["response"]["decision_result"]["selected_option"] == "VALIDATE_FIRST"
    assert result["response"]["position_context"]["position_code"] == "CEO"
