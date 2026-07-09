from DEMOS.DEMO_001.login_api_demo import run_demo


def test_demo_001c_returns_activity_stream():
    result = run_demo()

    stream = result["activity_stream"]

    assert len(stream) >= 2
    assert stream[0]["event_type"] == "EMPLOYEE_ACTIVITY_RECORDED"
    assert stream[0]["payload"]["activity_type"] == "RECEIVED_WORK"
    assert stream[-1]["payload"]["activity_type"] == "THINKING"
