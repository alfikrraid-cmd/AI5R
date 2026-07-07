from OSA.API.command_api import OSACommandAPI


def test_command_api_accepts_command_and_creates_task():
    api = OSACommandAPI()

    result = api.execute(
        prompt="Build UMKM marketing plan",
        employee_id="EMP-001",
    )

    assert result["status"] == "SUCCESS"
    assert result["employee_id"] == "EMP-001"
    assert result["prompt"] == "Build UMKM marketing plan"
    assert result["task_id"].startswith("TASK-")
    assert result["stage"] == "READY"
    assert result["response"] == "Command accepted by OSA runtime pipeline"


def test_command_api_rejects_empty_prompt():
    api = OSACommandAPI()

    try:
        api.execute(prompt="", employee_id="EMP-001")
    except ValueError as error:
        assert str(error) == "prompt is required"
    else:
        raise AssertionError("Expected ValueError")
