import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from OSA.TOOL_REGISTRY import ToolRegistry
from OSA.TOOL_RUNTIME import (
    ToolExecutionRequest,
    ToolRuntime,
)


def echo_tool(text: str):
    return text.upper()


def test_tool_runtime_executes_registered_tool():
    registry = ToolRegistry()
    registry.register(
        "echo",
        echo_tool,
    )

    runtime = ToolRuntime(registry)

    result = runtime.execute(
        ToolExecutionRequest(
            tool_name="echo",
            arguments={
                "text": "ai5r",
            },
        )
    )

    assert result.status == "SUCCESS"
    assert result.output == "AI5R"


def test_tool_runtime_requires_tool_name():
    registry = ToolRegistry()
    runtime = ToolRuntime(registry)

    try:
        runtime.execute(
            ToolExecutionRequest(
                tool_name="",
                arguments={},
            )
        )
    except ValueError as error:
        assert str(error) == "tool_name is required"
    else:
        raise AssertionError()
