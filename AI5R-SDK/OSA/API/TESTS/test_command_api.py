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
    assert result["pipeline_id"].startswith("PIPE-CMD-")
    assert result["goal_id"].startswith("CMD-")
    assert result["task_count"] == 1
    assert result["execution_count"] == 1
    assert result["memory_count"] == 1
    assert result["response"] == "Command accepted by Runtime Pipeline"


def test_command_api_rejects_empty_prompt():
    api = OSACommandAPI()

    try:
        api.execute(prompt="", employee_id="EMP-001")
    except ValueError as error:
        assert str(error) == "prompt is required"
    else:
        raise AssertionError("Expected ValueError")


def test_command_api_uses_runtime_pipeline():
    api = OSACommandAPI()

    result = api.execute(
        prompt="Create sales dashboard",
        employee_id="EMP-001",
    )

    assert result["status"] == "SUCCESS"
    assert result["pipeline_id"].startswith("PIPE-CMD-")
    assert result["execution_count"] == 1
    assert result["memory_count"] == 1
