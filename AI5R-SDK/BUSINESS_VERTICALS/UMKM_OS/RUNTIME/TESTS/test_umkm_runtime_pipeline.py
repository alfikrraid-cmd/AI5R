from BUSINESS_VERTICALS.UMKM_OS.RUNTIME.umkm_runtime import AI5RUMKMOSRuntime


def test_umkm_runtime_runs_goal_through_product_runtime(tmp_path):
    runtime = AI5RUMKMOSRuntime(root_path=tmp_path)

    runtime.start({
        "product": "UMKM OS",
        "agents": ["MARKETING_AGENT", "SALES_AGENT"],
    })

    result = runtime.run_goal("Create UMKM sales plan")

    assert result["status"] == "SUCCESS"
    assert result["product"] == "UMKM_OS"
    assert result["pipeline_id"].startswith("PIPE-CMD-")
