from OSA.ORGANIZATION_RUNTIME import EndToEndOrganizationRuntime


def test_end_to_end_organization_runtime_completes_full_pipeline():
    runtime = EndToEndOrganizationRuntime()

    result = runtime.run(
        goal="Launch AI5R autonomous digital organization",
        metadata={"source": "test"},
    )

    assert result.status == "COMPLETED"
    assert result.goal == "Launch AI5R autonomous digital organization"

    assert result.task["status"] == "CREATED"
    assert result.plan["status"] == "PLANNED"
    assert result.capability["status"] == "RESOLVED"
    assert result.skill["status"] == "MATCHED"
    assert result.employee["status"] == "ORCHESTRATED"
    assert result.coordination["status"] == "COORDINATED"
    assert result.agent_runtime["status"] == "ADAPTED"
    assert result.tool["status"] == "SELECTED"
    assert result.execution["status"] == "EXECUTED"
    assert result.reflection["status"] == "REFLECTED"
    assert result.memory["status"] == "LEARNED"
    assert result.context["status"] == "UPDATED"
    assert result.event["status"] == "PUBLISHED"
    assert result.organization["status"] == "UPDATED"

    assert result.event["event_type"] == "ORGANIZATION_RUNTIME_COMPLETED"


def test_end_to_end_organization_runtime_rejects_empty_goal():
    runtime = EndToEndOrganizationRuntime()

    try:
        runtime.run("")
    except ValueError as exc:
        assert str(exc) == "Goal is required"
    else:
        raise AssertionError("Expected ValueError")
