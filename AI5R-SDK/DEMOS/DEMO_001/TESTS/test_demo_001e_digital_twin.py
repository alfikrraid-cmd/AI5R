from DEMOS.DEMO_001.login_api_demo import run_demo


def test_demo_001e_returns_digital_twin_snapshot():
    result = run_demo()

    snapshot = result["digital_twin_snapshot"]

    assert len(snapshot) >= 1

    employee_twin = list(snapshot.values())[0]

    assert employee_twin["entity_type"] == "DIGITAL_EMPLOYEE"
    assert employee_twin["status"] == "COMPLETED"
    assert employee_twin["state"]["progress"] == 100


def test_demo_001e_logs_digital_twin_creation():
    result = run_demo()
    logs = "\n".join(result["logs"])

    assert "Digital Twin Snapshot created" in logs
