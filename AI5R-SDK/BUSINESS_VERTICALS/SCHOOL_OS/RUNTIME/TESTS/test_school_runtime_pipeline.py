from BUSINESS_VERTICALS.SCHOOL_OS.RUNTIME.school_runtime import SchoolRuntime


def test_school_runtime_runs_goal_through_product_runtime(tmp_path):
    runtime = SchoolRuntime(root_path=tmp_path)

    runtime.start()

    result = runtime.run_goal("Create school admission strategy")

    assert result["status"] == "SUCCESS"
    assert result["product"] == "SCHOOL_OS"
    assert result["pipeline_id"].startswith("PIPE-CMD-")
    assert runtime.health() == "ACTIVE"
