from BUSINESS_VERTICALS.AUDITOR_OS.RUNTIME.auditor_runtime import AuditorRuntime


def test_auditor_runtime_runs_goal_through_product_runtime(tmp_path):
    runtime = AuditorRuntime(root_path=tmp_path)

    runtime.start()

    result = runtime.run_goal("Create audit risk assessment")

    assert result["status"] == "SUCCESS"
    assert result["product"] == "AUDITOR_OS"
    assert result["pipeline_id"].startswith("PIPE-CMD-")
    assert runtime.health() == "ACTIVE"
