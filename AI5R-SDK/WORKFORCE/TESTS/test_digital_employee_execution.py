from WORKFORCE.digital_employee_factory import DigitalEmployeeFactory


def test_digital_employee_executes_work_order():
    result = DigitalEmployeeFactory().manufacture(
        employee_name="Backend Employee",
        organization_id="ORG-AI5R",
        identity_id="ID-BACKEND-001",
        position_id="BACKEND_ENGINEER",
        kernel_id="KERNEL-001",
        capability_ids=["AUTHENTICATION"],
    )

    employee = result["employee"]

    execution = employee.execute_work_order(
        {
            "objective": "Build authentication API",
            "payload": {
                "feature": "login",
            },
        }
    )

    assert execution["status"] == "EXECUTED"
    assert execution["employee_id"] == employee.employee_id
    assert execution["manufacturing_request"]["source"] == "DIGITAL_EMPLOYEE"
    assert execution["manufacturing_request"]["objective"] == "Build authentication API"
    assert "CAPTURE_EXPERIENCE" in execution["execution_steps"]


def test_digital_employee_requires_active_status():
    employee = DigitalEmployeeFactory().manufacture(
        employee_name="Inactive Employee",
        organization_id="ORG-AI5R",
        identity_id="ID-INACTIVE-001",
        position_id="QA_ENGINEER",
        kernel_id="KERNEL-001",
    )["employee"]

    employee.status = "INACTIVE"

    try:
        employee.execute_work_order({"objective": "Create tests"})
    except ValueError as exc:
        assert "must be ACTIVE" in str(exc)
    else:
        raise AssertionError("Expected inactive employee execution to fail")


def test_digital_employee_requires_objective():
    employee = DigitalEmployeeFactory().manufacture(
        employee_name="Backend Employee",
        organization_id="ORG-AI5R",
        identity_id="ID-BACKEND-002",
        position_id="BACKEND_ENGINEER",
        kernel_id="KERNEL-001",
    )["employee"]

    try:
        employee.execute_work_order({})
    except ValueError as exc:
        assert "objective is required" in str(exc)
    else:
        raise AssertionError("Expected missing objective to fail")


def test_digital_employee_learns_new_capability_from_work_order():
    employee = DigitalEmployeeFactory().manufacture(
        employee_name="Backend Employee",
        organization_id="ORG-AI5R",
        identity_id="ID-BACKEND-003",
        position_id="BACKEND_ENGINEER",
        kernel_id="KERNEL-001",
        capability_ids=["FASTAPI"],
    )["employee"]

    execution = employee.execute_work_order(
        {
            "objective": "Build JWT login",
            "learned_capability_ids": ["JWT_AUTH"],
        }
    )

    assert "JWT_AUTH" in employee.capability_ids
    assert execution["experience_object"]["learned_capability_ids"] == ["JWT_AUTH"]
