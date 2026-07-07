import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from OSA.TOOL_RUNTIME import (
    ToolExecutionRequest,
    ToolRuntime,
)


def echo_tool(text: str):
    return text.upper()


class FakeToolRegistry:
    def __init__(self):
        self.tools = {
            "echo": echo_tool,
        }

    def resolve(self, tool_name):
        return self.tools[tool_name]


def test_tool_runtime_executes_registered_tool():
    registry = FakeToolRegistry()
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
    runtime = ToolRuntime(FakeToolRegistry())

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
