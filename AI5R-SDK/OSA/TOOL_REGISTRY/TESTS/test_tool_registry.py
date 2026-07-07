import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from OSA.TOOL_REGISTRY import (
    ToolDefinition,
    ToolRegistry,
    ToolStatus,
)


def test_tool_registry_registers_tool():
    registry = ToolRegistry()

    tool = registry.register(
        ToolDefinition(
            tool_id="TOOL-FS-001",
            name="Filesystem Tool",
            description="Reads and writes files",
        )
    )

    assert tool.tool_id == "TOOL-FS-001"
    assert registry.get("TOOL-FS-001") == tool


def test_tool_registry_lists_tools():
    registry = ToolRegistry()

    registry.register(
        ToolDefinition(
            tool_id="TOOL-WEB-001",
            name="Web Search Tool",
        )
    )

    registry.register(
        ToolDefinition(
            tool_id="TOOL-DB-001",
            name="Database Tool",
        )
    )

    assert len(registry.list_tools()) == 2


def test_tool_registry_executes_tool_without_handler():
    registry = ToolRegistry()

    registry.register(
        ToolDefinition(
            tool_id="TOOL-ECHO-001",
            name="Echo Tool",
        )
    )

    result = registry.execute(
        "TOOL-ECHO-001",
        {"message": "hello"},
    )

    assert result["tool_id"] == "TOOL-ECHO-001"
    assert result["status"] == "NO_HANDLER"
    assert result["payload"]["message"] == "hello"


def test_tool_registry_executes_tool_with_handler():
    registry = ToolRegistry()

    def echo_handler(payload):
        return {
            "status": "OK",
            "output": payload["message"],
        }

    registry.register(
        ToolDefinition(
            tool_id="TOOL-ECHO-002",
            name="Echo Tool",
            handler=echo_handler,
        )
    )

    result = registry.execute(
        "TOOL-ECHO-002",
        {"message": "hello"},
    )

    assert result["status"] == "OK"
    assert result["output"] == "hello"


def test_tool_registry_can_disable_and_enable_tool():
    registry = ToolRegistry()

    registry.register(
        ToolDefinition(
            tool_id="TOOL-SHELL-001",
            name="Shell Tool",
        )
    )

    disabled = registry.disable("TOOL-SHELL-001")

    assert disabled.status == ToolStatus.DISABLED

    enabled = registry.enable("TOOL-SHELL-001")

    assert enabled.status == ToolStatus.ENABLED


def test_tool_registry_rejects_disabled_tool_execution():
    registry = ToolRegistry()

    registry.register(
        ToolDefinition(
            tool_id="TOOL-SHELL-001",
            name="Shell Tool",
        )
    )

    registry.disable("TOOL-SHELL-001")

    try:
        registry.execute("TOOL-SHELL-001", {})
    except RuntimeError as error:
        assert str(error) == "Tool is disabled: TOOL-SHELL-001"
    else:
        raise AssertionError("RuntimeError was not raised")


def test_tool_registry_requires_tool_id_and_name():
    registry = ToolRegistry()

    try:
        registry.register(
            ToolDefinition(
                tool_id="",
                name="Broken Tool",
            )
        )
    except ValueError as error:
        assert str(error) == "tool_id is required"
    else:
        raise AssertionError("ValueError was not raised")

    try:
        registry.register(
            ToolDefinition(
                tool_id="TOOL-BROKEN",
                name="",
            )
        )
    except ValueError as error:
        assert str(error) == "name is required"
    else:
        raise AssertionError("ValueError was not raised")


def test_tool_registry_raises_when_tool_missing():
    registry = ToolRegistry()

    try:
        registry.get("TOOL-MISSING")
    except KeyError as error:
        assert str(error) == "'Tool not found: TOOL-MISSING'"
    else:
        raise AssertionError("KeyError was not raised")
